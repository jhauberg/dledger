import sys
import csv
import locale

from dividendreport.localeutil import trysetlocale
from dividendreport.formatutil import format_amount
from dividendreport.fileutil import fileencoding

from dataclasses import dataclass
from datetime import datetime

from typing import List, Tuple

SUPPORTED_PROVIDERS = ['native', 'nordnet']


@dataclass(frozen=True, unsafe_hash=True)
class Transaction:
    """ Represents a transaction that has been realized. """

    date: datetime.date
    ticker: str
    position: int
    amount: float

    def __repr__(self):
        return str((str(self.date),
                    self.ticker,
                    self.position,
                    format_amount(self.amount)))


def transactions(path: str, provider: str) \
        -> List[Transaction]:
    """ Return a list of records imported from a file. """

    encoding = fileencoding(path)

    if encoding is None or len(encoding) == 0:
        raise ValueError(f'Path could not be read: \'{path}\'')

    if provider == 'native':
        return read_native_transactions(path, encoding)
    elif provider == 'nordnet':
        return read_nordnet_transactions(path, encoding)

    return []


def read_native_transactions(path: str, encoding: str = 'utf-8') \
        -> List[Transaction]:
    records = []

    with open(path, newline='', encoding=encoding) as file:
        reader = csv.reader(file, delimiter='\t')

        for row in reader:
            if len(row) == 0:
                # skip empty rows
                continue

            row_as_str = ', '.join(row).strip()

            if row_as_str.startswith('#'):
                # skip this row
                continue

            records.append(read_native_transaction(row))

    return records


def read_native_transaction(record: List[str]) \
        -> Transaction:
    if len(record) < 4:
        raise ValueError('Unexpected number of columns')

    date_value = str(record[0]).strip()
    ticker = str(record[1]).strip()
    position_value = str(record[2]).strip()
    amount_value = str(record[3]).strip()

    # parse date; expects format '2018-03-19'
    date = datetime.strptime(date_value, "%Y-%m-%d").date()

    prev_locale = locale.getlocale(locale.LC_NUMERIC)

    trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    position = locale.atoi(position_value)
    amount = locale.atof(amount_value)

    locale.setlocale(locale.LC_NUMERIC, prev_locale)

    return Transaction(date, ticker, position, amount)


def read_nordnet_transactions(path: str, encoding: str = 'utf-8') \
        -> List[Transaction]:
    records = []

    with open(path, newline='', encoding=encoding) as file:
        reader = csv.reader(file, delimiter='\t')

        next(reader)  # skip headers

        for row in reader:
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

            records.append(read_nordnet_transaction(row))

    return records


def read_nordnet_transaction(record: List[str]) \
        -> Transaction:
    if len(record) < 12:
        raise ValueError('Unexpected number of columns')

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


def sanitize(records: List[Transaction], *, verbose: bool = False) \
        -> List[Transaction]:
    """ Return a sanitized list of records. """

    negative_records = filter(
        lambda r: r.position < 0 or r.amount < 0, records)

    for record in negative_records:
        if verbose:
            print(f'Removing record; negative position or amount: {record}', file=sys.stderr)

        records.remove(record)

    future_records = filter(
        lambda r: r.date > datetime.today().date(), records)

    for record in future_records:
        if verbose:
            print(f'Removing record; set in future: {record}', file=sys.stderr)

        records.remove(record)

    return sorted(records, key=lambda r: r.date)


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
                   format_amount(transaction.amount))

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
