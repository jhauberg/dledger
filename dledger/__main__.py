#!/usr/bin/env python3

"""
usage: dledger report         <journal>... [--period=<years>] [--weighted] [-V]
       dledger chart <ticker> <journal>... [--period=<years>] [-V]
       dledger forecast       <journal>... [--weighted] [-V]
       dledger stats          <journal>... [--period=<years>]
       dledger print          <journal>
       dledger convert <file>... [--type=<name>] [--output=<journal>] [-V]

OPTIONS:
     --type=<name>       Specify type of transaction data [default: journal]
     --output=<journal>  Specify journal filename [default: ledger.journal]
     --period=<years>    Specify range of years [default: current year]
     --weighted          Show report as a weighted table
  -V --verbose           Show diagnostic messages
  -h --help              Show program help
  -v --version           Show program version

See https://github.com/jhauberg/dledger for additional details.
"""

import sys
import os
import locale

from docopt import docopt  # type: ignore

from dledger import __version__
from dledger.record import tickers, symbols
from dledger.report import generate
from dledger.projection import scheduled_transactions
from dledger.journal import (
    write, read, SUPPORTED_TYPES
)


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
    elif args['stats']:
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
    elif args['report']:
        period = args['--period']
        if period == 'current year':
            # todo: set to current year; maybe even use range() ?
            pass
        generate(records)
    elif args['chart']:
        ticker = args['<ticker>']
        pass
    elif args['forecast']:
        future_transactions = scheduled_transactions(records)
        write(future_transactions, file=sys.stdout)

    sys.exit(0)


if __name__ == '__main__':
    main()
