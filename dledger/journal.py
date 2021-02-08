import csv
import re
import math
import locale
import os

from dledger.localeutil import trysetlocale
from dledger.formatutil import format_amount, decimalplaces
from dledger.fileutil import fileencoding
from dledger.dateutil import parse_datestamp

from dataclasses import dataclass, replace
from datetime import datetime, date
from decimal import Decimal

from typing import List, Union, Tuple, Optional, Any, Dict, Iterable
from enum import Enum

SUPPORTED_TYPES = ["journal", "nordnet"]

POSITION_SET = 0  # directive to set or infer absolute position
POSITION_ADD = 1  # directive/multiplier to add to previous position
POSITION_SUB = -1  # directive/multiplier to subtract from previous position


class Distribution(Enum):
    """ Represents the type of a dividend distribution. """

    FINAL = 0
    INTERIM = 1
    SPECIAL = 2


@dataclass(frozen=True, unsafe_hash=True)
class Amount:
    """ Represents a cash amount. """

    value: Union[float, int]
    places: Optional[int] = None
    symbol: Optional[str] = None
    fmt: Optional[str] = None


@dataclass(frozen=True)
class EntryAttributes:
    """Represents a set of attributes describing some facts about a journal entry.

    These are properties that can only be known at parse-time, as a journal entry may undergo
    several processing steps ultimately changing its final representation.

    For example, whether a record is preliminary or not cannot be deduced after processing
    as it will end up having a generated amount attached to it (where it would otherwise be None).
    """

    location: Tuple[str, int]  # journal:linenumber
    # todo: we need this information during parsing in order to infer an absolute position,
    #       however, once we're done parsing, this field rarely becomes very useful later on,
    #       as it will generally always equal (position, POSITION_SET)
    #       this is the case since because positional records are typically redundant and will
    #       be pruned anyway. consider whether we can do something to make this more useful?
    positioning: Tuple[Optional[float], int]  # position/change:directive
    is_preliminary: bool = False  # True if amount component left blank intentionally
    preliminary_amount: Optional[Amount] = None


@dataclass(frozen=True, unsafe_hash=True)
class Transaction:
    """ Represents a transactional record. """

    entry_date: date  # no assumption whether this is payout, ex-date or other
    ticker: str
    position: float  # absolute position
    amount: Optional[Amount] = None
    dividend: Optional[Amount] = None
    kind: Distribution = Distribution.FINAL
    payout_date: Optional[date] = None
    ex_date: Optional[date] = None
    entry_attr: Optional[EntryAttributes] = None

    @property
    def ispositional(self) -> bool:
        """Return True if transaction only records a position component, False otherwise.

        This is typically the case for a buy/sell transaction.
        """
        return self.amount is None and self.dividend is None

    def __lt__(self, other):  # type: ignore
        def literal_location(r: Transaction) -> Tuple[str, int]:
            return r.entry_attr.location if r.entry_attr is not None else ("", 0)

        # sort by primary date and always put buy/sell transactions later if on same date
        # e.g.  2019/01/01 ABC (+10)
        #       2019/01/01 ABC (10)  $ 1
        #   =>
        #       2019/01/01 ABC (10)  $ 1
        #       2019/01/01 ABC (+10)
        # thirdly, take literal order in journal into account (both linenumber and path)
        # finally, to stabilize sorting in all cases, use ticker for alphabetical ordering
        return (
            self.entry_date,
            self.ispositional,
            literal_location(self),
            self.ticker,
        ) < (
            other.entry_date,
            other.ispositional,
            literal_location(other),
            other.ticker,
        )


class ParseError(Exception):
    def __init__(self, message: str, location: Tuple[str, int]):
        super().__init__(f"{os.path.abspath(location[0])}:{location[1]} {message}")


def read(path: str, kind: str) -> List[Transaction]:
    """ Return a list of records imported from a file. """

    encoding = fileencoding(path)
    if encoding is None or len(encoding) == 0:
        raise ValueError(f"Path could not be read: '{path}'")

    if kind == "journal":
        return excluding_redundant_transactions(
            read_journal_transactions(path, encoding)
        )
    elif kind == "nordnet":
        return read_nordnet_transactions(path, encoding)
    return []


