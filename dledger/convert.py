import math

from datetime import date

from dledger.journal import (
    Transaction,
    POSITION_SPLIT,
    POSITION_SPLIT_WHOLE,
)
from dledger.record import (
    tickers,
    by_ticker,
    after,
    latest,
)
from dledger.projection import (
    GeneratedAmount,
    latest_exchange_rates,
)
from dledger.formatutil import decimalplaces, truncate_floating_point
from dledger.dateutil import in_months, todayd

from dataclasses import replace
from typing import List, Dict, Tuple, Optional


def removing_redundancies(
    records: List[Transaction],
    since: date = todayd(),
) -> List[Transaction]:
    for ticker in tickers(records):
        recs = list(by_ticker(records, ticker))
        # find all entries that only record a change in position
        position_records = list(r for r in recs if r.ispositional)
        if len(position_records) == 0:
            continue
        # find all records with a cash component
        realized_records = list(r for r in recs if r not in position_records)
        latest_transaction: Optional[Transaction] = None
        if len(realized_records) > 0:
            latest_transaction = realized_records[-1]
        # at this point we no longer need to keep some of the position entries around,
        # as we have already used them to infer and determine position for each realized entry
        for record in position_records:
            if record.entry_attr is not None:
                _, directive = record.entry_attr.positioning
                if (
                    directive == POSITION_SPLIT or
                    directive == POSITION_SPLIT_WHOLE
                ):
                    # special case: record has a split directive;
                    # must be retained for journal integrity
                    continue
            is_redundant = False
            if latest_transaction is None:
                # this record is not used for inference nor forecasts,
                # because no dividend transactions exist
                is_redundant = True
            elif (
                record.entry_date < in_months(since, months=-12)
            ):
                # more than a year has passed;
                # forecasts will expire naturally, so record is redundant
                is_redundant = True
            elif (
                record.entry_date < latest_transaction.entry_date
            ):
                # dated earlier than latest transaction; i.e. this positional
                # record will not be used for inference nor forecasts
                if latest_transaction.ex_date is not None:
                    if record.entry_date < latest_transaction.ex_date:
                        is_redundant = True
                else:
                    is_redundant = True
            elif (
                record.entry_date == latest_transaction.entry_date and
                math.isclose(
                    record.position,
                    latest_transaction.position,
                    abs_tol=0.000001)
            ):
                # dated same as a dividend transaction; discard this record
                # if position on both is approximately identical
                is_redundant = True
            if is_redundant:
                records.remove(record)
    return records


def adjusting_for_splits(records: List[Transaction]) -> List[Transaction]:
    splits = list(
        record
        for record in records
        if record.ispositional
        and record.entry_attr is not None
        and (
            record.entry_attr.positioning[1] == POSITION_SPLIT
            or record.entry_attr.positioning[1] == POSITION_SPLIT_WHOLE
        )
    )
    adjusted_records = []
    for record in records:
        later_splits = list(
            after(
                by_ticker(splits, record.ticker),
                record.ex_date if record.ex_date is not None else record.entry_date,
            )
        )
        if len(later_splits) > 0:
            # note that each split can be handled in one of two ways:
            #  1) fractional remainders paid out as cash, keep whole (default)
            #  2) fractional remainders kept as a fractional share
            # if we always assumed either, we could adjust by the product of all factors,
            # but since we support both kinds, we need to apply each split individually
            product = math.prod(
                split.entry_attr.positioning[0] for split in later_splits
            )
            adjusted_position = record.position
            for split in later_splits:  # assuming ordered earlier to later
                factor, directive = split.entry_attr.positioning
                assert factor is not None
                adjusted_position = adjusted_position * factor
                if directive == POSITION_SPLIT_WHOLE:
                    adjusted_position = math.floor(adjusted_position)

            adjusted_dividend = record.dividend
            if record.dividend is not None:
                adjusted_dividend_value = truncate_floating_point(
                    record.dividend.value / product, places=4
                )
                adjusted_dividend_places = decimalplaces(adjusted_dividend_value)
                adjusted_dividend = replace(
                    record.dividend,
                    value=adjusted_dividend_value,
                    places=max(adjusted_dividend_places, record.dividend.places),
                )
            record = replace(
                record, position=adjusted_position, dividend=adjusted_dividend
            )
        adjusted_records.append(record)
    return adjusted_records


