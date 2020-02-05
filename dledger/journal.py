import csv
import re
import locale

from dledger.localeutil import trysetlocale
from dledger.formatutil import format_amount
from dledger.fileutil import fileencoding
from dledger.dateutil import parse_datestamp

from dataclasses import dataclass
from datetime import datetime, date

from typing import List, Tuple, Optional
from enum import Enum

SUPPORTED_TYPES = ['journal', 'nordnet']

IMPORT_EX_DATE = False  # whether to import ex- or payout date when reading non-journal transactions


class Distribution(Enum):
    FINAL = 0
    INTERIM = 1
    SPECIAL = 2


@dataclass(frozen=True, unsafe_hash=True)
class Amount:
    value: float
    symbol: Optional[str] = None
    format: Optional[str] = None


@dataclass(frozen=True, unsafe_hash=True)
class Transaction:
    """ Represents a transaction. """

    date: date  # for order and display; no assumption on whether this is payout, ex-date or other
    ticker: str
    position: int
    amount: Optional[Amount] = None
    dividend: Optional[Amount] = None
    kind: Distribution = Distribution.FINAL
    payout_date: Optional[date] = None  # to determine exchange rate if transaction date is earlier

    def __lt__(self, other):
        return self.date < other.date


def read(path: str, kind: str) \
        -> List[Transaction]:
    """ Return a list of records imported from a file. """

    encoding = fileencoding(path)

    if encoding is None or len(encoding) == 0:
        raise ValueError(f'Path could not be read: \'{path}\'')

    if kind == 'journal':
        return read_journal_transactions(path, encoding)
    elif kind == 'nordnet':
        return read_nordnet_transactions(path, encoding)

    return []


def raise_parse_error(error: str, location: Tuple[str, int]) -> None:
    raise ValueError(f'{location[0]}:{location[1]} {error}')


def read_journal_transactions(path: str, encoding: str = 'utf-8') \
        -> List[Transaction]:
    journal_entries = []

    # note that this pattern will initially let inconsistent formatting pass (e.g. 2019/12-1)
    # but will eventually raise a formatting error later on (it is faster to skip validation
    # through parse_datestamp at this point)
    transaction_start = re.compile(r'[0-9]+[-/][0-9]+[-/][0-9]+')

    with open(path, newline='', encoding=encoding) as file:
        starting_line_number = -1  # todo: why -1?
        line_number = 0
        lines: List[str] = []
        # start reading, line by line; each line read representing part of the current transaction
        # once we encounter a line starting with what looks like a date, we take that to indicate
        # the beginning of next transaction and parse all lines read up to this point (excluding
        # that line), and then repeat until end of file
        while line := file.readline():
            line_number += 1
            # remove any surrounding whitespace
            line = line.strip()
            # strip any comment
            if '#' in line:
                line = line[:line.index('#')]
            # determine start of next transaction
            if transaction_start.match(line) is not None:
                if len(lines) > 0:
                    # parse all lines read up to this point (e.g. parse previous transaction)
                    journal_entries.append(read_journal_transaction(
                        lines, location=(path, starting_line_number)))
                    lines.clear()
                starting_line_number = line_number
            if len(line) > 0:
                lines.append(line)
        if len(lines) > 0:
            journal_entries.append(read_journal_transaction(
                lines, location=(path, starting_line_number)))

    # transactions are not necessarily ordered by date in a journal
    # so they must be sorted prior to inferring positions/currencies
    journal_entries = sorted(journal_entries, key=lambda r: r[0])

    records: List[Transaction] = []

    for entry in journal_entries:
        d, d2, ticker, position, amount, dividend, kind, location = entry
        p, position_change_direction = position

        if d2 is not None:
            if d2 < d:
                raise_parse_error(f'payout earlier than transaction ({d2} < {d})',
                                  location=location)

        if amount is not None and dividend is not None:
            if amount.symbol is None and dividend.symbol is not None:
                amount = Amount(amount.value,
                                symbol=dividend.symbol,
                                format=dividend.format)
            elif dividend.symbol is None and amount.symbol is not None:
                dividend = Amount(dividend.value,
                                  symbol=amount.symbol,
                                  format=amount.format)

        if amount is not None and amount.symbol is None:
            # infer symbol/format from previous entries
            for previous_record in reversed(records):
                if previous_record.ticker == ticker:
                    if previous_record.amount is None:
                        continue
                    amount = Amount(amount.value,
                                    symbol=previous_record.amount.symbol,
                                    format=previous_record.amount.format)
                    if dividend is not None:
                        dividend = Amount(dividend.value,
                                          symbol=previous_record.amount.symbol,
                                          format=previous_record.amount.format)
                    break

        if p is None or position_change_direction != 0:
            # infer position from previous entries
            for previous_record in reversed(records):
                if previous_record.ticker == ticker:
                    if previous_record.position is None:
                        continue
                    if p is None:
                        p = 0
                    p = previous_record.position + p * position_change_direction
                    if p < 0:
                        raise_parse_error(f'position change to negative position ({p})',
                                          location=location)
                    break

        if amount is not None and dividend is not None:
            if amount.symbol == dividend.symbol:
                logical_position = int(round(amount.value / dividend.value))
                if p is None:
                    # infer position from amount/dividend - if same currency
                    p = logical_position

                if p != logical_position:
                    raise_parse_error(f'position does not equal amount divided by dividend '
                                      f'({logical_position})',
                                      location=location)

        if p is None:
            raise_parse_error(f'position could not be inferred', location=location)

        if amount is not None and dividend is None:
            dividend = Amount(amount.value / p,
                              symbol=amount.symbol,
                              format=amount.format)

        records.append(Transaction(d, ticker, p, amount, dividend, kind, payout_date=d2))

    records = remove_redundant_journal_transactions(records)

    return records