def read_journal_transactions(path: str, encoding: str = "utf-8") -> List[Transaction]:
    journal_entries = []

    # note that this pattern will initially let inconsistent formatting pass (e.g. 2019/12-1)
    # but will eventually raise a formatting error later on (it is faster to skip validation
    # through parse_datestamp at this point)
    transaction_start = re.compile(r"[0-9]+[-/][0-9]+[-/][0-9]+")
    # any (stripped) line starting with "include" is considered an inclusion directive;
    # handled as it occurs in the journal
    include_start = re.compile(r"include")

    with open(path, newline="", encoding=encoding) as file:
        line_number = 0
        lines: List[Tuple[int, str]] = []
        # start reading, line by line; each line read representing part of the current transaction
        # once we encounter a line starting with what looks like a date, we take that to indicate
        # the beginning of next transaction and parse all lines read up to this point (excluding
        # that line), and then repeat until end of file
        while line := file.readline():
            line_number += 1
            # strip any comment
            if "#" in line:
                line = line[: line.index("#")]
            # remove leading and trailing whitespace
            line = line.strip()
            # determine start of next transaction
            if transaction_start.match(line) is not None:
                for n, (previous_line_number, previous_line) in enumerate(
                    reversed(lines)
                ):
                    if transaction_start.match(previous_line) is not None:
                        offset = n + 1
                        lines = lines[len(lines) - offset:]
                        journal_entries.append(
                            read_journal_transaction(
                                lines, location=(path, previous_line_number)
                            )
                        )
                        lines.clear()
                        break
            if len(line) > 0:
                # line has content; determine if it's an include directive
                if include_start.match(line) is not None:
                    relative_include_path = line[len("include"):].strip()
                    include_path = os.path.join(
                        os.path.dirname(path), relative_include_path
                    )
                    if os.path.samefile(path, include_path):
                        raise ParseError(
                            "attempt to recursively include journal",
                            location=(path, line_number),
                        )
                    journal_entries.extend(
                        # note that this assumes all included journals are of identical encoding
                        # if we instead went `read(.., kind="journal"), then this would not support
                        # pruning redundant records (as they might be needed during recursion)
                        read_journal_transactions(include_path, encoding)
                    )
                    # clear out this line; we've dealt with the directive and
                    # don't want to handle it when parsing next transaction
                    line = ""
                lines.append(
                    (line_number, line)
                )  # todo: also attach info, e.g. TRANSACTION_START
                #       so we don't have to do regex check twice
        if len(lines) > 0:
            for n, (previous_line_number, previous_line) in enumerate(
                reversed(lines)
            ):
                if transaction_start.match(previous_line) is not None:
                    offset = n + 1
                    lines = lines[len(lines) - offset:]
                    journal_entries.append(
                        read_journal_transaction(
                            lines, location=(path, previous_line_number)
                        )
                    )
                    break

    # transactions are not necessarily ordered by date in a journal
    # so they must be sorted prior to inferring positions/currencies
    # note that position change entries are always sorted to occur *after*
    # any realized transaction on the same date (see Transaction.__lt__)
    journal_entries = sorted(
        journal_entries,
        key=lambda r: (r.entry_date, r.amount is None and r.dividend is None),
    )

    records: List[Transaction] = []

    def truncate_floating_point(value: float, *, places: int = 2) -> float:
        v = Decimal(value)
        v = round(v, places)
        return float(v)

    for entry in journal_entries:
        # todo: hackily pack, then unpack to get mutable copies of each attribute
        d, d2, d3, ticker, amount, dividend, attr = (
            entry.entry_date,
            entry.payout_date,
            entry.ex_date,
            entry.ticker,
            entry.amount,
            entry.dividend,
            entry.entry_attr,
            # note that we intentionally ignore entry.position here (expecting it to be -1)
        )

        assert attr is not None

        p, p_directive = attr.positioning
        location = attr.location

        if p is None or p_directive != POSITION_SET:
            # infer position from previous entries
            by_ex_date = sorted(
                records,
                key=lambda r: (
                    r.ex_date if r.ex_date is not None else r.entry_date,
                    r.ispositional,
                ),
            )

            for previous_record in reversed(by_ex_date):
                if previous_record.ticker == ticker:
                    if previous_record.position is None:
                        continue
                    if d3 is not None and previous_record.entry_date > d3:
                        continue
                    if p is None:
                        p = 0
                    p_delta = p * p_directive
                    p = truncate_floating_point(previous_record.position + p_delta)
                    if p < 0:
                        raise ParseError(
                            f"position change to negative position ({p})", location
                        )
                    break

        if amount is not None and dividend is not None:
            if amount.symbol == dividend.symbol:
                inferred_p = amount.value / dividend.value
                if p is not None:
                    # determine whether position equates (close enough) to the inferred position
                    # tolerance based on fractional precision from Robinhood/M1
                    # see https://robinhood.com/us/en/support/articles/66zKxGmw7zjdkFXEcGYksl/fractional-shares/
                    # or https://support.m1finance.com/hc/en-us/articles/221053227-Explanation-of-Fractional-Shares
                    # todo: Robinhood rounds to nearest penny, so this ambiguity check might not work
                    #       e.g. 1 penny = $ 0.01
                    #       so if you your position would amount to 0.006, you would get 0.01
                    #       but also hit this error, because your position is 0.006/div, not 0.01/div
                    if not math.isclose(p, inferred_p, abs_tol=0.000001):
                        raise ParseError(
                            f"ambiguous position ({p} or {inferred_p}?)", location
                        )
                else:
                    p = truncate_floating_point(inferred_p)

        if p is None:
            raise ParseError(f"position could not be inferred", location)

        if amount is not None and p == 0:
            raise ParseError(f"payout on closed position", location)

        if amount is not None and dividend is None:
            inferred_dividend = truncate_floating_point(amount.value / p)
            dividend = Amount(
                inferred_dividend,
                places=decimalplaces(inferred_dividend),
                symbol=amount.symbol,
                fmt=amount.fmt,
            )

        if amount is None and dividend is None:
            if d2 is not None or d3 is not None:
                raise ParseError(f"associated date on positional record", location)

        if d2 is not None and d3 is not None:
            if d2 < d3:
                raise ParseError(f"payout date dated earlier than ex-date", location)

        is_incomplete = False
        prelim_amount = None
        if (
            amount is None or amount is not None and amount.value == 0
        ) and dividend is not None:
            prelim_amount = amount
            is_incomplete = True

        transaction_attribs = replace(
            attr, preliminary_amount=prelim_amount, is_preliminary=is_incomplete
        )

        transaction = replace(
            entry,
            amount=amount if prelim_amount is None else None,
            entry_attr=transaction_attribs,
            position=p,
            dividend=dividend,
        )

        records.append(transaction)

    return records


