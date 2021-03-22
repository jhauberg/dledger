import sys

from datetime import datetime, date

sys.path.append('../../')

from dledger.journal import Transaction, Amount, write
from dledger.dateutil import previous_month

today = datetime.today().date()

starting_date = date(today.year, today.month, 1)

MAX_RECORDS = 10000

# generate monthly transactions, starting from this month, going back MAX_RECORDS months
records = []

d = starting_date
while len(records) < MAX_RECORDS:
    records.append(
        Transaction(
            entry_date=d,
            ticker="ABC",
            position=10,
            amount=Amount(1, fmt="$ %s")
        )
    )
    d = previous_month(d)

records.sort()

with open("benchmark.journal", "w") as file:
    write(records, file, condensed=True)
