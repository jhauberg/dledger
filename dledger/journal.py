import csv
import re
import math
import locale
import os

from dledger.localeutil import trysetlocale
from dledger.formatutil import format_amount, decimalplaces
from dledger.fileutil import fileencoding
from dledger.dateutil import parse_datestamp

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal

from typing import List, Union, Tuple, Optional, Any, Dict, Iterable
from enum import Enum

SUPPORTED_TYPES = ['journal', 'nordnet']

IMPORT_EX_DATE = False  # whether to import ex- or payout date when reading non-journal transactions


class Distribution(Enum):
    """ Represents the type of a dividend distribution. """

    FINAL = 0
    INTERIM = 1
    SPECIAL = 2


@dataclass(frozen=True, unsafe_hash=True)
class Amount:
    """ Represents a cash amount. """

    value: Union[float, int]
    places: Optional[int] = None
    symbol: Optional[str] = None
    fmt: Optional[str] = None


@dataclass(frozen=True)
class EntryAttributes:
    """ Represents a set of attributes describing some facts about a journal entry.

    These are properties that can only be known at parse-time, as a journal entry may undergo
    several processing steps ultimately changing its final representation.

    For example, whether a record is preliminary or not cannot be deduced after processing,
    as it will end up having a generated amount attached to it (where it would otherwise be None).
    """

    location: Tuple[str, int]  # journal:linenumber
    is_preliminary: bool = False  # True if amount component left blank intentionally
    preliminary_amount: Optional[Amount] = None


@dataclass(frozen=True, unsafe_hash=True)
class Transaction:
    """ Represents a transactional record. """

    entry_date: date  # no assumption whether this is payout, ex-date or other
    ticker: str
    position: float
    amount: Optional[Amount] = None
    dividend: Optional[Amount] = None
    kind: Distribution = Distribution.FINAL
    payout_date: Optional[date] = None
    ex_date: Optional[date] = None
    entry_attr: Optional[EntryAttributes] = None

    def __lt__(self, other):  # type: ignore
        def is_nondividend_transaction(r: Transaction) -> bool:
            return r.amount is None and r.dividend is None

        def literal_location(r: Transaction) -> Tuple[str, int]:
            return r.entry_attr.location if r.entry_attr is not None else ('', 0)
        # sort by primary date and always put buy/sell transactions later if on same date
        # e.g.  2019/01/01 ABC (+10)
        #       2019/01/01 ABC (10)  $ 1
        #   =>
        #       2019/01/01 ABC (10)  $ 1
        #       2019/01/01 ABC (+10)
        # thirdly, take literal order in journal into account (both linenumber and path)
        # finally, to stabilize sorting in all cases, use ticker for alphabetical ordering
        return (self.entry_date, is_nondividend_transaction(self), literal_location(self), self.ticker) < \
               (other.entry_date, is_nondividend_transaction(other), literal_location(other), other.ticker)


class ParseError(Exception):
    def __init__(self, message: str, location: Tuple[str, int]):
        super().__init__(f'{os.path.abspath(location[0])}:{location[1]} {message}')


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