def excluding_redundant_transactions(
    records: List[Transaction],
) -> List[Transaction]:
    for ticker in set([record.ticker for record in records]):
        recs = list(r for r in records if r.ticker == ticker)
        # find all entries that only record a change in position
        position_records = list(r for r in recs if r.ispositional)
        if len(position_records) == 0:
            continue
        # find all dividend transactions (e.g. cash received or earned)
        realized_records = list(r for r in recs if r not in position_records)
        if len(realized_records) == 0:
            continue
        latest_record = realized_records[-1]
        # at this point we no longer need to keep some of the position entries around,
        # as we have already used them to infer and determine position for each realized entry
        for record in position_records:
            # so each position entry dated prior to a dividend entry is basically redundant
            if record.position == 0:
                # unless it's a closer, in which case we have to keep it around in any case
                # (e.g. see example/strategic.journal)
                continue
            if (
                latest_record.ex_date is not None
                and record.entry_date >= latest_record.ex_date
            ):
                continue
            is_redundant = False
            if record.entry_date < latest_record.entry_date:
                is_redundant = True
            elif record.entry_date == latest_record.entry_date and math.isclose(
                record.position, latest_record.position, abs_tol=0.000001
            ):
                is_redundant = True
            if is_redundant:
                records.remove(record)

    return records


