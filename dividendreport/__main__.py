#!/usr/bin/env python3

"""
usage: dividendreport annual <file>... [--provider=<name>] [--verbose]
                                                             [--debug]
       dividendreport export <file>... [--provider=<name>] [--verbose]
                                         [--output=<file>]  [--pretty]

OPTIONS
     --provider=<name>  Specify type of transaction data [default: native]
  -o --output=<file>    Specify filename of exported records [default: export.tsv]
     --pretty           Format exported records for humans
     --verbose          Show diagnostic messages
     --debug            Print debug reports (overrides default report)
  -h --help             Show program help
  -v --version          Show program version

See https://github.com/jhauberg/dividendreport for additional details.
"""

import sys

from docopt import docopt  # type: ignore

from dividendreport import __version__
from dividendreport.report import generate
from dividendreport.ledger import (
    export, transactions, sanitize,
    SUPPORTED_TYPES
)


def main() -> None:
    """ Entry point for invoking the dividendreport CLI. """

    if sys.version_info < (3, 7):
        sys.exit('Python 3.7+ required')

    args = docopt(__doc__, version='dividendreport ' + __version__.__version__)

    input_type = args['--type']
    is_verbose = args['--verbose']
    show_annual_report = args['annual']
    should_export = args['export']
    input_paths = args['<file>']
    provider = args['--provider']

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

    if should_export:
        export(records, filename=args['--output'], pretty=args['--pretty'])

        sys.exit(0)

    if show_annual_report:
        generate(records, debug=args['--debug'])

    sys.exit(0)


if __name__ == '__main__':
    main()