def read_journal_transactions(path: str, encoding: str = 'utf-8') \
        -> List[Transaction]:
    journal_entries = []

    # note that this pattern will initially let inconsistent formatting pass (e.g. 2019/12-1)
    # but will eventually raise a formatting error later on (it is faster to skip validation
    # through parse_datestamp at this point)
    transaction_start = re.compile(r'[0-9]+[-/][0-9]+[-/][0-9]+')

    with open(path, newline='', encoding=encoding) as file:
        starting_line_number = -1
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
                # we will reach this line *before* parsing the first actual transaction,
                # even if zero lines above it, which means starting_line_number can only equal -1
                # if we never reach a valid transaction
                starting_line_number = line_number
            if len(line) > 0:
                lines.append(line)
        if len(lines) > 0:
            if starting_line_number == -1:
                # find the line number of the first line with content
                starting_line_number = line_number - len(lines) + 1
            journal_entries.append(read_journal_transaction(
                lines, location=(path, starting_line_number)))

    # transactions are not necessarily ordered by date in a journal
    # so they must be sorted prior to inferring positions/currencies
    # note that position change entries are always sorted to occur *after*
    # any realized transaction on the same date (see Transaction.__lt__)
    journal_entries = sorted(journal_entries, key=lambda r: (r[0], r[5] is None and r[6] is None))

    records: List[Transaction] = []

    def truncate_floating_point(value: float, *, places: int = 2) -> float:
        v = Decimal(value)
        v = round(v, places)
        return float(v)

    for entry in journal_entries:
        d, d2, d3, ticker, position, amount, dividend, kind, location = entry
        p, p_direction = position

        if p is None or p_direction != 0:
            # infer position from previous entries
            # todo: this sorting rule occurs in multiple places; should consolidate
            by_ex_date = sorted(records, key=lambda r: (
                r.ex_date if r.ex_date is not None else r.entry_date,
                r.amount is None and r.dividend is None
            ))
            for previous_record in reversed(by_ex_date):
                if previous_record.ticker == ticker:
                    if previous_record.position is None:
                        continue
                    if d3 is not None and previous_record.entry_date > d3:
                        continue
                    if p is None:
                        p = 0
                    p = truncate_floating_point(previous_record.position + p * p_direction)
                    if p < 0:
                        raise ParseError(f'position change to negative position ({p})', location)
                    break

        if amount is not None and dividend is not None:
            if amount.symbol == dividend.symbol:
                inferred_p = amount.value / dividend.value
                if p is not None:
                    # determine whether position equates (close enough) to the inferred position
                    # tolerance based on fractional precision from Robinhood/M1
                    # see https://robinhood.com/us/en/support/articles/66zKxGmw7zjdkFXEcGYksl/fractional-shares/
                    # or https://support.m1finance.com/hc/en-us/articles/221053227-Explanation-of-Fractional-Shares
                    # todo: Robinhood rounds to nearest penny, so this ambiguity check might not work
                    #       e.g. 1 penny = $ 0.01
                    #       so if you your position would amount to 0.006, you would get 0.01
                    #       but also hit this error, because your position is 0.006/div, not 0.01/div
                    if not math.isclose(p, inferred_p, abs_tol=0.000001):
                        raise ParseError(f'ambiguous position ({p} or {inferred_p}?)', location)
                else:
                    p = truncate_floating_point(inferred_p)

        if p is None:
            raise ParseError(f'position could not be inferred', location)

        if amount is not None and dividend is None:
            inferred_dividend = truncate_floating_point(amount.value / p, places=2)
            dividend = Amount(inferred_dividend,
                              places=decimalplaces(inferred_dividend),
                              symbol=amount.symbol,
                              fmt=amount.fmt)

        if d2 is not None and d3 is not None:
            if d2 < d3:
                raise ParseError(f'payout date dated earlier than ex-date', location)

        is_incomplete = False
        prelim_amount = None
        if (amount is None or amount is not None and amount.value == 0) and dividend is not None:
            prelim_amount = amount
            is_incomplete = True

        entry_attribs = EntryAttributes(
            location, is_preliminary=is_incomplete, preliminary_amount=prelim_amount)

        records.append(
            Transaction(d, ticker, p,
                        amount if prelim_amount is None else None,
                        dividend, kind,
                        payout_date=d2, ex_date=d3,
                        entry_attr=entry_attribs))

    records = remove_redundant_journal_transactions(records)

    return records


def remove_redundant_journal_transactions(records: List[Transaction]) \
        -> List[Transaction]:
    for ticker in set([record.ticker for record in records]):
        recs = list(r for r in records if r.ticker == ticker)
        # find all entries that only record a change in position
        position_records = list(r for r in recs if r.amount is None and r.dividend is None)

        if len(position_records) == 0:
            continue

        # find all dividend transactions (e.g. cash received or earned)
        realized_records = list(r for r in recs if r.amount is not None or r.dividend is not None)

        if len(realized_records) > 0:
            latest_record = realized_records[-1]
            # at this point we no longer need to keep some of the position entries around,
            # as we have already used them to infer and determine position for each realized entry
            for record in position_records:
                # so each position entry dated prior to a dividend entry is basically redundant
                if record.position == 0:
                    # unless it's a closer, in which case we have to keep it around in any case
                    # (e.g. see example/strategic.journal)
                    continue
                if latest_record.ex_date is not None and record.entry_date >= latest_record.ex_date:
                    continue
                is_redundant = False
                if record.entry_date < latest_record.entry_date:
                    is_redundant = True
                elif record.entry_date == latest_record.entry_date and \
                        math.isclose(record.position, latest_record.position, abs_tol=0.000001):
                    is_redundant = True
                if is_redundant:
                    records.remove(record)

    return records


