"""
USAGE:
  dledger report [<journal>]... [--forecast [--drift (--by-position | --by-currency)] |
                                (--monthly | --quarterly | --yearly |
                                 --trailing | --weight | --sum)]
                                [--period=<interval>] [--by-payout-date | --by-ex-date]
                                [--no-projection] [--no-adjustment]
                                [--dividend=<currency>] [--payout=<currency>]
                                [--no-exchange | --exchange-to=<currency>]
                                [--ticker=<ticker>] [--tag=<tags>]
                                [--debug] [--reverse] [--no-color]
  dledger convert <file>...     [--type=<name>] [--output=<journal>]
                                [--condense] [-dr]
  dledger print  [<journal>]... [--condense] [-dr]
  dledger stats  [<journal>]... [--period=<interval>] [-d]


OPTIONS:
     --type=<name>            Specify type of transaction data [default: journal]
     --output=<journal>       Specify journal filename [default: dividends.journal]
  -p --period=<interval>      Specify reporting date interval
     --no-projection          Don't include forecasted transactions
     --no-adjustment          Don't adjust past transactions for splits
     --by-payout-date         List chronologically by payout date
     --by-ex-date             List chronologically by ex-dividend date
     --ticker=<ticker>        Only show income by ticker
     --dividend=<currency>    Only Show income exchanged from currency
     --payout=<currency>      Only Show income exchanged to currency
     --exchange-to=<currency> Show income as if exchanged to currency
     --no-exchange            Show income prior to any exchange
     --forecast               Show income forecast over the next 12 months (per ticker)
     --drift                  Show drift from target weight
     --by-position            Show drift from target position
     --by-currency            Show drift from target currency exposure (weight)
     --tag=<tags>             Only include transactions tagged specifically
  -y --yearly                 Show income by year
  -q --quarterly              Show income by quarter
  -m --monthly                Show income by month
     --trailing               Show income by trailing 12-months (per month)
     --weight                 Show income by weight (per ticker)
     --sum                    Show income by totals
     --no-color               Don't apply ANSI colors
     --condense               Write transactions in the shortest form possible
  -r --reverse                List in reverse order
  -d --debug                  Show diagnostic messages
  -h --help                   Show program help
  -v --version                Show program version

See https://github.com/jhauberg/dledger for additional details.
"""

import os
import sys
import locale

from docopt import docopt  # type: ignore

from dledger import __version__
from dledger.dateutil import parse_period
from dledger.printutil import enable_color_escapes, suppress_color
from dledger.record import in_period, tickers
from dledger.report import (
    print_simple_report,
    print_simple_rolling_report,
    print_simple_annual_report,
    print_simple_monthly_report,
    print_simple_quarterly_report,
    print_simple_sum_report,
    print_simple_weight_by_ticker,
    print_balance_report,
    print_currency_balance_report,
    print_stats,
    DRIFT_BY_WEIGHT,
    DRIFT_BY_POSITION,
)
from dledger.projection import (
    scheduled_transactions,
    latest_exchange_rates,
)
from dledger.journal import (
    ParseError,
    Transaction,
    write,
    read,
    SUPPORTED_TYPES,
)
from dledger.convert import (
    InferenceError,
    inferring_components,
    removing_redundancies,
    adjusting_for_splits,
    with_estimates,
    in_currency,
    in_dividend_currency,
)

from dataclasses import replace

from typing import List, Iterable, Optional


