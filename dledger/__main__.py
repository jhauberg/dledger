#!/usr/bin/env python3

"""
usage: dledger report         <journal>... [--period=<years>] [--weighted] [-V]
       dledger chart <ticker> <journal>... [--period=<years>] [-V]
       dledger forecast       <journal>... [--weighted] [-V]
       dledger convert <file>... [--type=<name>] [--output=<journal>] [-V]

OPTIONS:
     --type=<name>       Specify type of transaction data [default: native]
     --output=<journal>  Specify journal filename [default: journal.tsv]
     --period=<years>    Specify range of years [default: current year]
     --weighted          Show report as a weighted table
  -V --verbose           Show diagnostic messages
  -h --help              Show program help
  -v --version           Show program version

See https://github.com/jhauberg/dledger for additional details.
"""

import sys

from docopt import docopt  # type: ignore

from dledger import __version__
from dledger.report import generate
from dledger.journal import (
    export, transactions, sanitize,
    SUPPORTED_TYPES
)


def main() -> None:
    """ Entry point for invoking the command-line interface. """

    if sys.version_info < (3, 8):
        sys.exit('Python 3.8+ required')

    args = docopt(__doc__, version='dledger ' + __version__.__version__)

    print(args)

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

        if not (input_path.endswith('.tsv') or
                input_path.endswith('.csv')):
            sys.exit('Only TSV/CSV files are supported')

        records.extend(transactions(input_path, input_type))

    records = sanitize(records, verbose=is_verbose)

    if len(records) == 0:
        if is_verbose:
            print('No valid records', file=sys.stderr)

        sys.exit(0)

    if args['convert']:
        export(records, filename=args['--output'], pretty=True)

        sys.exit(0)

    if args['report']:
        period = args['--period']
        if period == 'current year':
            # todo: set to current year; maybe even use range() ?
            pass
        generate(records)
    elif args['chart']:
        ticker = args['<ticker>']
        pass
    elif args['forecast']:
        pass

    sys.exit(0)


if __name__ == '__main__':
    main()
