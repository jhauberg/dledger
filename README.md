# dledger

`dledger` is a local-first, command-line tool for tracking and forecasting dividend income.

In tradition of [ledger-likes](https://plaintextaccounting.org/#plain-text-accounting-apps) and [plain-text accounting](https://plaintextaccounting.org), `dledger` is small, portable and reliable, and operates on plain-text journals that are both easy to read and quick to edit- and most importantly, all yours.

**Requires Python 3.8+**

---

Here's a journal that tracks a position of 100 shares of Apple over 3 transactions:

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
```
```console
                $ 73    2019/02/14 AAPL
                $ 77    2019/05/16 AAPL
                $ 77    2019/08/15 AAPL
~               $ 77  < 2019/11/15 AAPL
~               $ 77  < 2020/02/15 AAPL
~               $ 77  < 2020/05/31 AAPL
~               $ 77  < 2020/08/15 AAPL
```

Using the `--annual` flag will sum up dividends by year:

```shell
$ dledger report ~/.journal --annual
```
```console
~              $ 304    2019
~              $ 231  < 2020/08
```

Read the [manual](MANUAL.md) to learn more.

## License

This is a Free and Open-Source software project released under the [MIT License](LICENSE).
