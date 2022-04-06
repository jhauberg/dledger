import csv
import re
import math
import locale
import os

from dledger.localeutil import DECIMAL_POINT_COMMA, DECIMAL_POINT_PERIOD, tempconv
from dledger.formatutil import format_amount, decimalplaces, truncate_floating_point
from dledger.fileutil import fileencoding
from dledger.dateutil import parse_datestamp, todayd

from dataclasses import dataclass, replace
from datetime import datetime, date

from typing import List, Union, Tuple, Optional, Any, Dict, Iterable
from enum import Enum

SUPPORTED_TYPES = ["journal", "nordnet"]

POSITION_SET = 0           # (= 1) or blank; directive to set or infer absolute position
POSITION_ADD = 1           # (+ 1) directive to add to previous position
POSITION_SUB = -1          # (- 1) directive to subtract from previous position
POSITION_SPLIT = -2        # (X 2/1) directive to split keeping fractional position
POSITION_SPLIT_WHOLE = -3  # (x 2/1) directive to split keeping whole position


class Distribution(Enum):
    """Represents the type of a dividend distribution."""

    FINAL = 0
    INTERIM = 1
    SPECIAL = 2


@dataclass(frozen=True, unsafe_hash=True)
class Amount:
    """Represents a cash amount."""

    value: Union[float, int]
    places: Optional[int] = None
    symbol: Optional[str] = None
    fmt: Optional[str] = None


@dataclass(frozen=True)
class EntryAttributes:
    """Represents a set of attributes describing some facts about a journal
    entry.

    These are properties that can only be known at parse-time, as a journal
    entry may undergo several processing steps ultimately changing its
    final representation.

    For example, whether a record is preliminary or not cannot be deduced after
    processing as it will end up having a generated amount attached to it
    (where it would otherwise be `None`).
    """

    location: Tuple[str, int]  # journal:linenumber
    # todo: we need this information during parsing in order to infer an
    #       absolute position, however, once we're done parsing, this field
    #       rarely becomes very useful later on, as it will generally always
    #       equal (position, POSITION_SET), this is the case since because
    #       positional records are typically redundant and will be pruned anyway
    #       consider whether we can do something to make this more useful?
    positioning: Tuple[
        Optional[float], int
    ]  # position/change:directive (i.e. POSITION_*)
    is_preliminary: bool = False  # True if amount component left blank intentionally
    preliminary_amount: Optional[Amount] = None


@dataclass(frozen=True, unsafe_hash=True)
class Transaction:
    """Represents a transactional record."""

    entry_date: date  # no assumption whether this is payout, ex-date or other
    ticker: str
    position: float  # absolute position
    amount: Optional[Amount] = None
    dividend: Optional[Amount] = None
    kind: Distribution = Distribution.FINAL
    payout_date: Optional[date] = None
    ex_date: Optional[date] = None
    tags: Optional[List[str]] = None
    entry_attr: Optional[EntryAttributes] = None

    @property
    def ispositional(self) -> bool:
        """Return `True` if transaction only records a position component,
        `False` otherwise.

        This is typically the case for a buy/sell transaction.
        """
        return self.amount is None and self.dividend is None

    def __lt__(self, other):  # type: ignore
        def literal_location(r: Transaction) -> Tuple[str, int]:
            return r.entry_attr.location if r.entry_attr is not None else ("", 0)

        # sort by entry date and always put buy/sell transactions later if on same date
        # e.g.  2019/01/01 ABC (+10)
        #       2019/01/01 ABC (10)  $ 1
        #   =>
        #       2019/01/01 ABC (10)  $ 1
        #       2019/01/01 ABC (+10)
        # thirdly, take literal order in journal into account (both linenumber and path)
        # finally, stabilize sorting using ticker for alphabetical ordering
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


def read(path: str, *, kind: str) -> List[Transaction]:
    """Return a list of records imported from a file."""

    try:
        encoding = fileencoding(path)
    except FileNotFoundError:
        encoding = None

    if encoding is None or len(encoding) == 0:
        raise ValueError(f"Path could not be read: '{path}'")

    if kind == "journal":
        return read_journal_transactions(path, encoding)
    elif kind == "nordnet":
        return read_nordnet_transactions(path, encoding)
    else:
        raise ValueError(f"unsupported transaction type")