def read_journal_transaction(lines: List[str], *, location: Tuple[str, int]) \
        -> Tuple[date, Optional[date], Optional[date], str, Tuple[Optional[float], int], Optional[Amount], Optional[Amount], Distribution, Tuple[str, int]]:
    condensed_line = '  '.join(lines)
    if len(condensed_line) < 10:  # the shortest starting transaction line is "YYYY/M/D X"
        raise ParseError('invalid transaction', location)
    datestamp_end_index = condensed_line.index(' ')
    datestamp = condensed_line[:datestamp_end_index]
    try:
        d = parse_datestamp(datestamp, strict=True)
    except ValueError:
        raise ParseError(f'invalid date format (\'{datestamp}\')', location)
    condensed_line = condensed_line[datestamp_end_index:].strip()
    break_separators = ['(',   # position opener
                        '[',   # secondary date opener
                        '  ',  # manually spaced (or automatically spaced by newline)
                        '\t']  # manually tabbed
    try:
        # note that by including [ as a breaker, we allow additional formatting options
        # but it also requires any position () to always be the next component after ticker
        # e.g. this format is allowed:
        #   "2019/12/31 ABC [2020/01/15] $ 1"
        # but this is not:
        #   "2019/12/31 ABC [2020/01/15] (10) $ 1"
        # it must instead be:
        #   "2019/12/31 ABC (10) [2020/01/15] $ 1"
        # (the secondary date is like a tag attached to the cash amount)
        break_index = min([condensed_line.index(sep) for sep in break_separators
                           if sep in condensed_line])
    except ValueError:
        raise ParseError(f'invalid transaction', location)
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
        raise ParseError('invalid ticker format', location)
    position: Optional[float] = None
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
            position = locale.atof(position_str)
        except ValueError:
            raise ParseError(f'invalid position (\'{position_str}\')', location)
        condensed_line = condensed_line[break_index:].strip()

    if len(condensed_line) == 0:
        return d, None, None, ticker, (position, position_change_direction), None, None, kind, location

    amount_components = condensed_line.split('@')
    dividend: Optional[Amount] = None
    d3: Optional[date] = None
    if len(amount_components) > 1:
        dividend_str, dividend_datestamp = parse_amount_date(amount_components[1].strip())
        if len(dividend_str) > 0:
            dividend = parse_amount(dividend_str, location=location)
            if dividend.value <= 0:
                raise ParseError(f'negative or zero dividend (\'{dividend.value}\')', location)
        if dividend_datestamp is not None:
            try:
                d3 = parse_datestamp(dividend_datestamp, strict=True)
            except ValueError:
                raise ParseError(f'invalid date format (\'{dividend_datestamp}\')', location)
    amount: Optional[Amount] = None
    d2: Optional[date] = None
    if len(amount_components) > 0:
        amount_str, amount_datestamp = parse_amount_date(amount_components[0].strip())
        if len(amount_str) > 0:
            amount = parse_amount(amount_str, location=location)
            if amount.value < 0:
                raise ParseError(f'negative amount (\'{amount.value}\')', location)
        else:
            if dividend is None:
                raise ParseError(f'missing amount', location)
        if amount_datestamp is not None:
            try:
                d2 = parse_datestamp(amount_datestamp, strict=True)
            except ValueError:
                raise ParseError(f'invalid date format (\'{amount_datestamp}\')', location)
    return d, d2, d3, ticker, (position, position_change_direction), amount, dividend, kind, location


