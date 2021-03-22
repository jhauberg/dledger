# Testing and Coverage

Tests for `dledger` can be run using [pytest](https://pytest.org).

## Running tests

Move into the `test` directory and run `pytest`:

```shell
$ pytest
```

## Installing coverage plugin

Additionally, a [coverage plugin](https://pypi.org/project/pytest-cov/) can be installed to `pytest`, making it able to show coverage for the entire test suite; this is useful to reveal code paths that are not taken by any test, and thus, are not covered and tested.

```shell
$ pip install pytest-cov
```

## Running tests with coverage

Make sure you're still in the `test` directory, then add the `--cov` argument to `pytest`:

```shell
$ pytest --cov=dledger
```

## Build report (optional)

To get a better understanding of exactly which code paths lack coverage, a HTML report can be made.

### Install coveragepy

The `pytest-cov` plugin should automatically have installed [coveragepy](https://github.com/nedbat/coveragepy) as well, but in case it has not, install it:

```shell
$ pip install coverage
```

### Make HTML report

Given a successful test/coverage run, the findings can be made into a neatly navigable report:

```shell
$ coverage html
```

The report can then be read at `htmlcov/index.html`.

For convenience, chain run/report together:

```shell
$ pytest --cov=dledger && coverage html
```