def read_journal_transactions(path: str, encoding: str = "utf-8") -> List[Transaction]:
    journal_entries = []

    # note that this pattern will initially let inconsistent formatting pass through
    # (e.g. 2019/12-1), but will eventually raise a formatting error later on
    # (it is faster to skip validation through parse_datestamp at this point)
    transaction_start = re.compile(r"[0-9]+[-/][0-9]+[-/][0-9]+")
    # any (stripped) line starting with "include" is considered an inclusion directive;
    # handled as it occurs in the journal
    include_start = re.compile(r"include")

    with open(path, newline="", encoding=encoding) as file:
        line_number = 0
        lines: List[Tuple[int, str]] = []
        # start reading, line by line; each line being part of the current transaction
        # once we encounter a line starting with what looks like a date, we take that
        # to indicate the beginning of next transaction and parse all lines
        # up to this point (excluding that line), and then repeat until end of file
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
                        lines = lines[len(lines) - offset :]
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
                    relative_include_path = line[len("include") :].strip()
                    if relative_include_path.startswith('"'):
                        relative_include_path = relative_include_path[1:].strip()
                    if relative_include_path.endswith('"'):
                        relative_include_path = relative_include_path[:-1].strip()
                    include_path = os.path.normcase(
                        os.path.join(os.path.dirname(path), relative_include_path)
                    )
                    if os.path.samefile(path, include_path):
                        raise ParseError(
                            "attempt to recursively include journal",
                            location=(path, line_number),
                        )
                    # note that implicit dependencies could potentially be handled here
                    # by passing on the current list of records to the read function or
                    # something similar- for now this is just linearly drilling down
                    # through each journal and its explicit dependencies
                    journal_entries.extend(
                        # note that this assumes all included journals are of identical
                        # encoding; if we instead went `read(.., kind="journal"), then
                        # this would not support pruning redundant records
                        # (as they might be needed during recursion)
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
            for n, (previous_line_number, previous_line) in enumerate(reversed(lines)):
                if transaction_start.match(previous_line) is not None:
                    offset = n + 1
                    lines = lines[len(lines) - offset :]
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

    return infer(journal_entries)


def infer(entries: Iterable[Transaction]) -> List[Transaction]:
    transactions: List[Transaction] = []

    for record in entries:
        assert record.entry_attr is not None

        # inferrable properties: Position, Dividend (and Entry Attributes)
        # i.e. these may differ from original entry to the resulting transaction
        attr = record.entry_attr
        position, position_directive = attr.positioning
        dividend = record.dividend

        if position is None or (
            position_directive == POSITION_ADD
            or position_directive == POSITION_SUB
            or position_directive == POSITION_SPLIT
            or position_directive == POSITION_SPLIT_WHOLE
        ):
            # infer position from previous entries
            by_ex_date = sorted(
                transactions,
                key=lambda r: (
                    r.ex_date if r.ex_date is not None else r.entry_date,
                    r.ispositional,
                ),
            )

            for previous_record in reversed(by_ex_date):
                if previous_record.ticker == record.ticker:
                    if previous_record.position is None:
                        continue
                    if (
                        record.ex_date is not None
                        and previous_record.entry_date > record.ex_date
                    ):
                        continue
                    if position is None:
                        position = 0
                    if position_directive == POSITION_SPLIT:
                        position = truncate_floating_point(
                            previous_record.position * position
                        )
                    elif position_directive == POSITION_SPLIT_WHOLE:
                        position = truncate_floating_point(
                            math.floor(previous_record.position * position)
                        )
                    else:
                        position = truncate_floating_point(
                            previous_record.position + (position * position_directive)
                        )
                    if position < 0:
                        raise ParseError(
                            f"position change to negative position ({position})",
                            attr.location,
                        )
                    break

        if record.amount is not None and record.dividend is not None:
            if record.amount.symbol == record.dividend.symbol:
                inferred_p = record.amount.value / record.dividend.value
                if position is not None:
                    # determine whether literal position is close enough to the
                    # inferred position; note that the precision here should match
                    # the precision of any inferred dividend
                    precision = 0.000001
                    if record.dividend.places is not None:
                        denominator = "1" + ("0" * (record.dividend.places - 1))
                        precision = 1 / int(denominator)
                    if not math.isclose(position, inferred_p, abs_tol=precision):
                        raise ParseError(
                            f"ambiguous position ({position} or {inferred_p}?)",
                            attr.location,
                        )
                else:
                    position = truncate_floating_point(inferred_p)

        if position is None:
            raise ParseError(f"position could not be inferred", attr.location)

        if record.amount is not None and position == 0:
            raise ParseError(f"payout on closed position", attr.location)

        if record.amount is not None and record.dividend is None:
            inferred_dividend = truncate_floating_point(
                record.amount.value / position, places=4
            )
            dividend = Amount(
                inferred_dividend,
                places=decimalplaces(inferred_dividend),
                symbol=record.amount.symbol,
                fmt=record.amount.fmt,
            )

        if record.amount is None and dividend is None:
            if record.payout_date is not None or record.ex_date is not None:
                raise ParseError(f"associated date on positional record", attr.location)

        if record.payout_date is not None and record.ex_date is not None:
            if record.payout_date < record.ex_date:
                raise ParseError(
                    f"payout date dated earlier than ex-date", attr.location
                )

        is_incomplete = False
        prelim_amount = None
        if (
            record.amount is None
            or record.amount is not None
            and record.amount.value == 0
        ) and dividend is not None:
            prelim_amount = record.amount
            is_incomplete = True

        attr = replace(
            attr, preliminary_amount=prelim_amount, is_preliminary=is_incomplete
        )

        record = replace(
            record,
            amount=record.amount if prelim_amount is None else None,
            entry_attr=attr,
            position=position,
            dividend=dividend,
        )

        transactions.append(record)
    return transactions


def strip_tags(text: str) -> Tuple[str, List[str]]:
    def strip_tag(match) -> str:
        tags.append(match.group(0))
        return ""

    tags: List[str] = []
    text = re.sub(r";\S+", strip_tag, text)
    tags = [tag[1:] for tag in tags]
    return text, tags


def read_journal_transaction(
    lines: List[Tuple[int, str]], *, location: Tuple[str, int]
) -> Transaction:
    if len(lines) == 0:
        raise ParseError("invalid transaction", location)

    def anyindex(string: str, sub: List[str]) -> int:
        """Return the first index of any matching string in a list of
        substrings."""
        return min([string.index(s) for s in sub if s in string])

    # combine all lines into single string, adding double-space to replace linebreak
    full_line = "  ".join([l for (_, l) in lines])
    # strip leading and trailing whitespace; we don't need to keep edging linebreaks
    condensed_line = full_line.strip()
    # strip and keep tags
    condensed_line, tags = strip_tags(condensed_line)
    try:
        # date must be followed by either of the following separators (one or more)
        datestamp_end_index = anyindex(condensed_line, [" ", "\t"])
    except ValueError:
        raise ParseError(f"invalid transaction", location)
    datestamp = condensed_line[:datestamp_end_index]
    try:
        d = parse_datestamp(datestamp, strict=True)
    except ValueError:
        raise ParseError(f"invalid date format ('{datestamp}')", location)
    condensed_line = condensed_line[datestamp_end_index:].strip()
    try:
        # determine where ticker ends by the first appearance of any of the separators;
        # note that by including [ as a breaker, we allow additional formatting options
        # but also requires any position () to always be the next component after ticker
        # e.g. this format is allowed:
        #   "2019/12/31 ABC [2020/01/15] $ 1"
        # but this is not:
        #   "2019/12/31 ABC [2020/01/15] (10) $ 1"
        # it must instead be:
        #   "2019/12/31 ABC (10) [2020/01/15] $ 1"
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

        def parse_position(text: str) -> float:
            try:
                return locale.atof(text)
            except ValueError:
                raise ParseError(f"invalid position ('{text}')", location)

        if position_str.startswith("="):
            # for example: "(= 10)"
            position_change_directive = POSITION_SET
            position = parse_position(position_str[1:])
        elif position_str.startswith("+"):
            # for example: "(+ 10)"
            position_change_directive = POSITION_ADD
            position = parse_position(position_str[1:])
        elif position_str.startswith("-"):
            # for example: "(- 10)"
            position_change_directive = POSITION_SUB
            position = parse_position(position_str[1:])
        elif position_str.lower().startswith("x"):
            # for example: "(x 4/1)"
            # todo: maybe prefer something that augments the "x"; maybe "x~" ?
            position_change_directive = (
                POSITION_SPLIT  # keep fractional shares
                if position_str.startswith("X")
                else POSITION_SPLIT_WHOLE  # keep whole shares; considered default
            )
            position_str = position_str[1:]
            if "/" not in position_str:
                raise ParseError(
                    f"invalid split directive ('{position_str}')", location
                )
            split_components = position_str.split("/")
            if len(split_components) != 2:
                raise ParseError(
                    f"invalid split directive ('{position_str}')", location
                )
            try:
                # position actually becomes a multiplier in this case,
                # rather than an absolute position
                a = locale.atof(split_components[0])
                b = locale.atof(split_components[1])
            except ValueError:
                raise ParseError(f"invalid position ('{position_str}')", location)
            position = a / b
        else:
            # default to set/= directive
            position_change_directive = POSITION_SET
            position = parse_position(position_str)
        condensed_line = condensed_line[break_index:].strip()
    if len(condensed_line) == 0:
        return Transaction(
            d,
            ticker,
            -1,  # note -1 position; consider this None
            tags=tags if len(tags) > 0 else None,
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
        tags=tags if len(tags) > 0 else None,
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
            # a symbol can exist on both sides of the string,
            # but then which one do we use?
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

    required_headers = {
        1: "Bogføringsdag",
        2: "Handelsdag",
        3: "Valørdag",
        6: "Værdipapirer",
        9: "Antal",
        10: "Kurs",
        14: "Beløb",
        15: "Valuta",
        21: "Transaktionstekst",
    }

    with open(path, newline="", encoding=encoding) as file:
        reader = csv.reader(file, delimiter="\t")

        headers = next(reader)

        line_number = 1
        location = (path, line_number)

        required_min_header_count = sorted(required_headers.keys())[-1] + 1
        if len(headers) < required_min_header_count:
            raise ParseError(
                f"unexpected number of columns "
                f"({len(headers)} < {required_min_header_count})",
                location,
            )

        for column, expected_header in required_headers.items():
            header = str(headers[column]).strip()
            if header != expected_header:
                raise ParseError(
                    f"unexpected header at column {column} "
                    f'("{header}" != "{expected_header}")',
                    location,
                )

        for row in reader:
            line_number += 1
            location = (path, line_number)

            if len(row) == 0:
                # skip empty rows
                continue

            transactional_type = str(row[5]).strip()

            if transactional_type == "MAK. UDB.":
                # note that we can't reasonably know which transaction is actually
                # being reverted; even if we sort chronologically later and know the
                # ticker, it is still not guaranteed to be "in order"
                # so better bail out and have user fix the issue- similarly,
                # with ambiguous values, we don't make any guesses as we simply
                # cannot be certain which option is correct
                raise ParseError(
                    f"earlier transaction reverted; proceeding would cause duplicates",
                    location,
                )

            required_transactional_types = [
                "UDB."  # danish
                # todo: type descriptions for other languages (swedish etc.)
            ]

            if not any(t == transactional_type for t in required_transactional_types):
                continue

            records.append(
                read_nordnet_transaction(row, required_headers, location=location)
            )

    return records


def read_nordnet_transaction(
    columns: List[str], headers: Dict[int, str], *, location: Tuple[str, int]
) -> Transaction:
    if len(columns) < 22:
        raise ParseError(
            f"unexpected number of columns ({len(columns)} < 22)", location
        )

    values = [str(columns[column]).strip() for column in headers.keys()]
    # assuming order remains identical
    (
        entry_date_value,
        ex_date_value,
        payout_date_value,
        ticker,
        position_str,
        dividend_str,
        amount_str,
        amount_symbol,
        transaction_text,
    ) = values

    # hack: some numbers may show as e.g. '1.500' which atof will parse as 1.5,
    #       when in fact it should be parsed as 1.500,00 as per danish locale
    #       so this attempts to negate that issue by removing all dot-separators,
    #       but leaving comma-decimal separator
    amount_str = amount_str.replace(".", "")
    dividend_str = dividend_str.replace(".", "")

    today = todayd()
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

    # we have to assume either period or comma as decimal point here,
    # as we can't just rely on system locale- nordnet transactions will always
    # be either one or the other- not necessarily matching system locale
    with tempconv(DECIMAL_POINT_COMMA):
        position = locale.atoi(position_str)
        amount = locale.atof(amount_str)
        dividend = locale.atof(dividend_str)

    if "/" not in transaction_text:
        raise ParseError(f'unexpected transaction text: "{transaction_text}"', location)

    transaction_text_components = transaction_text.split("/")
    if len(transaction_text_components) > 2:
        raise ParseError(f'unexpected transaction text: "{transaction_text}"', location)

    # we only care about the left-hand side result
    transaction_text_components = transaction_text_components[0].strip().split(" ")
    if len(transaction_text_components) < 2:
        raise ParseError(f'unexpected transaction text: "{transaction_text}"', location)

    dividend_symbol = transaction_text_components[-1]
    dividend_rate_str = transaction_text_components[-2]

    # hack: for this number, it is typically represented using period for decimals, but
    #       occasionally a comma sneaks in- we assume that is an error and correct it
    dividend_rate_str = dividend_rate_str.replace(",", ".")

    try:
        # again, we have to assume one or the other here- in most cases
        # this column uses period decimal point
        with tempconv(DECIMAL_POINT_PERIOD):
            dividend_rate = locale.atof(dividend_rate_str)
    except ValueError:
        raise ParseError(f'unexpected transaction text: "{transaction_text}"', location)

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
        entry_attr=EntryAttributes(location, positioning=(position, POSITION_SET)),
    )


def max_decimal_places(amounts: Iterable[Optional[Amount]]) -> Optional[int]:
    all_amounts = [amount for amount in amounts if amount is not None]
    places_by_preference = [
        amount.places for amount in all_amounts if amount.places is not None
    ]
    max_decimals: Optional[int] = None
    if len(places_by_preference) > 0:
        max_decimals = max(places_by_preference)
    places_by_inference = [
        decimalplaces(amount.value) for amount in all_amounts if amount.places is None
    ]
    if len(places_by_inference) > 0:
        for places in places_by_inference:
            if max_decimals is None or (max_decimals < 2 and places > max_decimals):
                # determine whether this amount actually has more decimals than the
                # preference (i.e. potentially hiding some value [see #21])
                # but clamp to no more than 2 decimal places;
                # typically this would be a generated amount
                max_decimals = min(places, 2)
    return max_decimals


def write(records: List[Transaction], file: Any, *, condensed: bool = False) -> None:
    # the guiding principle of writing/printing is that given an input,
    # the output must produce identical reports to the input, but written in the
    # most legible/explicit way possible; to comply with that, there are some
    # special cases that must be handled- namely positional records;
    # these can typically be omitted, except for those with split directives;
    # to produce an identical report, splits must be either retained _or_ past
    # records adjusted; the latter means altering truths and is not acceptable;
    # thus, splits must be retained
    # it could be argued that given this, all positional records should simply
    # be retained, if only for posterity, however, 1) they are not required to
    # produce identical reports, and 2) they are primarily used as interim records
    # to improve forecasting; dledger is not a portfolio tracker, and buy/sells
    # are not the focus of the program- splits are an exception, as those are
    # useful pieces of information to retain
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
            decimalplaces(r.position)
            for r in records
            if r.ticker == ticker and
            # don't include split directives (as the position property
            # holds a multiplier; not an absolute position)
            (
                r.entry_attr is None
                or (
                    r.entry_attr.positioning[1] != POSITION_SPLIT
                    and r.entry_attr.positioning[1] != POSITION_SPLIT_WHOLE
                )
            )
        )
    for record in records:
        indicator = ""
        if record.kind is Distribution.SPECIAL:
            indicator = "* "
        elif record.kind is Distribution.INTERIM:
            indicator = "^ "
        datestamp = record.entry_date.strftime("%Y/%m/%d")
        assert record.entry_attr is not None
        transient_position, directive = record.entry_attr.positioning
        if directive == POSITION_SPLIT or directive == POSITION_SPLIT_WHOLE:
            assert transient_position is not None
            from fractions import Fraction

            fraction = Fraction(transient_position).limit_denominator()
            split = f"{fraction.numerator}/{fraction.denominator}"
            if record.entry_attr.positioning[1] == POSITION_SPLIT_WHOLE:
                p = f"x {split}"
            else:
                p = f"X {split}"
        else:
            decimals = position_decimal_places[record.ticker]
            if decimals is not None:
                p = format_amount(record.position, trailing_zero=False, places=decimals)
            else:
                p = format_amount(record.position, trailing_zero=False, rounded=False)
        line = f"{datestamp} {indicator}{record.ticker} ({p})"
        if record.tags is not None and len(record.tags) > 0:
            for tag in record.tags:
                line += f" ;{tag}"
        if not condensed:
            print(line, file=file)
        amount_display = ""
        if record.payout_date is not None:
            payout_datestamp = record.payout_date.strftime("%Y/%m/%d")
            amount_display += f"[{payout_datestamp}]"
        if record.amount is not None:
            decimals = (
                record.amount.places
                if record.amount.places is not None
                else payout_decimal_places[record.ticker]
            )
            if decimals is not None:
                payout_display = format_amount(record.amount.value, places=decimals)
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
            decimals = (
                record.dividend.places
                if record.dividend.places is not None
                else dividend_decimal_places[record.ticker]
            )
            if decimals is not None:
                dividend_display = format_amount(record.dividend.value, places=decimals)
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