def read_journal_transaction(
    lines: List[Tuple[int, str]], *, location: Tuple[str, int]
) -> Transaction:
    if len(lines) == 0:
        raise ParseError("invalid transaction", location)

    def anyindex(string: str, sub: List[str]) -> int:
        """ Return the first index of any matching string in a list of substrings. """
        return min([string.index(s) for s in sub if s in string])

    # combine all lines into single string, adding double-space to replace linebreak
    full_line = "  ".join([l for (_, l) in lines])
    # strip leading and trailing whitespace; we don't need to keep edging linebreaks
    condensed_line = full_line.strip()
    try:
        # date must be followed by either of the following separators (one or more)
        datestamp_end_index = anyindex(condensed_line, [" ", "\n", "\t"])
    except ValueError:
        raise ParseError(f"invalid transaction", location)
    datestamp = condensed_line[:datestamp_end_index]
    try:
        d = parse_datestamp(datestamp, strict=True)
    except ValueError:
        raise ParseError(f"invalid date format ('{datestamp}')", location)
    condensed_line = condensed_line[datestamp_end_index:].strip()
    try:
        # determine where ticker ends by the first appearance of any of the following separators
        # note that by including [ as a breaker, we allow additional formatting options
        # but it also requires any position () to always be the next component after ticker
        # e.g. this format is allowed:
        #   "2019/12/31 ABC [2020/01/15] $ 1"
        # but this is not:
        #   "2019/12/31 ABC [2020/01/15] (10) $ 1"
        # it must instead be:
        #   "2019/12/31 ABC (10) [2020/01/15] $ 1"
        # (the secondary date is like a tag attached to the cash amount)
        break_index = anyindex(condensed_line, ["(", "[", "  ", "\n", "\t"])
    except ValueError:
        raise ParseError(f"invalid transaction", location)
    kind = Distribution.FINAL
    ticker = condensed_line[
        :break_index
    ].strip()  # todo: incorrect if */^ followed by newline
    if ticker.startswith("*"):
        kind = Distribution.SPECIAL
        ticker = ticker[1:].strip()
    elif ticker.startswith("^"):
        kind = Distribution.INTERIM
        ticker = ticker[1:].strip()
    condensed_line = condensed_line[break_index:].strip()
    if len(ticker) == 0:
        raise ParseError("invalid ticker format", location)
    position: Optional[float] = None
    position_change_directive = POSITION_SET
    if ")" in condensed_line:
        break_index = condensed_line.index(")") + 1
        position_str = condensed_line[:break_index].strip()
        position_str = position_str[1:-1].strip()
        if position_str.startswith("+"):
            position_change_directive = POSITION_ADD
            position_str = position_str[1:]
        elif position_str.startswith("-"):
            position_change_directive = POSITION_SUB
            position_str = position_str[1:]
        try:
            position = locale.atof(position_str)
        except ValueError:
            raise ParseError(f"invalid position ('{position_str}')", location)
        condensed_line = condensed_line[break_index:].strip()
    if len(condensed_line) == 0:
        return Transaction(
            d,
            ticker,
            -1,  # note -1 position; consider this None
            entry_attr=EntryAttributes(
                location, positioning=(position, position_change_directive)
            ),
        )

    amount_components = condensed_line.split("@")
    dividend: Optional[Amount] = None
    d3: Optional[date] = None
    if len(amount_components) > 1:
        dividend_str, dividend_datestamp = parse_amount_date(
            amount_components[1].strip()
        )
        if len(dividend_str) > 0:
            dividend = parse_amount(dividend_str, location=location)
            if dividend.value <= 0:
                raise ParseError(
                    f"negative or zero dividend ('{dividend.value}')", location
                )
        if dividend_datestamp is not None:
            try:
                d3 = parse_datestamp(dividend_datestamp, strict=True)
            except ValueError:
                raise ParseError(
                    f"invalid date format ('{dividend_datestamp}')", location
                )
    amount: Optional[Amount] = None
    d2: Optional[date] = None
    if len(amount_components) > 0:
        amount_str, amount_datestamp = parse_amount_date(amount_components[0].strip())
        if len(amount_str) > 0:
            try:
                amount = parse_amount(amount_str, location=location)
            except ParseError as e:
                lx = -1
                for (linenumber, line) in lines:
                    # todo: this is absolutely not bulletproof
                    if amount_components[0] in line:
                        lx = linenumber
                assert lx != -1
                raise ParseError(e.args[0], location=(location[0], lx))
            if amount.value < 0:
                raise ParseError(f"negative amount ('{amount.value}')", location)
        else:
            if dividend is None:
                raise ParseError(f"missing dividend amount", location)
        if amount_datestamp is not None:
            try:
                d2 = parse_datestamp(amount_datestamp, strict=True)
            except ValueError:
                raise ParseError(
                    f"invalid date format ('{amount_datestamp}')", location
                )
    return Transaction(
        d,
        ticker,
        -1,  # note -1 position; consider this None
        kind=kind,
        payout_date=d2,
        ex_date=d3,
        amount=amount,
        dividend=dividend,
        entry_attr=EntryAttributes(
            location, positioning=(position, position_change_directive)
        ),
    )


