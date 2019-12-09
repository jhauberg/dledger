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

    date: date
    ticker: str
    position: int
    amount: Optional[Amount] = None
    dividend: Optional[Amount] = None
    kind: Distribution = Distribution.FINAL

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

    transaction_start = re.compile(r'[0-9]+[-/][0-9]+[-/][0-9]+')

    with open(path, newline='', encoding=encoding) as file:
        starting_line_number = -1
        line_number = 0
        lines: List[str] = []
        while line := file.readline():
            line_number += 1
            # remove any surrounding whitespace
            line = line.strip()
            # strip any comment
            if '#' in line:
                line = line[:line.index('#')]
            # determine start of transaction
            if transaction_start.match(line) is not None:
                if len(lines) > 0:
                    # parse all lines read up to this point
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
        d, ticker, position, amount, dividend, kind, location = entry
        position, position_change_direction = position

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

        if position is None or position_change_direction != 0:
            # infer position from previous entries
            for previous_record in reversed(records):
                if previous_record.ticker == ticker:
                    if previous_record.position is None:
                        continue
                    if position is None:
                        position = 0
                    position = previous_record.position + position * position_change_direction
                    if position < 0:
                        raise_parse_error(f'position change to negative position ({position})',
                                          location=location)
                    break

        if amount is not None and dividend is not None:
            if amount.symbol == dividend.symbol:
                logical_position = int(round(amount.value / dividend.value))
                if position is None:
                    # infer position from amount/dividend - if same currency
                    position = logical_position

                if position != logical_position:
                    raise_parse_error(f'position does not match amount/dividend '
                                      f'({logical_position})',
                                      location=location)

        if position is None:
            raise_parse_error(f'position could not be inferred', location=location)

        records.append(Transaction(d, ticker, position, amount, dividend, kind))

    position_change_entries = list(filter(
        lambda r: r.amount is None and position is not None, records))

    latest_position_change_entries = []
    for ticker in set([record.ticker for record in position_change_entries]):
        fs = list(filter(lambda r: r.ticker == ticker, position_change_entries))
        latest_position_change_entries.append(fs[-1])

    for r in position_change_entries:
        if r in latest_position_change_entries:
            continue
        records.remove(r)

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
    condensed_line = condensed_line[datestamp_end_index:].strip()
    break_separators = ['(', '  ', '\t']
    break_index = None
    try:
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
        return d, ticker, (position, position_change_direction), None, None, kind, location

    amount_components = condensed_line.split('@')
    amount: Optional[Amount] = None
    if len(amount_components) > 0:
        amount_str = amount_components[0].strip()
        amount = split_amount(amount_str, location=location)
        if amount.value < 0:
            raise_parse_error(f'invalid amount (\'{amount.value}\')', location)
    dividend: Optional[Amount] = None
    if len(amount_components) > 1:
        dividend_str = amount_components[1].strip()
        dividend = split_amount(dividend_str, location=location)
        if dividend.value < 0:
            raise_parse_error(f'invalid dividend (\'{dividend.value}\')', location)

    return d, ticker, (position, position_change_direction), amount, dividend, kind, location


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

    date_value = str(record[3]).strip()
    ticker = str(record[5]).strip()
    position_value = str(record[8]).strip()
    dividend_value = str(record[9]).strip()
    amount_value = str(record[12]).strip()
    amount_symbol = str(record[13]).strip()
    dividend_symbol = str(record[19]).strip()

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

    dividend_symbol = dividend_symbol.split(' ')[-1].split('/')[0]

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
            payout_display = format_amount(record.amount.value, trailing_zero=False)
            if record.amount.format is not None:
                payout_display = record.amount.format % payout_display
            amount_display += payout_display
        if record.dividend is not None:
            dividend_display = format_amount(record.dividend.value, trailing_zero=False)
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
