#!/usr/bin/env python3

"""
usage: dledger report  <journal>... [--period=<interval>] [-V]
                                    [--monthly | --quarterly | --annual | --trailing | --weight | --sum]
                                    [--without-forecast]
                                    [--by-ticker=<ticker>]
                                    [--by-payout-date]
                                    [--in-currency=<symbol>]
       dledger stats   <journal>... [--period=<interval>] [-V]
       dledger print   <journal>... [--condensed] [-V]
       dledger convert <file>...    [--type=<name>] [-V]
                                    [--output=<journal>]

OPTIONS:
     --type=<name>            Specify type of transaction data [default: journal]
     --output=<journal>       Specify journal filename [default: ledger.journal]
  -d --period=<interval>      Specify reporting date interval
     --without-forecast       Don't include forecasted transactions
     --by-ticker=<ticker>     Show income by ticker (exclusively)
     --in-currency=<symbol>   Show income as if exchanged to currency
  -y --annual                 Show income by year
  -q --quarterly              Show income by quarter
  -m --monthly                Show income by month
     --trailing               Show income by rolling trailing 12-month totals
     --weight                 Show income by weight (per ticker)
     --sum                    Show income by totals
  -V --verbose                Show diagnostic messages
  -h --help                   Show program help
  -v --version                Show program version

See https://github.com/jhauberg/dledger for additional details.
"""

import sys
import locale

from docopt import docopt  # type: ignore

from dledger import __version__
from dledger.dateutil import parse_period
from dledger.localeutil import trysetlocale
from dledger.printutil import enable_color_escapes
from dledger.record import in_period
from dledger.report import (
    print_simple_report,
    print_simple_rolling_report,
    print_simple_annual_report, print_simple_monthly_report, print_simple_quarterly_report,
    print_simple_sum_report, print_simple_weight_by_ticker,
    print_stats
)
from dledger.projection import (
    scheduled_transactions, convert_estimates, convert_to_currency
)
from dledger.journal import (
    Transaction, write, read, SUPPORTED_TYPES
)

from dataclasses import replace

from typing import List


def main() -> None:
    """ Entry point for invoking the command-line interface. """

    if sys.version_info < (3, 8):
        sys.exit('Python 3.8+ required')

    args = docopt(__doc__, version='dledger ' + __version__.__version__)

    enable_color_escapes()

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

    if args['--by-payout-date']:
        records = [r if r.payout_date is None else
                   replace(r, date=r.payout_date, payout_date=None) for
                   r in records]

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
        if interval is not None:
            records = list(in_period(records, interval))

        print_stats(records, journal_paths=input_paths)

        sys.exit(0)

    records = convert_estimates(records)

    transactions = list(r for r in records if r.amount is not None)

    if not args['--without-forecast']:
        transactions.extend(
            scheduled_transactions(records))

    if interval is not None:
        transactions = list(in_period(transactions, interval))

    transactions = sorted(transactions)

    exchange_symbol = args['--in-currency']

    if exchange_symbol is not None:
        transactions = convert_to_currency(transactions, symbol=exchange_symbol)

    ticker = args['--by-ticker']

    if ticker is not None:
        transactions = list(r for r in transactions if r.ticker == ticker)

    if args['report']:
        if args['--weight']:
            print_simple_weight_by_ticker(transactions)
        elif args['--sum']:
            print_simple_sum_report(transactions)
        elif args['--trailing']:
            print_simple_rolling_report(transactions)
        elif args['--annual']:
            print_simple_annual_report(transactions)
        elif args['--monthly']:
            print_simple_monthly_report(transactions)
        elif args['--quarterly']:
            print_simple_quarterly_report(transactions)
        else:
            print_simple_report(transactions, detailed=ticker is not None)

        sys.exit(0)

    sys.exit(0)


if __name__ == '__main__':
    main()