def main() -> None:
    """Entry point for invoking the command-line interface."""

    if sys.version_info < (3, 8):
        # 3.8 required for the following peps/features:
        #  PEP 572 (walrus operator)
        sys.exit(
            f"Python 3.8+ required; "
            f"{sys.version_info[0]}.{sys.version_info[1]} currently"
        )

    args = docopt(__doc__, version="dledger " + __version__.__version__)

    enable_color_escapes()

    try:
        # default to current system locale
        locale.setlocale(locale.LC_ALL, "")
    except (locale.Error, ValueError):
        sys.exit("locale not specified")

    input_paths = args["<file>"] if args["convert"] else args["<journal>"]

    if len(input_paths) == 0:
        try:
            env_journal_path = os.environ["DLEDGER_FILE"]
            env_journal_path = os.path.expandvars(env_journal_path)
            env_journal_path = os.path.expanduser(env_journal_path)
            input_paths = [env_journal_path]
        except KeyError:
            default_journal_path = os.path.expanduser("~/.dledger.journal")
            input_paths = [default_journal_path]

    for path in input_paths:
        if not os.path.isfile(path):
            sys.exit(f"{path}: journal not found")

    input_type = args["--type"]
    is_verbose = args["--debug"] or "DEBUG" in os.environ
    # see https://no-color.org
    if args["--no-color"] or "NO_COLOR" in os.environ:
        suppress_color(True)

    # note that --type defaults to 'journal' for all commands
    # (only convert supports setting type explicitly)
    if input_type not in SUPPORTED_TYPES:
        sys.exit(f"transaction type is not supported: {input_type}")

    records: List[Transaction] = []
    for input_path in input_paths:
        try:
            additional_records = read(input_path, kind=input_type)
            if len(additional_records) == 0:
                # if this resulted in no records, it's likely that something
                # didn't go as expected, however, since no exception was raised,
                # it is probably related to a type mismatch
                if is_verbose and (
                    input_type == "journal" and input_path.endswith(".csv")
                ):
                    # note that it is not unacceptable to use `csv` extension
                    # for a journal, so this can not be considered an error
                    print(
                        f"{input_path}: path does not look like a journal; "
                        f"did you mean to add `--type=nordnet` ?",
                        file=sys.stderr,
                    )
                continue
            records.extend(additional_records)
        except ParseError as pe:
            sys.exit(f"{pe}")
        except ValueError as ve:
            sys.exit(f"{ve}")

    if len(records) == 0:
        sys.exit(0)  # no further output possible, but not an error

    try:
        records = inferring_components(records)
    except InferenceError as e:
        sys.exit(f"{ParseError(str(e), e.record.entry_attr.location)}")

    records = removing_redundancies(records)

    descending_order = args["--reverse"]

    if (args["print"] or args["convert"]) and descending_order:
        # note that other program functions except records in ascending order,
        # so we only apply reversal for this specific case - additionally,
        # reporting commands typically have specific query mechanisms making
        # record order insignificant
        records.reverse()
    if args["print"]:
        write(records, file=sys.stdout, condensed=args["--condense"])
        sys.exit(0)
    if args["convert"]:
        with open(args["--output"], "w", newline="") as file:
            write(records, file=file, condensed=args["--condense"])
        sys.exit(0)

    interval = args["--period"]
    if interval is not None:
        # note that given `-p=apr`, this translates to an interval of `=apr`
        # this could be confusing since you can do `--period=apr` and get `apr`
        # todo: consider checking/correcting this specifically
        try:
            interval = parse_period(interval)
        except ValueError as e:
            sys.exit(f"{e}")

    # determine exchange rates before filtering out any transactions,
    # as we expect the latest rate to be applied in all cases,
    # no matter the period, ticker or other criteria
    exchange_rates = latest_exchange_rates(records)

    if args["stats"]:
        if interval is not None:
            # filter down all records by --period, not just transactions
            records = list(in_period(records, interval))
        print_stats(records, input_paths=input_paths, rates=exchange_rates)
        sys.exit(0)

    # produce estimate amounts for preliminary or incomplete records, transforming
    # them into transactions for all intents and purposes from this point onwards
    # (i.e. including them as journaled transactions for debug purposes)
    records = with_estimates(records, rates=exchange_rates)
    # keep a copy of the list of records as they were before any date swapping,
    # so that we can produce diagnostics only on those transactions entered manually;
    # i.e. not forecasts
    # note that because we copy the list at this point (i.e. *before* period filtering),
    # we have to apply any period filtering again when producing diagnostics
    # if we had copied the list *after* period filtering, we would also be past
    # the date-swapping step, causing every record to look like a diagnostic-producing
    # case (i.e. they would all be lacking either payout or ex-date)
    journaled_records: Optional[Iterable[Transaction]] = None
    if is_verbose:
        journaled_records = (
            r
            for r in records
            if r.entry_attr is not None  # only non-generated entries
            and r.amount is not None  # only keep transactions
        )

    ticker = args["--ticker"]
    if ticker is not None:
        # note that we can apply ticker filtering early because
        # every record of significance will be associated with this ticker
        # (unlike tag filtering, for example)
        records = filter_by_ticker(records, ticker)

    if not args["--no-adjustment"]:
        records = adjusting_for_splits(records)

    if args["--by-payout-date"]:
        # forcefully swap entry date with payout date, if able
        # (diagnostic later if unable)
        records = [
            r
            if r.payout_date is None
            else replace(r, entry_date=r.payout_date, payout_date=None)
            for r in records
        ]

    elif args["--by-ex-date"]:
        # forcefully swap entry date with ex date, if able (diagnostic later if unable)
        records = [
            r if r.ex_date is None else replace(r, entry_date=r.ex_date, ex_date=None)
            for r in records
        ]

    forecasted_transactions = []
    if not args["--no-projection"]:
        # produce forecasted transactions dated into the future
        forecasted_transactions = scheduled_transactions(records, rates=exchange_rates)

    if args["--forecast"]:
        if args["--no-projection"]:
            sys.exit(0)  # no further output possible, but not an error
        records = forecasted_transactions
    else:
        records.extend(forecasted_transactions)

    # for reporting, keep only dividend transactions
    transactions = [r for r in records if r.amount is not None]

    if interval is not None:
        # filter down to only transactions within period interval
        transactions = list(in_period(transactions, interval))

    tag = args["--tag"]
    if tag is not None:
        # note that we can only apply tag filtering at this point (late),
        # because some records may be important for producing forecasts - and
        # these could very well not be tagged
        tags = tag.strip().split(",")
        if len(tags) > 0:
            transactions = filter_by_tag(transactions, tags)

    dividend_currency = args["--dividend"]
    if dividend_currency is not None:
        transactions = [
            txn for txn in transactions if txn.dividend.symbol == dividend_currency
        ]
    payout_currency = args["--payout"]
    if payout_currency is not None:
        transactions = [
            txn for txn in transactions if txn.amount.symbol == payout_currency
        ]

    # (redundantly) sort for good measure
    transactions = sorted(transactions)

    if args["--no-exchange"]:
        transactions = in_dividend_currency(transactions)

    if args["--exchange-to"] is not None:
        # forcefully apply an exchange to given currency
        try:
            transactions = in_currency(
                transactions, symbol=args["--exchange-to"], rates=exchange_rates
            )
        except LookupError as e:
            sys.exit(f"{e}")

    if args["report"]:
        if args["--forecast"]:
            if args["--drift"]:
                if args["--by-currency"]:
                    print_currency_balance_report(transactions)
                elif args["--by-position"]:
                    print_balance_report(
                        transactions,
                        deviance=DRIFT_BY_POSITION,
                        descending=descending_order,
                    )
                else:
                    print_balance_report(
                        transactions,
                        deviance=DRIFT_BY_WEIGHT,
                        descending=descending_order,
                    )
            else:
                keys = ("--by-position", "--by-currency")
                no_effect_flag = next((x for x in keys if args[x] is True), None)
                if no_effect_flag is not None:
                    # condition specified without --drift; this has no effect
                    sys.exit(
                        f"`{no_effect_flag}` has no effect; "
                        f"did you mean to add `--drift` ?"
                    )
                print_balance_report(transactions, descending=descending_order)
        else:
            if args["--weight"]:
                print_simple_weight_by_ticker(transactions)
            elif args["--sum"]:
                print_simple_sum_report(transactions)
            elif args["--trailing"]:
                print_simple_rolling_report(transactions, descending=descending_order)
            elif args["--yearly"]:
                print_simple_annual_report(transactions, descending=descending_order)
            elif args["--monthly"]:
                print_simple_monthly_report(transactions, descending=descending_order)
            elif args["--quarterly"]:
                print_simple_quarterly_report(transactions, descending=descending_order)
            else:
                print_simple_report(
                    transactions,
                    detailed=ticker is not None,
                    descending=descending_order,
                )

    if is_verbose:
        assert journaled_records is not None
        # only include those records applicable to current filter options
        debuggable_entries = list(
            record
            for record in journaled_records
            if any(record.entry_attr == txn.entry_attr for txn in transactions)
        )
        from dledger.debug import (
            debug_find_missing_payout_date,
            debug_find_missing_ex_date,
            debug_find_duplicate_entries,
            debug_find_duplicate_tags,
            debug_find_ambiguous_exchange_rates,
        )

        if args["--by-payout-date"]:
            debug_find_missing_payout_date(debuggable_entries)
        if args["--by-ex-date"]:
            debug_find_missing_ex_date(debuggable_entries)
        debug_find_duplicate_entries(debuggable_entries)
        debug_find_ambiguous_exchange_rates(debuggable_entries, exchange_rates)
        debug_find_duplicate_tags(debuggable_entries)

    sys.exit(0)


def filter_by_tag(records: List[Transaction], tags: List[str]) -> List[Transaction]:
    return list(
        filter(
            lambda txn: txn.tags is not None
            and any(x.strip() in txn.tags for x in tags),
            records,
        )
    )


def filter_by_ticker(records: List[Transaction], ticker: str) -> List[Transaction]:
    unique_tickers = tickers(records)
    # first look for exact match
    if ticker not in unique_tickers:
        # otherwise look for partial matches
        matching_tickers = [
            t for t in unique_tickers if t.startswith(ticker)
        ]  # note case-sensitive
        if len(matching_tickers) == 1:  # unambiguous match
            ticker = matching_tickers[0]
    # filter down to only include records by ticker
    return list(r for r in records if r.ticker == ticker)


if __name__ == "__main__":
    main()