def with_estimates(
    records: List[Transaction], rates: Optional[Dict[Tuple[str, str], Tuple[date, float]]] = None
) -> List[Transaction]:
    """ Return a list of transactions, replacing missing amounts with estimates. """
    rates = rates if rates is not None else latest_exchange_rates(records)
    transactions = list(r for r in records if r.amount is not None)
    estimate_records = (
        r for r in records if (r.amount is None and r.dividend is not None)
    )
    for rec in estimate_records:
        conversion_factor = 1.0
        assert rec.dividend is not None
        if rec.entry_attr is not None and rec.entry_attr.preliminary_amount is not None:
            estimate_symbol = rec.entry_attr.preliminary_amount.symbol
            estimate_format = rec.entry_attr.preliminary_amount.fmt
            assert rec.dividend.symbol is not None
            assert estimate_symbol is not None
            rate = rates[
                (rec.dividend.symbol, estimate_symbol)
            ]
            conversion_factor = rate[1]
        else:
            estimate_symbol = rec.dividend.symbol
            estimate_format = rec.dividend.fmt
            latest_transaction = latest(by_ticker(transactions, rec.ticker))
            if latest_transaction is not None:
                assert latest_transaction.amount is not None
                estimate_symbol = latest_transaction.amount.symbol
                estimate_format = latest_transaction.amount.fmt
                if rec.dividend.symbol != latest_transaction.amount.symbol:
                    assert rec.dividend.symbol is not None
                    assert latest_transaction.amount.symbol is not None
                    rate = rates[
                        (rec.dividend.symbol, latest_transaction.amount.symbol)
                    ]
                    conversion_factor = rate[1]
        estimate_amount = GeneratedAmount(
            value=(rec.position * rec.dividend.value) * conversion_factor,
            symbol=estimate_symbol,
            fmt=estimate_format,
        )
        estimate = replace(rec, amount=estimate_amount)
        i = records.index(rec)
        records.pop(i)
        records.insert(i, estimate)

    return records


def in_dividend_currency(records: List[Transaction]) -> List[Transaction]:
    """ Return a list of transactions, replacing amounts with the sum of dividend times position. """
    for r in records:
        if r.dividend is None:
            continue
        if r.dividend.symbol == r.amount.symbol:
            # no conversion needed
            continue
        native_value = r.dividend.value * r.position
        native_amount = replace(
            r.amount,
            value=native_value,
            symbol=r.dividend.symbol,
            fmt=r.dividend.fmt,
            places=None,
        )
        native_record = replace(r, amount=native_amount)
        i = records.index(r)
        records.pop(i)
        records.insert(i, native_record)

    return records


def in_currency(
    records: List[Transaction],
    *,
    symbol: str,
    rates: Optional[Dict[Tuple[str, str], Tuple[date, float]]] = None,
) -> List[Transaction]:
    """ Return a list of transactions, replacing amounts with estimates in given currency. """
    rates = rates if rates is not None else latest_exchange_rates(records)
    transactions = list(r for r in records if r.amount is not None)
    convertible_records = (
        r for r in records if (r.amount is not None and r.amount.symbol != symbol)
    )
    for rec in convertible_records:
        assert rec.amount is not None
        assert rec.amount.symbol is not None
        try:
            conversion_factor = rates[(rec.amount.symbol, symbol)]
        except KeyError:
            try:
                rate = rates[
                    (symbol, rec.amount.symbol)
                ]
                conversion_factor = rate[1]
                conversion_factor = 1.0 / conversion_factor
            except KeyError:
                raise ValueError(f"can't exchange between {rec.amount.symbol}/{symbol}")
        estimate_format: Optional[str] = None
        for t in reversed(transactions):
            assert t.amount is not None
            if t.amount.symbol == symbol:
                estimate_format = t.amount.fmt
            elif t.dividend is not None and t.dividend.symbol == symbol:
                estimate_format = t.dividend.fmt
            if estimate_format is not None:
                break
        estimate_amount = GeneratedAmount(
            value=rec.amount.value * conversion_factor,
            symbol=symbol,
            fmt=estimate_format,
        )
        estimate = replace(rec, amount=estimate_amount)
        i = records.index(rec)
        records.pop(i)
        records.insert(i, estimate)

    return records
