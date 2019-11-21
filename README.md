# dledger

`dledger` is a local-first, command-line tool for tracking and forecasting dividend income.

In tradition of [ledger-likes](https://plaintextaccounting.org/#plain-text-accounting-apps) and [plain-text accounting](https://plaintextaccounting.org), `dledger` operates on a plain-text format that is both easy to read and quick to edit. Small, portable and dependable. No strings attached.

---

Here's a journal that tracks a position of 100 Apple shares over 3 transactions:

```
2019/02/14 AAPL (100)
  $ 73

2019/05/16 AAPL
  $ 77

2019/08/15 AAPL
  $ 77
```

Running `dledger` shows all dividends received, including forecasts for the next 12 months:

```shell
$ dledger report ~/.journal
                $ 73    2019/02/14 AAPL
                $ 77    2019/05/16 AAPL
                $ 77    2019/08/15 AAPL
~               $ 75  < 2019/11/15 AAPL
~               $ 73  < 2020/02/15 AAPL
~               $ 77  < 2020/05/30 AAPL
~               $ 77  < 2020/08/15 AAPL
```

Using the `--annual` flag will sum up dividends by year:

```shell
$ dledger report ~/.journal --annual
~              $ 302    2019
~              $ 227  < 2020/08
```

Read the [manual](MANUAL.md) to learn more.

## License

This is a Free and Open-Source software project released under the [MIT License](LICENSE).
