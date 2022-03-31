# Benchmarking

Performance can be gauged by timing how fast `dledger` is at running its intended purpose in extreme cases.

## Generate benchmark data

First we need to generate a benchmark journal containing a whole bunch of records:

```shell
$ python3 gen.py
```

This should generate a `benchmark.journal` in this directory. This journal can be used for benchmarking; i.e. determining how fast `dledger` reads and performs operations on the records within.

## Running a benchmark

To run a benchmark, move to the root of the project, then run `time` on a `report` command, using the newly generated benchmark records:

```shell
$ /usr/bin/time python3 -m dledger report contrib/benchmark/benchmark.journal > /dev/null
```

*We could use the `time` command provided by your shell instead; here we use the system built-in executable.*

This clocks in how long it took to execute the given command; in this case, a `report` command involving parsing, projecting and spitting out a forecast.

*Note that we pipe all `dledger` generated output to `/dev/null` because in this case we're not actually interested in seeing any of that.*

```console
        0.82 real         0.79 user         0.01 sys
```

These timings will obviously differ depending on the system it runs on; but they can be used to gauge relative performance loss/increase when performed on the same machine.
