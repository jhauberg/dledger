# $ dledger

A local-first, command-line tool for tracking and forecasting dividend income.

In tradition of [ledger-likes](https://plaintextaccounting.org/#plain-text-accounting-apps) and [plain-text accounting](https://plaintextaccounting.org), `dledger` is small, portable and reliable, and performs reports on plain-text journals that are both easy to read and quick to edit. Use it to get a better picture of your current and future dividend cashflow.

Reports and forecasts are based entirely on your own data; no external sources are used and no data ever leaves your hands.

<br />

| [Latest release (0.11.0)](https://github.com/jhauberg/dledger/releases/tag/0.11.0) | Download the latest stable release.                            |
| :--------------------------------------------------------------------------------- | :------------------------------------------------------------- |
| [Issue tracker](https://github.com/jhauberg/dledger/issues)                        | Contribute your bugs, comments or feature requests.            |
| [Manual](MANUAL.md)                                                                | Instructions on [setup](MANUAL.md#install) and detailed usage. |

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
~               $ 77 <~ 2020/02/14 AAPL                 14 Feb
~               $ 77 <~ 2020/05/29 AAPL              15-18 May
~               $ 77 <~ 2020/08/14 AAPL              14-17 Aug
```

This particular report projects that (if following its recent schedule), Apple will distribute 4 dividends over the next 12 months; **Nov**, **Feb**, **May** and **Aug**.

The projected dividends are estimates based on latest-known exchange rates (if applicable), and distribution dates are forecast with up to two levels of specificity: 1) most likely in either the first or second half of a given month, and 2) likely within a range of previously observed dates.

Read the [manual](MANUAL.md#reports) to learn more.

<br />

<table>
  <tr>
    <td>
      This is a Free and Open-Source Software project released under the <a href="LICENSE">MIT License</a>.
    </td>
  </tr>
</table>
