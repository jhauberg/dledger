#!/usr/bin/env python3

"""
usage: dledger report         <journal>... [--period=<interval>] [--monthly | --quarterly] [-V]
       dledger chart <ticker> <journal>... [--period=<interval>] [-V]
       dledger forecast       <journal>... [--period=<interval>] [--weighted] [-V]
       dledger stats          <journal>... [--period=<interval>] [-V]
       dledger print          <journal> [-V]
       dledger convert <file>... [--type=<name>] [--output=<journal>] [-V]

OPTIONS:
     --type=<name>        Specify type of transaction data [default: journal]
     --output=<journal>   Specify journal filename [default: ledger.journal]
     --period=<interval>  Specify reporting date interval
  -q --quarterly          Show income by quarter
  -m --monthly            Show income by month
  -w --weighted           Show income as a weighted table
  -V --verbose            Show diagnostic messages
  -h --help               Show program help
  -v --version            Show program version

See https://github.com/jhauberg/dledger for additional details.
"""

import sys
import os
import locale

from docopt import docopt  # type: ignore

from dledger import __version__
from dledger.record import tickers, symbols
from dledger.dateutil import parse_period
from dledger.report import (
    print_simple_annual_report, print_simple_monthly_report, print_simple_quarterly_report,
    print_simple_forecast, print_simple_weight_by_ticker, print_simple_chart
)
from dledger.projection import scheduled_transactions
from dledger.journal import (
    write, read, SUPPORTED_TYPES
)


def filter_by_period(records, interval):
    if interval is None:
        return records

    starting, ending = interval

    if starting is not None:
        records = filter(lambda r: starting <= r.date, records)
    if ending is not None:
        records = filter(lambda r: r.date <= ending, records)

    return records


def main() -> None:
    """ Entry point for invoking the command-line interface. """

    if sys.version_info < (3, 8):
        sys.exit('Python 3.8+ required')

    args = docopt(__doc__, version='dledger ' + __version__.__version__)

    input_paths = (args['<file>']
                   if args['convert'] else
                   args['<journal>'])

    input_type = args['--type']
    is_verbose = args['--verbose']

    records = []

    for input_path in input_paths:
        # note that --provider defaults to 'native' for all commands
        # (only convert supports setting provider explicitly)
        if input_type not in SUPPORTED_TYPES:
            sys.exit(f'Transaction type is not supported: {input_type}')

        records.extend(read(input_path, input_type))

    records = sorted(records, key=lambda r: r.date)

    if len(records) == 0:
        if is_verbose:
            print('No valid records', file=sys.stderr)

        sys.exit(0)

    if args['convert']:
        with open(args['--output'], 'w', newline='') as file:
            write(records, file=file)

        sys.exit(0)

    if args['print']:
        write(records, file=sys.stdout)

        sys.exit(0)

    interval = args['--period']

    if interval is not None:
        interval = parse_period(interval)

    if args['stats']:
        def print_stat_row(name: str, text: str) -> None:
            name = name.rjust(10)
            print(f'{name}: {text}')
        for n, journal_path in enumerate(input_paths):
            print_stat_row(f'Journal {n+1}', os.path.abspath(journal_path))
        try:
            lc = locale.getlocale(locale.LC_ALL)
            print_stat_row('Locale', f'{lc}')
        except:
            print_stat_row('Locale', 'Not configured')
        records = list(filter_by_period(records, interval))
        transactions = list(filter(lambda r: r.amount is not None, records))
        if len(transactions) > 0 and len(transactions) != len(records):
            print_stat_row('Records', f'{len(records)} ({len(transactions)})')
        else:
            print_stat_row('Records', f'{len(records)}')
        if len(records) > 0:
            print_stat_row('Earliest', f'{records[0].date}')
            print_stat_row('Latest', f'{records[-1].date}')
            print_stat_row('Tickers', f'{len(tickers(records))}')
            currencies = symbols(records)
            if len(currencies) > 0:
                print_stat_row('Symbols', f'{currencies}')

        sys.exit(0)

    if args['report']:
        if args['--monthly']:
            print_simple_monthly_report(records)
        elif args['--quarterly']:
            print_simple_quarterly_report(records)
        else:
            print_simple_annual_report(records)

        sys.exit(0)

    if args['chart']:
        ticker = args['<ticker>']
        transactions = list(filter(lambda r: r.amount is not None and r.ticker == ticker, records))
        print_simple_chart(transactions)

        sys.exit(0)

    if args['forecast']:
        transactions = list(filter_by_period(scheduled_transactions(records), interval))

        if args['--weighted']:
            print_simple_weight_by_ticker(transactions)
        else:
            print_simple_forecast(transactions)

        sys.exit(0)

    sys.exit(0)


if __name__ == '__main__':
    main()
