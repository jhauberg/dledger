import csv
import re
import locale

from dledger.localeutil import trysetlocale
from dledger.formatutil import format_amount
from dledger.fileutil import fileencoding

from dataclasses import dataclass
from datetime import datetime

from typing import List, Tuple, Optional

SUPPORTED_TYPES = ['journal', 'native', 'nordnet']


@dataclass(frozen=True)
class Amount:
    value: float
    symbol: Optional[str] = None
    format: Optional[str] = None


@dataclass(frozen=True, unsafe_hash=True)
class Transaction:
    """ Represents a transaction. """

    date: datetime.date
    ticker: str
    position: int
    amount: Optional[Amount] = None
    dividend: Optional[Amount] = None
    is_special: bool = False


def transactions(path: str, kind: str) \
        -> List[Transaction]:
    """ Return a list of records imported from a file. """

    encoding = fileencoding(path)

    if encoding is None or len(encoding) == 0:
        raise ValueError(f'Path could not be read: \'{path}\'')

    if kind == 'journal':
        return read_journal_transactions(path, encoding)
    elif kind == 'native':
        return read_native_transactions(path, encoding)
    elif kind == 'nordnet':
        return read_nordnet_transactions(path, encoding)

    return []


def raise_parse_error(error: str, location: Tuple[str, int]) -> None:
    raise ValueError(f'{location[0]}:{location[1]} {error}')


def read_journal_transactions(path: str, encoding: str = 'utf-8') \
        -> List[Transaction]:
    try:
        # default to system locale, if able
        locale.setlocale(locale.LC_ALL, '')
    except:
        # fallback to US locale
        trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    journal_entries = []

    transaction_start = re.compile(r'[0-9]+[-/][0-9]+[-/][0-9]+')

    with open(path, newline='', encoding=encoding) as file:
        starting_line_number = None
        line_number = 0
        lines = []
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

    records = []
    for entry in journal_entries:
        date, ticker, position, amount, dividend, is_special, location = entry
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
                    break

        if amount is not None and dividend is not None:
            if amount.symbol == dividend.symbol:
                logical_position = int(round(amount.value / dividend.value))
                if position is None:
                    # infer position from amount/dividend - if same currency
                    position = logical_position

                if position != logical_position:
                    raise raise_parse_error(f'position does not match amount/dividend '
                                            f'({logical_position})',
                                            location=location)

        if position is None:
            raise raise_parse_error(f'position could not be inferred', location=location)

        records.append(Transaction(date, ticker, position, amount, dividend, is_special))

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
    if len(condensed_line) < 10:
        raise_parse_error('Invalid transaction', location)
    datestamp = condensed_line[:10]
    date = None
    try:
        date = datetime.strptime(datestamp, "%Y/%m/%d").date()
    except ValueError:
        try:
            date = datetime.strptime(datestamp, "%Y-%m-%d").date()
        except ValueError:
            raise_parse_error(f'Invalid date format (\'{datestamp}\')', location)
    condensed_line = condensed_line[10:].strip()
    break_separators = ['(', '  ', '\t']
    break_index = min(condensed_line.index(sep) for sep in break_separators if sep in condensed_line)
    ticker = None
    is_special = False
    if break_index is not None:
        ticker = condensed_line[:break_index].strip()
        if ticker.startswith('*'):
            is_special = True
            ticker = ticker[1:].strip()
        condensed_line = condensed_line[break_index:].strip()
    if ticker is None or len(ticker) == 0:
        raise_parse_error('Invalid ticker format', location)
    position = None
    position_change_direction = 0
    if ')' in condensed_line:
        break_index = condensed_line.index(')') + 1
        position = condensed_line[:break_index].strip()
        position = position[1:-1].strip()
        if position.startswith('+'):
            position_change_direction = 1
            position = position[1:]
        elif position.startswith('-'):
            position_change_direction = -1
            position = position[1:]
        try:
            position = locale.atoi(position)
        except ValueError:
            raise_parse_error(f'Invalid position (\'{position}\')', location)
        condensed_line = condensed_line[break_index:].strip()

    if len(condensed_line) == 0:
        return date, ticker, (position, position_change_direction), None, None, is_special, location

    amount_components = condensed_line.split('@')
    amount = None
    if len(amount_components) > 0:
        amount = amount_components[0].strip()
        amount = split_amount(amount, location=location)
        if amount.value < 0:
            raise_parse_error(f'Invalid amount (\'{amount}\')', location)
    dividend = None
    if len(amount_components) > 1:
        dividend = amount_components[1].strip()
        dividend = split_amount(dividend, location=location)
        if dividend.value < 0:
            raise_parse_error(f'Invalid dividend (\'{amount}\')', location)

    return date, ticker, (position, position_change_direction), amount, dividend, is_special, location


