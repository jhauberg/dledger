import sys

from datetime import date

from typing import List, Dict, Tuple

from dledger.formatutil import format_amount
from dledger.record import tickers, by_ticker
from dledger.journal import (
    Transaction,
    Distribution,
)
from dledger.projection import (
    conversion_factors,
)


def debug_find_missing_payout_date(transactions: List[Transaction]) -> None:
    skipped_transactions = [r for r in transactions if r.payout_date is None]
    for transaction in skipped_transactions:
        assert transaction.entry_attr is not None
        journal, linenumber = transaction.entry_attr.location
        print(
            f"{journal}:{linenumber} transaction is missing payout date",
            file=sys.stderr,
        )


def debug_find_missing_ex_date(transactions: List[Transaction]) -> None:
    skipped_transactions = [r for r in transactions if r.ex_date is None]
    for transaction in skipped_transactions:
        assert transaction.entry_attr is not None
        journal, linenumber = transaction.entry_attr.location
        print(
            f"{journal}:{linenumber} transaction is missing ex-dividend date",
            file=sys.stderr,
        )


def debug_find_potential_duplicates(transactions: List[Transaction]) -> None:
    for ticker in tickers(transactions):
        entries = list(by_ticker(transactions, ticker))
        dupes: List[Transaction] = []
        for i, txn in enumerate(entries):
            assert txn.entry_attr is not None
            if txn in dupes:
                continue
            for j, other_txn in enumerate(entries):
                if i == j:
                    # don't compare to self
                    continue
                if txn.entry_date != other_txn.entry_date:
                    # not dated identically; move on
                    continue
                if txn.ispositional or other_txn.ispositional:
                    # either is positional; move on
                    continue
                if (
                    txn.kind == Distribution.SPECIAL
                    or other_txn.kind == Distribution.SPECIAL
                ):
                    continue
                dupe = other_txn
                dupes.append(dupe)
                journal, linenumber = dupe.entry_attr.location
                existing_journal, existing_linenumber = txn.entry_attr.location
                existing_journal = (
                    "" if existing_journal == journal else existing_journal
                )
                print(
                    f"{journal}:{linenumber} "
                    f"potential transaction duplicate "
                    f"(see '{existing_journal}:{existing_linenumber}')",
                    file=sys.stderr,
                )


def debug_find_ambiguous_exchange_rates(
    transactions: List[Transaction],
    exchange_rates: Dict[Tuple[str, str], Tuple[date, float]],
) -> None:
    from dledger.projection import GeneratedAmount

    ambiguous_exchange_rates = conversion_factors(
        # only include journaled records, but don't include preliminary
        # estimates (signified by GeneratedAmount)
        [
            record
            for record in transactions
            if not isinstance(record.amount, GeneratedAmount)
        ]
    )

    for symbols, rates in ambiguous_exchange_rates.items():
        if len(rates) > 1:
            applied_rate = exchange_rates[symbols]
            applied_rate_amount = format_amount(applied_rate[1])
            applied_datestamp = applied_rate[0].strftime("%Y/%m/%d")
            ambiguous_rate = rates[:-1][0]  # take the first
            ambiguous_rate_amount = format_amount(ambiguous_rate[1])
            ambiguous_datestamp = ambiguous_rate[0].strftime("%Y/%m/%d")
            from_symbol, to_symbol = symbols
            print(
                f"ambiguous exchange rate for {from_symbol}/{to_symbol}:\n"
                f" {applied_datestamp} {applied_rate_amount} (applied) or\n"
                f" {ambiguous_datestamp} {ambiguous_rate_amount}",
                file=sys.stderr,
            )


def debug_find_duplicate_tags(transactions: List[Transaction]) -> None:
    tagged_transactions = (txn for txn in transactions if txn.tags is not None)
    for txn in tagged_transactions:
        assert txn.entry_attr is not None
        unique_tags = set(txn.tags)
        for tag in unique_tags:
            if txn.tags.count(tag) > 1:
                assert txn.entry_attr is not None
                journal, linenumber = txn.entry_attr.location
                print(
                    f"{journal}:{linenumber} transaction has duplicate tag: {tag}",
                    file=sys.stderr,
                )