def remove_redundant_journal_transactions(records: List[Transaction]) \
        -> List[Transaction]:
    for ticker in set([record.ticker for record in records]):
        recs = list(r for r in records if r.ticker == ticker)
        # find all entries that only record a change in position
        position_entries = list(r for r in recs if r.amount is None and r.dividend is None)

        if len(position_entries) == 0:
            continue

        # find all realized transactions (e.g. cash received or earned)
        realized_entries = list(r for r in recs if r.amount is not None or r.dividend is not None)

        if len(realized_entries) > 0:
            latest_entry = realized_entries[-1]
            latest_pos_entry = position_entries[-1]
            # at this point we no longer need to keep most of the position entries around, as we
            # have already used them to infer and determine position for each realized entry
            for entry in position_entries:
                # so each position entry dated prior to a realized entry is basically redundant
                is_redundant = False
                if entry.date < latest_entry.date:
                    is_redundant = True
                elif entry.date == latest_entry.date and entry.position == latest_entry.position:
                    is_redundant = True
                elif entry == latest_pos_entry and entry.position == latest_entry.position:
                    is_redundant = True
                if is_redundant:
                    records.remove(entry)

    return records


def read_journal_transaction(lines: List[str], *, location: Tuple[str, int]) \
        -> tuple:
    condensed_line = '  '.join(lines)
    if len(condensed_line) < 10:  # the shortest starting transaction line is "YYYY/M/D X"
        raise_parse_error('invalid transaction', location)
    datestamp_end_index = condensed_line.index(' ')
    datestamp = condensed_line[:datestamp_end_index]
    d: Optional[date] = None
    try:
        d = parse_datestamp(datestamp, strict=True)
    except ValueError:
        raise_parse_error(f'invalid date format (\'{datestamp}\')', location)
    today = datetime.today().date()
    if d > today:
        raise_parse_error(f'date set in future (\'{datestamp}\')', location)
    condensed_line = condensed_line[datestamp_end_index:].strip()
    break_separators = ['(',   # position opener
                        '[',   # secondary date opener
                        '  ',  # manually spaced (or automatically spaced by newline)
                        '\t']  # manually tabbed
    break_index = None
    try:
        # note that by including [ as a breaker, we allow additional formatting options
        # but it also requires any position () to always be the next component after ticker
        # e.g. this format is allowed:
        #   "2019/12/31 ABC [2020/01/15]"
        # but this is not:
        #   "2019/12/31 ABC [2020/01/15] (10)"
        # it must instead be:
        #   "2019/12/31 ABC (10) [2020/01/15]"
        # (the secondary date is like a tag attached to the cash amount)
        break_index = min([condensed_line.index(sep) for sep in break_separators
                           if sep in condensed_line])
    except ValueError:
        raise_parse_error(f'invalid transaction', location)
    ticker = None
    kind = Distribution.FINAL
    if break_index is not None:
        ticker = condensed_line[:break_index].strip()
        if ticker.startswith('*'):
            kind = Distribution.SPECIAL
            ticker = ticker[1:].strip()
        elif ticker.startswith('^'):
            kind = Distribution.INTERIM
            ticker = ticker[1:].strip()
        condensed_line = condensed_line[break_index:].strip()
    if ticker is None or len(ticker) == 0:
        raise_parse_error('invalid ticker format', location)
    position: Optional[int] = None
    position_change_direction = 0
    if ')' in condensed_line:
        break_index = condensed_line.index(')') + 1
        position_str = condensed_line[:break_index].strip()
        position_str = position_str[1:-1].strip()
        if position_str.startswith('+'):
            position_change_direction = 1
            position_str = position_str[1:]
        elif position_str.startswith('-'):
            position_change_direction = -1
            position_str = position_str[1:]
        try:
            position = locale.atoi(position_str)
        except ValueError:
            raise_parse_error(f'invalid position (\'{position}\')', location)
        condensed_line = condensed_line[break_index:].strip()

    if len(condensed_line) == 0:
        return d, None, ticker, (position, position_change_direction), None, None, kind, location

    amount_components = condensed_line.split('@')
    dividend: Optional[Amount] = None
    if len(amount_components) > 1:
        dividend_str, dividend_date = split_secondary_date(amount_components[1].strip())
        if dividend_date is not None:
            raise_parse_error(f'secondary date applied to dividend', location)
        dividend = split_amount(dividend_str, location=location)
        if dividend.value <= 0:
            raise_parse_error(f'negative or zero dividend (\'{dividend.value}\')', location)
    amount: Optional[Amount] = None
    d2: Optional[date] = None
    if len(amount_components) > 0:
        amount_str, amount_datestamp = split_secondary_date(amount_components[0].strip())
        if len(amount_str) > 0:
            amount = split_amount(amount_str, location=location)
            if amount.value <= 0:
                raise_parse_error(f'negative or zero amount (\'{amount.value}\')', location)
        else:
            if dividend is None:
                raise_parse_error(f'missing amount', location)
        if amount_datestamp is not None:
            try:
                d2 = parse_datestamp(amount_datestamp, strict=True)
            except ValueError:
                raise_parse_error(f'invalid date format (\'{amount_datestamp}\')', location)
    return d, d2, ticker, (position, position_change_direction), amount, dividend, kind, location


