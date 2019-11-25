#!/usr/bin/env python3

"""
usage: dledger report         <journal>... [--period=<interval>] [-V]
                                           [--monthly | --quarterly | --annual | --weighted]
                                           [--without-forecast]
       dledger chart <ticker> <journal>... [--period=<interval>] [-V]
                                           [--without-forecast]
       dledger stats          <journal>... [--period=<interval>] [-V]
       dledger print          <journal>... [--condensed] [-V]
       dledger convert        <file>...    [--type=<name>] [-V]
                                           [--output=<journal>]

OPTIONS:
     --type=<name>        Specify type of transaction data [default: journal]
     --output=<journal>   Specify journal filename [default: ledger.journal]
  -p --period=<interval>  Specify reporting date interval
  -a --annual             Show income by year
  -q --quarterly          Show income by quarter
  -m --monthly            Show income by month
  -w --weighted           Show income by weight
     --without-forecast   Show only realized income
  -V --verbose            Show diagnostic messages
  -h --help               Show program help
  -v --version            Show program version

See https://github.com/jhauberg/dledger for additional details.
"""

import sys
import locale

from datetime import date

from docopt import docopt  # type: ignore

from dledger import __version__
from dledger.dateutil import parse_period
from dledger.localeutil import trysetlocale
from dledger.report import (
    print_simple_report,
    print_simple_annual_report, print_simple_monthly_report, print_simple_quarterly_report,
    print_simple_weight_by_ticker,
    print_simple_chart,
    print_stats
)
from dledger.projection import (
    scheduled_transactions
)
from dledger.journal import (
    Transaction, write, read, SUPPORTED_TYPES
)

from typing import List, Tuple, Iterable, Optional


def filter_by_period(records: Iterable[Transaction],
                     interval: Optional[Tuple[Optional[date], Optional[date]]]) \
        -> Iterable[Transaction]:
    if interval is None:
        return records

    starting, ending = interval

    if starting is not None:
        # inclusive of starting date
        records = filter(lambda r: starting <= r.date, records)
    if ending is not None:
        # exclusive of ending date
        records = filter(lambda r: r.date < ending, records)

    return records


def main() -> None:
    """ Entry point for invoking the command-line interface. """

    if sys.version_info < (3, 8):
        sys.exit('Python 3.8+ required')

    args = docopt(__doc__, version='dledger ' + __version__.__version__)

    try:
        # default to system locale, if able
        locale.setlocale(locale.LC_ALL, '')
    except (locale.Error, ValueError):
        # fallback to US locale
        trysetlocale(locale.LC_NUMERIC, ['en_US', 'en-US', 'en'])

    input_paths = (args['<file>']
                   if args['convert'] else
                   args['<journal>'])

    input_type = args['--type']
    is_verbose = args['--verbose']

    records: List[Transaction] = []

    for input_path in input_paths:
        # note that --type defaults to 'journal' for all commands
        # (only convert supports setting type explicitly)
        if input_type not in SUPPORTED_TYPES:
            sys.exit(f'Transaction type is not supported: {input_type}')

        records.extend(read(input_path, input_type))

    records = sorted(records)

    if len(records) == 0:
        if is_verbose:
            print('No valid records', file=sys.stderr)

        sys.exit(0)

    if args['convert']:
        with open(args['--output'], 'w', newline='') as file:
            write(records, file=file)

        sys.exit(0)

    if args['print']:
        write(records, file=sys.stdout, condensed=args['--condensed'])

        sys.exit(0)

    interval = args['--period']

    if interval is not None:
        interval = parse_period(interval)

    if args['stats']:
        # filter down all records by --period, not just transactions
        records = list(filter_by_period(records, interval))

        print_stats(records, journal_paths=input_paths)

        sys.exit(0)

    transactions = list(filter(
        lambda r: r.amount is not None, records))

    if not args['--without-forecast']:
        transactions.extend(
            scheduled_transactions(records))

    transactions = sorted(filter_by_period(transactions, interval))

    if args['report']:
        if args['--weighted']:
            print_simple_weight_by_ticker(transactions)
        elif args['--annual']:
            print_simple_annual_report(transactions)
        elif args['--monthly']:
            print_simple_monthly_report(transactions)
        elif args['--quarterly']:
            print_simple_quarterly_report(transactions)
        else:
            print_simple_report(transactions)

        sys.exit(0)

    if args['chart']:
        ticker = args['<ticker>']
        transactions = list(filter(
            lambda r: r.ticker == ticker, transactions))

        print_simple_chart(transactions)

        sys.exit(0)

    sys.exit(0)


if __name__ == '__main__':
    main()