def parse_amount_date(text: str) \
        -> Tuple[str, Optional[str]]:
    m = re.search(r'\[(.*)\]', text)  # match anything encapsulated by []
    if m is None:
        return text, None
    d = m.group(1).strip()
    text = text[:m.start()] + text[m.end():]
    return text.strip(), d


def parse_amount(amount: str, *, location: Tuple[str, int]) \
        -> Amount:
    def isbeginning(char: str) -> bool:
        return char.isdecimal() or (char == '+' or
                                    char == '-')
    symbol: Optional[str] = None
    # accumulate right-hand side of string by going through each character, in reverse
    rhs = ''
    for c in reversed(amount):
        # until finding the first occurrence of beginning of an amount
        if isbeginning(c):
            break
        rhs = c + rhs
    # assume first part of string the amount and remainder the symbol
    amount = amount[:len(amount) - len(rhs)]
    # accumulate left-hand side of string by going through each character
    lhs = ''
    for c in amount:
        if isbeginning(c):
            break
        lhs += c
    # assume remainder of string is the amount and lhs is the symbol
    amount = amount[len(lhs):]
    # parse out symbol using left/right-hand sides of the string
    if len(rhs) > 0:
        symbol = rhs.strip()
    if len(lhs) > 0:
        if symbol is not None:
            # a symbol can exist on both sides of the string, but then which one do we use?
            raise ParseError(f'ambiguous symbol definition (\'{symbol}\' or \'{lhs.strip()}\'?)', location)
        symbol = lhs.strip()
    if symbol is None or len(symbol) == 0:
        raise ParseError(f'missing symbol definition', location)

    # user-entered format; either lhs or rhs will always be empty at this point
    fmt = f'{lhs}%s{rhs}'

    if len(amount) > 0:
        # an amount has been entered
        try:
            value = locale.atof(amount)
        except ValueError:
            raise ParseError(f'invalid value (\'{amount}\')', location)
    else:
        value = int(0)  # note int-type
        # default/fallback format
        # (when no entered amount, no formatting can be determined other than symbol)
        fmt = f'%s {symbol}'

    return Amount(value, places=decimalplaces(amount), symbol=symbol, fmt=fmt)


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
        raise ParseError(f'unexpected number of columns ({len(record)} > 12)', location)

    date_value = str(record[2 if IMPORT_EX_DATE else 3]).strip()
    ticker = str(record[5]).strip()
    position_str = str(record[8]).strip()
    dividend_str = str(record[9]).strip()
    amount_str = str(record[12]).strip()
    amount_symbol = str(record[13]).strip()
    transaction_text = str(record[19]).strip()

    # hack: some numbers may show as e.g. '1.500' which atof will parse as 1.5,
    #       when in fact it should be parsed as 1.500,00 as per danish locale
    #       so this attempts to negate that issue by removing all dot-separators,
    #       but leaving comma-decimal separator
    amount_str = amount_str.replace('.', '')
    dividend_str = dividend_str.replace('.', '')

    # parse date; expects format '2018-03-19'
    d = datetime.strptime(date_value, "%Y-%m-%d").date()

    prev = locale.getlocale(locale.LC_NUMERIC)

    # Nordnet will provide numbers and data depending on user; set numeric locale accordingly
    # (currently assumes danish locale)
    trysetlocale(locale.LC_NUMERIC, ['da_DK', 'da-DK', 'da'])

    position = locale.atoi(position_str)
    amount = locale.atof(amount_str)
    dividend = locale.atof(dividend_str)

    locale.setlocale(locale.LC_NUMERIC, prev)

    transaction_text_components = transaction_text.split(' ')

    if transaction_text_components[-1].startswith('/'):
        # hack: the transaction text is sometimes split like "USD /SH"
        dividend_symbol = transaction_text_components[-2]
        dividend_rate_str = transaction_text_components[-3]
    else:
        dividend_symbol = transaction_text_components[-1].split('/')[0]
        dividend_rate_str = transaction_text_components[-2]

    # hack: for this number, it is typically represented using period for decimals
    #       but occasionally a comma sneaks in- we assume that is an error and correct it
    dividend_rate_str = dividend_rate_str.replace(',', '.')

    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    dividend_rate: Optional[float] = None

    try:
        dividend_rate = locale.atof(dividend_rate_str)
    except ValueError:
        raise ParseError(f'unexpected transaction text', location)

    locale.setlocale(locale.LC_NUMERIC, prev)

    assert dividend_rate is not None

    if dividend != dividend_rate:
        raise ParseError(f'ambiguous dividend ({dividend} or {dividend_rate}?)', location)

    return Transaction(
        d, ticker, position,
        Amount(amount, places=decimalplaces(amount_str), symbol=amount_symbol, fmt=f'%s {amount_symbol}'),
        Amount(dividend, places=decimalplaces(dividend_str), symbol=dividend_symbol, fmt=f'%s {dividend_symbol}'))