def parse_amount_date(text: str) -> Tuple[str, Optional[str]]:
    m = re.search(r"\[(.*)]", text)  # match anything encapsulated by []
    if m is None:
        return text, None
    d = m.group(1).strip()
    text = text[: m.start()] + text[m.end() :]
    return text.strip(), d


def parse_amount(amount: str, *, location: Tuple[str, int]) -> Amount:
    def isbeginning(char: str) -> bool:
        return char.isdecimal() or (
            char == "+" or char == "-" or char == "." or char == ","
        )

    symbol: Optional[str] = None
    # accumulate right-hand side of string by going through each character, in reverse
    rhs = ""
    for c in reversed(amount):
        # until finding the first occurrence of beginning of an amount
        if isbeginning(c):
            break
        rhs = c + rhs
    # assume first part of string the amount and remainder the symbol
    amount = amount[: len(amount) - len(rhs)]
    # trim trailing whitespace; leading whitespace considered intentional
    rhs = rhs.rstrip()
    # allow up to one leading whitespace
    rhs = (
        rhs[len(rhs) - len(rhs.lstrip()) - 1 :] if len(rhs) > len(rhs.lstrip()) else rhs
    )
    # accumulate left-hand side of string by going through each character
    lhs = ""
    for c in amount:
        if isbeginning(c):
            break
        lhs += c
    # assume remainder of string is the amount and lhs is the symbol
    amount = amount[len(lhs) :]
    # trim leading whitespace; trailing whitespace considered intentional
    lhs = lhs.lstrip()
    # allow up to one trailing whitespace
    lhs = lhs[: len(lhs.rstrip()) + 1] if len(lhs) > len(lhs.rstrip()) else lhs
    # parse out symbol using left/right-hand sides of the string
    if len(rhs) > 0:
        symbol = rhs.strip()
    if len(lhs) > 0:
        if symbol is not None:
            # a symbol can exist on both sides of the string, but then which one do we use?
            raise ParseError(
                f"ambiguous symbol definition ('{symbol}' or '{lhs.strip()}'?)",
                location,
            )
        symbol = lhs.strip()
    if symbol is None or len(symbol) == 0:
        raise ParseError(f"missing symbol definition", location)

    # user-entered format; either lhs or rhs will always be empty at this point
    fmt = f"{lhs}%s{rhs}"

    if len(amount) > 0:
        # an amount has been entered
        try:
            value = locale.atof(amount)
        except ValueError:
            raise ParseError(f"invalid value ('{amount}')", location)
    else:
        value = int(0)  # note int-type
        # default/fallback format
        # (when no entered amount, no formatting can be determined other than symbol)
        fmt = f"%s {symbol}"

    return Amount(value, places=decimalplaces(amount), symbol=symbol, fmt=fmt)