def split_secondary_date(text: str) \
        -> Tuple[str, Optional[str]]:
    m = re.search(r'\[(.*)\]', text)  # match anything encapsulated by []
    if m is None:
        return text, None
    d = m.group(1).strip()
    text = text[:m.start()] + text[m.end():]
    return text.strip(), d


def split_amount(amount: str, *, location: Tuple[str, int]) \
        -> Amount:
    symbol = None
    lhs = ''

    for c in amount:
        if c.isdigit() or (c == '+' or
                           c == '-'):
            break
        lhs += c

    amount = amount[len(lhs):]

    rhs = ''

    for c in reversed(amount):
        if c.isdigit() or (c == '+' or
                           c == '-'):
            break
        rhs = c + rhs

    amount = amount[:len(amount) - len(rhs)]

    if len(lhs) > 0:
        symbol = lhs.strip()
    if len(rhs) > 0:
        if symbol is not None:
            raise_parse_error(f'ambiguous symbol definition (\'{symbol}\' or \'{rhs.strip()}\'?)', location)
        symbol = rhs.strip()

    value: float = 0.0

    try:
        value = locale.atof(amount)
    except ValueError:
        raise_parse_error(f'invalid value (\'{amount}\')', location)

    return Amount(value, symbol, f'{lhs}%s{rhs}')