def split_amount(amount: str, *, location: Tuple[str, int]) \
        -> Amount:
    symbol = None
    lhs = ''

    for c in amount:
        if c.isdigit():
            break
        lhs += c

    amount = amount[len(lhs):]

    rhs = ''

    for c in reversed(amount):
        if c.isdigit():
            break
        rhs = c + rhs

    amount = amount[:len(amount) - len(rhs)]

    if len(lhs) > 0:
        symbol = lhs.strip()
    if len(rhs) > 0:
        if symbol is not None:
            raise_parse_error(f'ambiguous symbol definition ({rhs.strip()})', location)
        symbol = rhs.strip()

    value = None

    try:
        value = locale.atof(amount)
    except ValueError:
        raise_parse_error(f'Invalid value (\'{amount}\')', location)

    fmt = f'{lhs}%s{rhs}'

    return Amount(value, symbol, fmt)


def read_native_transactions(path: str, encoding: str = 'utf-8') \
        -> List[Transaction]:
    records = []

    with open(path, newline='', encoding=encoding) as file:
        reader = csv.reader(file, delimiter='\t')
        line_number = 0

        for row in reader:
            line_number += 1

            if len(row) == 0:
                # skip empty rows
                continue

            row_as_str = ', '.join(row).strip()

            if row_as_str.startswith('#'):
                # skip this row
                continue

            records.append(
                read_native_transaction(row, location=(path, line_number)))

    return records


def read_native_transaction(record: List[str], *, location: Tuple[str, int]) \
        -> Transaction:
    if len(record) < 4:
        raise_parse_error(f'Unexpected number of columns ({len(record)} < 4)', location)

    date_value = str(record[0]).strip()
    ticker_value = str(record[1]).strip()
    position_value = str(record[2]).strip()
    amount_value = str(record[3]).strip()

    if len(date_value) == 0:
        raise_parse_error('Blank date field', location)
    if len(ticker_value) == 0:
        raise_parse_error('Blank ticker field', location)
    if len(position_value) == 0:
        raise_parse_error('Blank position field', location)
    if len(amount_value) == 0:
        raise_parse_error('Blank amount field', location)

    ticker = ticker_value

    special = amount_value.endswith('*')

    if special:
        amount_value = amount_value[:-1].strip()

    date = None

    try:
        # parse date; expects format '2018-03-19'
        date = datetime.strptime(date_value, "%Y-%m-%d").date()
    except ValueError:
        raise_parse_error(f'Invalid date format (\'{date_value}\')', location)

    prev_locale = locale.getlocale(locale.LC_NUMERIC)

    # parse numeric values in US locale
    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    position = None

    try:
        position = locale.atoi(position_value)
    except ValueError:
        raise_parse_error(f'Invalid position (\'{position_value}\')', location)

    amount = None

    try:
        amount = locale.atof(amount_value)
    except ValueError:
        raise_parse_error(f'Invalid amount (\'{amount_value}\')', location)

    locale.setlocale(locale.LC_NUMERIC, prev_locale)

    return Transaction(date, ticker, position, amount, is_special=special)


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
        raise_parse_error(f'Unexpected number of columns ({len(record)} > 12)', location)

    date_value = str(record[3]).strip()
    ticker = str(record[5]).strip()
    position_value = str(record[8]).strip()
    amount_value = str(record[12]).strip()

    # hack: some numbers may show as e.g. '1.500' which atof will parse as 1.5,
    #       when in fact it should be parsed as 1.500,00 as per danish locale
    #       so this attempts to negate that issue by removing all dot-separators,
    #       but leaving comma-decimal separator
    amount_value = amount_value.replace('.', '')

    # parse date; expects format '2018-03-19'
    date = datetime.strptime(date_value, "%Y-%m-%d").date()

    prev = locale.getlocale(locale.LC_NUMERIC)

    # Nordnet will provide numbers and data depending on user; set numeric locale accordingly
    # (currently assumes danish locale)
    trysetlocale(locale.LC_NUMERIC, ['da_DK', 'da-DK', 'da'])

    position = locale.atoi(position_value)
    amount = locale.atof(amount_value)

    locale.setlocale(locale.LC_NUMERIC, prev)

    return Transaction(date, ticker, position, amount)


def export(records: List[Transaction], filename: str = 'export.tsv', *, pretty: bool = False):
    """ Write records to file.

    Optionally formatting for humans.
    """

    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file, delimiter='\t')

        prev_locale = locale.getlocale(locale.LC_NUMERIC)

        trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

        rows: List[Tuple[str, ...]] = []

        for transaction in records:
            date_repr = transaction.date.strftime('%Y-%m-%d')

            row = (str(date_repr),
                   str(transaction.ticker),
                   str(transaction.position),
                   format_amount(transaction.amount.value))

            rows.append(row)

        if pretty:
            column_widths: List[int] = []

            for row in rows:
                widths = [len(str(column)) for column in row]

                if len(column_widths) > 0:
                    for i, width in enumerate(widths):
                        if column_widths[i] < width:
                            column_widths[i] = width
                else:
                    column_widths = widths

            aligned_rows = [
                # left-align columns 1-2
                # right-align columns 3-4
                tuple(column.ljust(column_widths[i]) if i == 0 or i == 1 else
                      column.rjust(column_widths[i]) if i == 2 or i == 3 else
                      column
                      for i, column in enumerate(row))
                for row in rows
            ]

            rows = aligned_rows

        for row in rows:
            writer.writerow(row)

        locale.setlocale(locale.LC_NUMERIC, prev_locale)