def max_decimal_places(amounts: Iterable[Optional[Amount]]) -> Optional[int]:
    places: Optional[int] = None
    values = [amount.places for amount in amounts if
              amount is not None and
              amount.places is not None]
    if len(values) > 0:
        return max(values)
    return places


def write(records: List[Transaction], file: Any, *, condensed: bool = False) -> None:
    position_decimal_places: Dict[str, Optional[int]] = dict()
    payout_decimal_places: Dict[str, Optional[int]] = dict()
    dividend_decimal_places: Dict[str, Optional[int]] = dict()
    for ticker in set([record.ticker for record in records]):
        payout_decimal_places[ticker] = max_decimal_places(
            (r.amount for r in records if r.ticker == ticker)
        )
        dividend_decimal_places[ticker] = max_decimal_places(
            (r.dividend for r in records if r.ticker == ticker)
        )
        position_decimal_places[ticker] = max(
            decimalplaces(r.position) for r in records if r.ticker == ticker
        )
    for record in records:
        indicator = ''
        if record.kind is Distribution.SPECIAL:
            indicator = '* '
        elif record.kind is Distribution.INTERIM:
            indicator = '^ '
        datestamp = record.entry_date.strftime('%Y/%m/%d')
        p_decimal_places = position_decimal_places[record.ticker]
        if p_decimal_places is not None:
            p = format_amount(record.position, trailing_zero=False, places=p_decimal_places)
        else:
            p = format_amount(record.position, trailing_zero=False, rounded=False)
        line = f'{datestamp} {indicator}{record.ticker} ({p})'
        if not condensed:
            print(line, file=file)
        amount_display = ''
        if record.payout_date is not None:
            payout_datestamp = record.payout_date.strftime('%Y/%m/%d')
            amount_display += f'[{payout_datestamp}]'
        if record.amount is not None:
            amount_decimal_places = payout_decimal_places[record.ticker]
            if amount_decimal_places is not None:
                payout_display = format_amount(record.amount.value, places=amount_decimal_places)
            else:
                payout_display = format_amount(record.amount.value, rounded=False)
            if record.amount.fmt is not None:
                payout_display = record.amount.fmt % payout_display
            amount_display += f' {payout_display}' if record.payout_date is not None else payout_display
        if record.dividend is not None:
            div_decimal_places = dividend_decimal_places[record.ticker]
            if div_decimal_places is not None:
                dividend_display = format_amount(record.dividend.value, places=div_decimal_places)
            else:
                dividend_display = format_amount(record.dividend.value, rounded=False)
            if record.dividend.fmt is not None:
                dividend_display = record.dividend.fmt % dividend_display
            amount_display += f' @ {dividend_display}' if record.payout_date is not None or record.amount is not None else f'@ {dividend_display}'
        if record.ex_date is not None:
            exdate_datestamp = record.ex_date.strftime('%Y/%m/%d')
            amount_display += f' [{exdate_datestamp}]' if record.dividend is not None else f' @ [{exdate_datestamp}]'
        if len(amount_display) > 0:
            amount_line = f' {amount_display}' if condensed else f'  {amount_display}'
            if not condensed:
                print(amount_line, file=file)
            else:
                line += amount_line
        if condensed:
            print(line, file=file)
        if record != records[-1] and not condensed:
            print(file=file)