def read_nordnet_transactions(path: str, encoding: str = "utf-8") -> List[Transaction]:
    records = []

    with open(path, newline="", encoding=encoding) as file:
        reader = csv.reader(file, delimiter="\t")

        next(reader)  # skip headers

        line_number = 1

        for row in reader:
            line_number += 1

            if len(row) == 0:
                # skip empty rows
                continue

            transactional_type = str(row[4]).strip()

            required_transactional_types = [
                "UDB."  # danish
                # todo: type descriptions for other languages (swedish etc.)
            ]

            if not any(t == transactional_type for t in required_transactional_types):
                continue

            records.append(read_nordnet_transaction(row, location=(path, line_number)))

    return records


def read_nordnet_transaction(
    record: List[str], *, location: Tuple[str, int]
) -> Transaction:
    if len(record) < 12:
        raise ParseError(f"unexpected number of columns ({len(record)} > 12)", location)

    entry_date_value = str(record[1]).strip()
    ex_date_value = str(record[2]).strip()
    payout_date_value = str(record[3]).strip()
    ticker = str(record[5]).strip()
    position_str = str(record[8]).strip()
    dividend_str = str(record[9]).strip()
    amount_str = str(record[12]).strip()
    amount_symbol = str(record[13]).strip()
    transaction_text = str(record[19]).strip()

    # hack: some numbers may show as e.g. '1.500' which atof will parse as 1.5,
    #       when in fact it should be parsed as 1.500,00 as per danish locale
    #       so this attempts to negate that issue by removing all dot-separators,
    #       but leaving comma-decimal separator
    amount_str = amount_str.replace(".", "")
    dividend_str = dividend_str.replace(".", "")

    today = datetime.today().date()
    # parse date; expects format '2018-03-19'
    entry_date = datetime.strptime(entry_date_value, "%Y-%m-%d").date()
    if entry_date > today:
        raise ParseError(f"entry date set in future ({entry_date_value})", location)
    ex_date = datetime.strptime(ex_date_value, "%Y-%m-%d").date()
    if ex_date > today:
        raise ParseError(f"ex-dividend date set in future ({ex_date_value})", location)
    payout_date = datetime.strptime(payout_date_value, "%Y-%m-%d").date()
    if payout_date > today:
        raise ParseError(f"payout date set in future ({payout_date_value})", location)

    prev = locale.getlocale(locale.LC_NUMERIC)

    # Nordnet will provide numbers and data depending on user; set numeric locale accordingly
    # (currently assumes danish locale)
    trysetlocale(locale.LC_NUMERIC, ["da_DK", "da-DK", "da"])

    position = locale.atoi(position_str)
    amount = locale.atof(amount_str)
    dividend = locale.atof(dividend_str)

    locale.setlocale(locale.LC_NUMERIC, prev)

    transaction_text_components = transaction_text.split(" ")

    if transaction_text_components[-1].startswith("/"):
        # hack: the transaction text is sometimes split like "USD /SH"
        dividend_symbol = transaction_text_components[-2]
        dividend_rate_str = transaction_text_components[-3]
    else:
        dividend_symbol = transaction_text_components[-1].split("/")[0]
        dividend_rate_str = transaction_text_components[-2]

    # hack: for this number, it is typically represented using period for decimals
    #       but occasionally a comma sneaks in- we assume that is an error and correct it
    dividend_rate_str = dividend_rate_str.replace(",", ".")

    trysetlocale(locale.LC_NUMERIC, ["en_US", "en-US", "en"])

    try:
        dividend_rate = locale.atof(dividend_rate_str)
    except ValueError:
        raise ParseError(f"unexpected transaction text", location)

    locale.setlocale(locale.LC_NUMERIC, prev)

    assert dividend_rate is not None

    if dividend != dividend_rate:
        raise ParseError(
            f"ambiguous dividend ({dividend} or {dividend_rate}?)", location
        )

    return Transaction(
        entry_date,
        ticker,
        position,
        Amount(
            amount,
            places=decimalplaces(amount_str),
            symbol=amount_symbol,
            fmt=f"%s {amount_symbol}",
        ),
        Amount(
            dividend,
            places=decimalplaces(dividend_str),
            symbol=dividend_symbol,
            fmt=f"%s {dividend_symbol}",
        ),
        ex_date=ex_date,
        payout_date=payout_date,
    )


