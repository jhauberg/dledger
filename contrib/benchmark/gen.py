import sys

from datetime import datetime, date, timedelta

sys.path.append("../../")

from dledger.journal import Transaction, Amount, EntryAttributes, write
from dledger.dateutil import previous_month


def first_non_weekend_weekday(a: date):
    b = date(a.year, a.month, 1)
    while b.weekday() in [5, 6]:
        b = b + timedelta(days=1)
    return b


today = datetime.today().date()
starting_date = date(today.year, today.month, 1)

MAX_RECORDS = 10000

# generate monthly transactions, starting from this month, going back MAX_RECORDS months
records = []

d = first_non_weekend_weekday(starting_date)
while len(records) < MAX_RECORDS:
    records.append(
        Transaction(
            entry_date=d,
            ticker="ABC",
            position=10,
            amount=Amount(1, fmt="%s kr"),
            dividend=Amount(0.1, fmt="$ %s"),
            tags=["a", "b", "c"],
            entry_attr=EntryAttributes(
                location=("fantasy", -1),  # not important in this case
                positioning=(None, 0),  # not important in this case
            ),
        )
    )
    d = first_non_weekend_weekday(previous_month(d))

assert len(records) > 0

records.sort()

# note that we never apply system locale in this script, so decimals will
# always be written using default period (".") separator
# this can cause reports to display unexpected values; though, it should not
# matter for the purposes of this script, so just take note of it
with open("benchmark.journal", "w") as file:
    write(records, file, condensed=True)
