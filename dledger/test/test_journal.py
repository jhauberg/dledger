from dledger.journal import transactions


def test_transactions():
    records = transactions('../example/simple.journal', kind='journal')

    assert len(records) == 4

    records = transactions('../example/simple-condensed.journal', kind='journal')

    assert len(records) == 4
