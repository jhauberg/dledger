# $ dledger

`dledger` is a local-first, command-line tool for tracking and forecasting dividend income.

In tradition of [ledger-likes](https://plaintextaccounting.org/#plain-text-accounting-apps) and [plain-text accounting](https://plaintextaccounting.org), `dledger` is small, portable and reliable, and operates on plain-text journals that are both easy to read and quick to edit- and most importantly, future-proof and all yours.

Reports and forecasts are based entirely on your own data; no external data sources are used. This allows `dledger` to work for any investor, no matter the location and choice of currency.

<br />

| [Latest release (0.8.0)](https://github.com/jhauberg/dledger/releases/tag/0.8.0) | Download the latest stable release.                 |
| :------------------------------------------------------------------------------- | :-------------------------------------------------- |
| [Issue tracker](https://github.com/jhauberg/dledger/issues)                      | Contribute your bugs, comments or feature requests. |
| [Manual](MANUAL.md)                                                              | Instructions on [setup](MANUAL.md#install) and detailed usage.           |

<br />

## Example

Here's a journal that tracks a position of 100 shares of Apple over 3 transactions:

```
2019/02/14 AAPL (100)
  $ 73

2019/05/16 AAPL
  $ 77

2019/08/15 AAPL
  $ 77
```

<sup>&nbsp;&nbsp;A plain-text **.journal** file</sup>

### Reporting and Forecasting

Running a report shows all historical dividend income, including forecasts for the next 12 months:

```shell
$ dledger report ~/.journal
```
```console
                $ 73    2019/02/14 AAPL
                $ 77    2019/05/16 AAPL
                $ 77    2019/08/15 AAPL
~               $ 77 <~ 2019/11/15 AAPL
~               $ 77 <~ 2020/02/15 AAPL
~               $ 77 <~ 2020/05/31 AAPL
~               $ 77 <~ 2020/08/15 AAPL
```

Read the [manual](MANUAL.md#reports) to learn more.

<br />

<table>
  <tr>
    <td>
      This is a Free and Open-Source Software project released under the <a href="LICENSE">MIT License</a>.
    </td>
  </tr>
</table>