def read_nordnet_transactions(path: str, encoding: str = 'utf-8') \
        -> List[Transaction]:
    records = []

    with open(path, newline='', encoding=encoding) as file:
        reader = csv.reader(file, delimiter='\t')

        next(reader)  # skip headers

        line_number = 1

        for row in reader:
            line_number += 1

            if len(row) == 0:
                # skip empty rows
                continue

            transactional_type = str(row[4]).strip()

            required_transactional_types = [
                'UDB.'  # danish
                # todo: type descriptions for other languages (swedish etc.)
            ]

            if not any(t == transactional_type for t in required_transactional_types):
                continue

            records.append(
                read_nordnet_transaction(row, location=(path, line_number)))

    return records


def read_nordnet_transaction(record: List[str], *, location: Tuple[str, int]) \
        -> Transaction:
    if len(record) < 12:
        raise_parse_error(f'unexpected number of columns ({len(record)} > 12)', location)

    date_value = str(record[2 if IMPORT_EX_DATE else 3]).strip()
    ticker = str(record[5]).strip()
    position_value = str(record[8]).strip()
    dividend_value = str(record[9]).strip()
    amount_value = str(record[12]).strip()
    amount_symbol = str(record[13]).strip()
    transaction_text = str(record[19]).strip()

    # hack: some numbers may show as e.g. '1.500' which atof will parse as 1.5,
    #       when in fact it should be parsed as 1.500,00 as per danish locale
    #       so this attempts to negate that issue by removing all dot-separators,
    #       but leaving comma-decimal separator
    amount_value = amount_value.replace('.', '')
    dividend_value = dividend_value.replace('.', '')

    # parse date; expects format '2018-03-19'
    d = datetime.strptime(date_value, "%Y-%m-%d").date()

    prev = locale.getlocale(locale.LC_NUMERIC)

    # Nordnet will provide numbers and data depending on user; set numeric locale accordingly
    # (currently assumes danish locale)
    trysetlocale(locale.LC_NUMERIC, ['da_DK', 'da-DK', 'da'])

    position = locale.atoi(position_value)
    amount = locale.atof(amount_value)
    dividend = locale.atof(dividend_value)

    locale.setlocale(locale.LC_NUMERIC, prev)

    transaction_text_components = transaction_text.split(' ')

    if transaction_text_components[-1].startswith('/'):
        # hack: the transaction text is sometimes split like "USD /SH"
        dividend_symbol = transaction_text_components[-2]
        dividend_rate = transaction_text_components[-3]
    else:
        dividend_symbol = transaction_text_components[-1].split('/')[0]
        dividend_rate = transaction_text_components[-2]

    # hack: for this number, it is typically represented using period for decimals
    #       but occasionally a comma sneaks in- we assume that is an error and correct it
    dividend_rate = dividend_rate.replace(',', '.')

    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    try:
        dividend_rate = locale.atof(dividend_rate)
    except ValueError:
        raise_parse_error(f'unexpected transaction text', location)

    locale.setlocale(locale.LC_NUMERIC, prev)

    if dividend != dividend_rate:
        raise_parse_error(f'ambiguous dividend ({dividend} or {dividend_rate}?)', location)

    return Transaction(
        d, ticker, position,
        Amount(amount, symbol=amount_symbol, format=f'%s {amount_symbol}'),
        Amount(dividend, symbol=dividend_symbol, format=f'%s {dividend_symbol}'))


def write(records: List[Transaction], file, *, condensed: bool = False) -> None:
    for record in records:
        indicator = ''
        if record.kind is Distribution.SPECIAL:
            indicator = '* '
        elif record.kind is Distribution.INTERIM:
            indicator = '^ '
        datestamp = record.date.strftime('%Y/%m/%d')
        line = f'{datestamp} {indicator}{record.ticker} ({record.position})'
        if not condensed:
            print(line, file=file)
        amount_display = ''
        if record.amount is not None:
            payout_display = format_amount(record.amount.value, trailing_zero=False, rounded=False)
            if record.amount.format is not None:
                payout_display = record.amount.format % payout_display
            amount_display += payout_display
        if record.dividend is not None:
            dividend_display = format_amount(record.dividend.value, trailing_zero=False, rounded=False)
            if record.dividend.format is not None:
                dividend_display = record.dividend.format % dividend_display
            amount_display += f' @ {dividend_display}'
        if len(amount_display) > 0:
            amount_line = f'  {amount_display}'
            if not condensed:
                print(amount_line, file=file)
            else:
                line += amount_line
        if condensed:
            print(line)
        if record != records[-1] and not condensed:
            print(file=file)
