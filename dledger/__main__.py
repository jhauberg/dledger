#!/usr/bin/env python3

"""
usage: dledger report  [<journal>]... [--period=<interval>] [-v]
                                      [--monthly | --quarterly | --annual | --trailing | --weight | --sum]
                                      [--without-forecast]
                                      [--by-ticker=<ticker>]
                                      [--by-payout-date | --by-ex-date]
                                      [--as-currency=<symbol> | --as-native-currency]
                                      [--baseline]
       dledger balance [<journal>]... [--by-position | --by-amount | --by-currency] [-v]
                                      [--by-payout-date | --by-ex-date]
                                      [--as-currency=<symbol> | --as-native-currency]
                                      [--baseline]
       dledger stats   [<journal>]... [--period=<interval>] [-v]
       dledger print   [<journal>]... [--condensed] [-v]
       dledger convert <file>...      [--type=<name>] [-v]
                                      [--output=<journal>]

OPTIONS:
     --type=<name>            Specify type of transaction data [default: journal]
     --output=<journal>       Specify journal filename [default: ledger.journal]
     --period=<interval>      Specify reporting date interval
     --without-forecast       Don't include forecasted transactions
     --by-payout-date         List chronologically by payout date
     --by-ex-date             List chronologically by ex-dividend date
     --by-ticker=<ticker>     Show income by ticker (exclusively)
     --as-currency=<symbol>   Show income as if exchanged to currency
     --as-native-currency     Show income as received, prior to any exchange
     --baseline               Show baseline income (i.e. 1 share per ticker)
     --by-position            Show drift from target position
     --by-amount              Show drift from target income
     --by-currency            Show drift from target currency exposure
     --annual                 Show income by year
     --quarterly              Show income by quarter
     --monthly                Show income by month
     --trailing               Show income by trailing 12-months (per month)
     --weight                 Show income by weight (per ticker)
     --sum                    Show income by totals
  -v --verbose                Show diagnostic messages
  -h --help                   Show program help
  -V --version                Show program version

See https://github.com/jhauberg/dledger for additional details.
"""

import os
import sys
import locale

from docopt import docopt  # type: ignore

