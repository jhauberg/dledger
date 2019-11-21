from dledger.journal import read


def test_transactions():
    records = read('../example/simple.journal', kind='journal')

    assert len(records) == 4

    records = read('../example/simple-condensed.journal', kind='journal')

    assert len(records) == 4

    records = read('../example/dividends.journal', kind='journal')

    assert len(records) == 4

    records = read('../example/positions.journal', kind='journal')

    assert len(records) == 5

    records = read('../example/positions-condensed.journal', kind='journal')

    assert len(records) == 5