def max_decimal_places(amounts: Iterable[Optional[Amount]]) -> Optional[int]:
    places: Optional[int] = None
    values = [
        amount.places
        for amount in amounts
        if amount is not None and amount.places is not None
    ]
    if len(values) > 0:
        return max(values)
    return places


def write(records: List[Transaction], file: Any, *, condensed: bool = False) -> None:
    position_decimal_places: Dict[str, Optional[int]] = dict()
    payout_decimal_places: Dict[str, Optional[int]] = dict()
    dividend_decimal_places: Dict[str, Optional[int]] = dict()
    for ticker in set([record.ticker for record in records]):
        payout_decimal_places[ticker] = max_decimal_places(
            (r.amount for r in records if r.ticker == ticker)
        )
        dividend_decimal_places[ticker] = max_decimal_places(
            (r.dividend for r in records if r.ticker == ticker)
        )
        position_decimal_places[ticker] = max(
            decimalplaces(r.position) for r in records if r.ticker == ticker
        )
    for record in records:
        indicator = ""
        if record.kind is Distribution.SPECIAL:
            indicator = "* "
        elif record.kind is Distribution.INTERIM:
            indicator = "^ "
        datestamp = record.entry_date.strftime("%Y/%m/%d")
        p_decimal_places = position_decimal_places[record.ticker]
        if p_decimal_places is not None:
            p = format_amount(
                record.position, trailing_zero=False, places=p_decimal_places
            )
        else:
            p = format_amount(record.position, trailing_zero=False, rounded=False)
        line = f"{datestamp} {indicator}{record.ticker} ({p})"
        if not condensed:
            print(line, file=file)
        amount_display = ""
        if record.payout_date is not None:
            payout_datestamp = record.payout_date.strftime("%Y/%m/%d")
            amount_display += f"[{payout_datestamp}]"
        if record.amount is not None:
            amount_decimal_places = payout_decimal_places[record.ticker]
            if amount_decimal_places is not None:
                payout_display = format_amount(
                    record.amount.value, places=amount_decimal_places
                )
            else:
                payout_display = format_amount(record.amount.value, rounded=False)
            if record.amount.fmt is not None:
                payout_display = record.amount.fmt % payout_display
            amount_display += (
                f" {payout_display}"
                if record.payout_date is not None
                else payout_display
            )
        if record.dividend is not None:
            div_decimal_places = dividend_decimal_places[record.ticker]
            if div_decimal_places is not None:
                dividend_display = format_amount(
                    record.dividend.value, places=div_decimal_places
                )
            else:
                dividend_display = format_amount(record.dividend.value, rounded=False)
            if record.dividend.fmt is not None:
                dividend_display = record.dividend.fmt % dividend_display
            amount_display += (
                f" @ {dividend_display}"
                if record.payout_date is not None or record.amount is not None
                else f"@ {dividend_display}"
            )
        if record.ex_date is not None:
            exdate_datestamp = record.ex_date.strftime("%Y/%m/%d")
            amount_display += (
                f" [{exdate_datestamp}]"
                if record.dividend is not None
                else f" @ [{exdate_datestamp}]"
            )
        if len(amount_display) > 0:
            amount_line = f" {amount_display}" if condensed else f"  {amount_display}"
            if not condensed:
                print(amount_line, file=file)
            else:
                line += amount_line
        if condensed:
            print(line, file=file)
        if record != records[-1] and not condensed:
            print(file=file)