from dledger import __version__
from dledger.dateutil import parse_period
from dledger.localeutil import trysetlocale
from dledger.printutil import enable_color_escapes
from dledger.record import in_period, tickers
from dledger.report import (
    print_simple_report,
    print_simple_rolling_report,
    print_simple_annual_report, print_simple_monthly_report, print_simple_quarterly_report,
    print_simple_sum_report, print_simple_weight_by_ticker,
    print_balance_report, print_currency_balance_report,
    print_stats,
    DRIFT_BY_WEIGHT, DRIFT_BY_AMOUNT, DRIFT_BY_POSITION
)
from dledger.projection import (
    scheduled_transactions, convert_estimates, convert_to_currency, convert_to_native_currency, latest_exchange_rates,
    conversion_factors
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

    if len(input_paths) == 0:
        try:
            env_journal_path = os.environ['DLEDGER_FILE']
            env_journal_path = os.path.expandvars(env_journal_path)
            env_journal_path = os.path.expanduser(env_journal_path)
            input_paths = [env_journal_path]
        except KeyError:
            default_journal_path = os.path.expanduser("~/.dledger.journal")
            input_paths = [default_journal_path]

    for path in input_paths:
        if not os.path.isfile(path):
            sys.exit(f'{path}: journal not found')

    input_type = args['--type']
    is_verbose = args['--verbose']

    # note that --type defaults to 'journal' for all commands
    # (only convert supports setting type explicitly)
    if input_type not in SUPPORTED_TYPES:
        sys.exit(f'Transaction type is not supported: {input_type}')

    records: List[Transaction] = []
    for input_path in input_paths:
        records.extend(read(input_path, input_type))
    if len(records) == 0:
        sys.exit(0)
    records = sorted(records)

    if args['convert']:
        with open(args['--output'], 'w', newline='') as file:
            write(records, file=file)
        sys.exit(0)

    if args['print']:
        write(records, file=sys.stdout, condensed=args['--condensed'])
        sys.exit(0)

    interval = args['--period'] if not args['balance'] else 'tomorrow:'
    if interval is not None:
        interval = parse_period(interval)

    # determine exchange rates before filtering out any transactions, as we expect the
    # latest rate to be applied in all cases, no matter the period, ticker or other criteria
    exchange_rates = latest_exchange_rates(records)

    if args['stats']:
        if interval is not None:
            # filter down all records by --period, not just transactions
            records = list(in_period(records, interval))
        print_stats(records, journal_paths=input_paths, rates=exchange_rates)
        sys.exit(0)

    ticker = args['--by-ticker']
    if ticker is not None:
        unique_tickers = tickers(records)
        # first look for exact match
        if ticker not in unique_tickers:
            # otherwise look for partial matches
            matching_tickers = [t for t in unique_tickers if
                                t.startswith(ticker)]  # note case-sensitive
            if len(matching_tickers) == 1:  # unambiguous match
                ticker = matching_tickers[0]
        # filter down to only include records by ticker
        records = list(r for r in records if r.ticker == ticker)
    # produce estimate amounts for preliminary or incomplete records,
    # transforming them into transactions for all intents and purposes from this point onwards
    records = convert_estimates(records, rates=exchange_rates)
    # keep a copy of the list of records as they were before any date swapping, so that we can
    # produce diagnostics only on those transactions entered manually; i.e. not forecasts
    # note that because we copy the list at this point (i.e. *before* period filtering),
    # we have to apply any period filtering again when producing diagnostics
    # if we had copied the list *after* period filtering, we would also be past the date-swapping
    # step, causing every record to look like a diagnostic-producing case (i.e. they would all be
    # lacking either payout or ex-date)
    journaled_transactions = ([r for r in records if
                               r.entry_attr is not None and  # only non-generated entries
                               r.amount is not None]  # only keep transactions
                              if is_verbose else
                              None)

    if args['--by-payout-date']:
        # forcefully swap entry date with payout date, if able (diagnostic later if unable)
        records = [r if r.payout_date is None else
                   replace(r, entry_date=r.payout_date, payout_date=None) for
                   r in records]

    elif args['--by-ex-date']:
        # forcefully swap entry date with ex date, if able (diagnostic later if unable)
        records = [r if r.ex_date is None else
                   replace(r, entry_date=r.ex_date, ex_date=None) for
                   r in records]

    if args['--as-native-currency']:
        records = convert_to_native_currency(records)

    if args['--baseline']:
        # convert all transactions to their baseline representations;
        # i.e. treating all transactions as if the position was 1
        # this is effectively just a way to reveal base dividends with
        # exchange rates applied (if applicable)
        def baseline_record(record: Transaction) -> Transaction:
            if record.amount is not None:
                baseline_amount = replace(
                    record.amount, value=record.amount.value / record.position)
            else:
                baseline_amount = record.amount
            return replace(record, position=1, amount=baseline_amount)
        records = [baseline_record(r) if r.position > 0 else r for r in records]

    if not args['--without-forecast']:
        # produce forecasted transactions dated into the future
        records.extend(scheduled_transactions(records, rates=exchange_rates))

    # for reporting, keep only dividend transactions
    transactions = [r for r in records if r.amount is not None]

    if interval is not None:
        # filter down to only transactions within period interval
        transactions = list(in_period(transactions, interval))
    # (redundantly) sort for good measure
    transactions = sorted(transactions)

    exchange_symbol = args['--as-currency']
    if exchange_symbol is not None:
        # forcefully apply an exchange to given currency
        transactions = convert_to_currency(
            transactions, symbol=exchange_symbol, rates=exchange_rates)

    if args['balance']:
        if args['--by-currency']:
            print_currency_balance_report(transactions)
        elif args['--by-position']:
            print_balance_report(transactions, deviance=DRIFT_BY_POSITION)
        elif args['--by-amount']:
            print_balance_report(transactions, deviance=DRIFT_BY_AMOUNT)
        else:
            print_balance_report(transactions, deviance=DRIFT_BY_WEIGHT)

    if args['report']:
        # finally produce and print a report
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

    if is_verbose:  # print diagnostics on final set of transactions, if any
        # find missing date entries when specifically sorting by date
        if args['--by-payout-date'] or args['--by-ex-date']:
            assert journaled_transactions is not None
            if interval is not None:
                journaled_transactions = list(in_period(journaled_transactions, interval))
            if ticker is not None:
                journaled_transactions = [r for r in journaled_transactions if r.ticker == ticker]
            journaled_transactions = sorted(journaled_transactions)
            if args['--by-payout-date']:
                skipped_transactions = [r for r in journaled_transactions if r.payout_date is None]
                for transaction in skipped_transactions:
                    assert transaction.entry_attr is not None
                    journal, linenumber = transaction.entry_attr.location
                    print(f'{journal}:{linenumber} transaction is missing payout date',
                          file=sys.stderr)
            elif args['--by-ex-date']:
                skipped_transactions = [r for r in journaled_transactions if r.ex_date is None]
                for transaction in skipped_transactions:
                    assert transaction.entry_attr is not None
                    journal, linenumber = transaction.entry_attr.location
                    print(f'{journal}:{linenumber} transaction is missing ex-dividend date',
                          file=sys.stderr)
        # find ambiguous conversion rates
        from dledger.projection import GeneratedAmount
        ambiguous_exchange_rates = conversion_factors(
            # only include journaled records, but don't include preliminary estimates (signified by GeneratedAmount)
            [r for r in journaled_transactions if not isinstance(r.amount, GeneratedAmount)])
        for symbols, rates in ambiguous_exchange_rates.items():
            if len(rates) > 1:
                print(f'ambiguous exchange rate {symbols} = {exchange_rates[symbols]}:\n or, {rates[:-1]}',
                      file=sys.stderr)

    sys.exit(0)


if __name__ == '__main__':
    main()
