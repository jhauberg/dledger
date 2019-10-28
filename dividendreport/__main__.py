#!/usr/bin/env python3

"""
usage: dividendreport generate <file>... [--provider=<name>] [--verbose] [--debug]
       dividendreport export   <file>... [--provider=<name>] [--verbose]
                                           [--output=<file>]  [--pretty]

EXAMPLES:
  dividendreport generate records.csv older-records.csv
    Print a dividend report from a set of records.
  dividendreport generate transactions-2018.csv transactions-2019.csv --provider=nordnet
    Print a dividend report from a set of transactions (by a specific provider).
    See list of supported providers.

  dividendreport export transactions-2018.csv transactions-2019.csv --provider=nordnet
    Export a set of transactions (by a specific provider) as native records.

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
from dividendreport.ledger import export, transactions, sanitize, SUPPORTED_PROVIDERS


def main() -> None:
    """ Entry point for invoking the dividendreport CLI. """

    if sys.version_info < (3, 7):
        sys.exit('Python 3.7+ required')

    args = docopt(__doc__, version='dividendreport ' + __version__.__version__)

    is_verbose = args['--verbose']
    is_debug = args['--debug']
    should_export = args['export']
    input_paths = args['<file>']
    provider = args['--provider']

    records = []

    for input_path in input_paths:
        if provider not in SUPPORTED_PROVIDERS:
            sys.exit('Provider not supported')

        if not (input_path.endswith('.tsv') or
                input_path.endswith('.csv')):
            sys.exit('Only TSV/CSV files are supported')

        records.extend(transactions(input_path, provider))

    records = sanitize(records, verbose=is_verbose)

    if len(records) == 0:
        if is_verbose:
            print('No valid records', file=sys.stderr)

        sys.exit(0)

    if should_export:
        export(records, filename=args['--output'], pretty=args['--pretty'])

        sys.exit(0)

    generate(records, debug=is_debug)

    sys.exit(0)


if __name__ == '__main__':
    main()
