# dledger: manual

This document provides a reference to the usage and inner workings of the [`dledger`](https://github.com/jhauberg/dledger) command-line interface tool.

## Introduction

`dledger` is a local-first, command-line tool for tracking and forecasting dividend income, hence the name "dividend ledger".

In tradition of [ledger-likes](https://plaintextaccounting.org/#plain-text-accounting-apps) and [plain-text accounting](https://plaintextaccounting.org), `dledger` is small, portable and reliable, and operates on plain-text journals that are both easy to read and quick to edit- and most importantly, all yours.

## Getting Started

**Requires Python 3.8**

The `dledger` program is built in Python and is supported on most major operating systems, including: macOS, Linux and Windows.

#### Install

```shell
$ python3 setup.py install
```

| Dependency                   | Description                                  | Version | License |
| ---------------------------- | -------------------------------------------- | ------- | ------- |
| [docopt](http://docopt.org/) | Describe and parse a command-line interface. | 0.6.2   | MIT     |

#### Usage

```shell
$ dledger --help
```

## Journals

In the ledger-like universe, a journal is a simple plain-text file that you edit and format manually- by hand.

The journal is where you keep all your transactions. Each transaction is recorded in a compatible format (see [formatting](#format-and-syntax)) and `dledger` is simply a tool to produce reports on these transactions.

There are no requirements on how you name your journal files, nor which extension to use. A common practice is to apply the `.journal` extension.

### Transactions

A `dledger` compatible transaction consist of the following elements:

1) A date
2) A ticker
3) A position
4) A cash amount

Here's an example of a genesis transaction (the first record for any given ticker), where $1 was received in dividends for a position of 10 shares in ABC (a fictional company in this context):

```
2019/01/15 ABC (10)
  $ 1
```

The next time you receive cash from ABC, you don't have to put in the number of shares you own (unless your position changed):

```
2019/04/15 ABC
  $ 1
```

If you prefer a more condensed format, you can write the transaction like this instead:

```
2019/04/15 ABC  $ 1
```

*Note that you must apply at least 2 spaces (a tab, or a new-line) between ticker and cash amount to separate the two components.*

You can extend a transaction with the exact dividend distributed per share:

```
2019/04/15 ABC
  $ 1 @ $ 0.1
```

If not manually extended, the dividend will automatically be inferred as the result of the calculation `cash / position`. This inference will always assume that the dividend is disitributed in the same currency as the cash received.

Here's an example of a transaction where the distributed dividend is in a different currency:

```
2019/01/15 ABC (10)
  $ 1 @ 10 DKK
```

This particular example establishes an [exchange rate](#exchange-rates) between DKK/$ that is applied in forecasted transactions involving these currencies.

#### Buy/sell transactions

A diligent investor will not only record their dividend transactions, but also their buy and sell transactions.

This will improve [forecasts](#forecasts) inbetween periods of dividend transactions, as payout estimates are essentially based on the calculation `position * dividend` (e.g. if you change your position but don't record it, it won't be noticeable until the next time you receive a dividend- *or don't*). 

A buy or sell transaction looks exactly like a dividend transaction, except it does not specify any cash amounts.

Here's a transaction where an additional 10 shares of ABC is bought:

```
2019/01/17 ABC (+10)
```

This transaction establishes that by January 17th, the position in ABC is now 20 shares.

Similarly, in this counter-example, 10 shares are sold, effectively closing the position:

```
2019/01/17 ABC (-10)
```

Alternatively, to avoid any confusion, the total new number of shares can be put in:

```
2019/01/17 ABC (20)  # after buying or,
2019/01/17 ABC (0)   # after selling/closing
```

*Note the lack of any minus/plus signs, indicating absolutes.*

This is a matter of preference as both methods are equally valid.

#### Special dividends

A company may occasionally choose to distribute additional cash through what is commonly referred to as a *special dividend*, or *extra dividend*. This is a non-recurring disitribution that is not considered part of the normal dividend schedule and frequency.

To record a special dividend transaction, you record the transaction like you normally would, except you also mark it with an asterisk (`*`).

```
2019/05/20 * ABC
  $ 10
```

This lets `dledger` know that this transaction is a one-time thing and should not be accounted for in forecasts.

#### Interim dividends

Recording an interim dividend transaction is similar to [recording a special dividend](#special-dividends), except you mark it with a carat (`^`) instead.

```
2019/05/20 ^ ABC
  10 EUR
```

This indicates that the transaction *is* part of the schedule and *should* be accounted for in forecasts, but the dividend projection should be independent of the regular (final) dividend.

### Locale

For the best results, `dledger` requires a reasonably well-configured environment. This includes an expectation of a configured system locale.

For macOS and Linux, this typically means setting the `LC_ALL` variable to your preferred locale/language. For example, `export LC_ALL=da_DK.UTF-8` will set a danish locale.

The locale defines the rules on how `dledger` reads and understands numbers; specifically decimal/grouping separators (or, comma vs period).

In a case where no locale has been configured (or is incorrectly configured), `dledger` will default to a US locale (en-US), which expects a period to represent the decimal separator, and commas for grouping.

You can run the [`stats`](#stats) command to see which locale `dledger` is using.

### Importing transactions

`dledger` supports importing transactions from Nordnet (a Swedish bank).

```shell
$ dledger convert transactions.csv --type=nordnet
```

This process is not perfect. It is very likely that the transactional data will contain errors such as inconsistent use of decimal separator, incorrect dates or similar. `dledger` will do its best to import data correctly and will always inform you instead of making assumptions, letting you fix/correct any invalid or ambiguous data before proceeding.

Once your data has successfully been imported, your work is not necessarily done. The import process does not take buy/sell transactions into account. Because of this, if you want better forecasts, the next step for you is to comb through `$ dledger report your.journal` and look for unexpected transactions for positions that should be closed and then close them (by editing your journal).

You don't *have* to do this, as the transactions will naturally fade away as time passes (12 months).

## Tracking methods

There are two main methods to track your dividend income:

1. By payout date

2. By ex-dividend date

Both methods involve recording the cash you receive, the only difference being *when* you record it and which date you associate with each transaction.

### By payout date

This is the most straightforward method to track your dividend income. To put it simply: when you see the cash in your account, you record the transaction. That's it.

This method requires the least amount of effort and is recommended if you just want to get an overview of your cashflow and when you can expect to have money in pocket.

### By ex-dividend date

This method requires a more hands-on approach, but does provide some benefits to the diligent investor, including:

* Tax estimations (e.g. ex-date in 2019, but payout in 2020)
* Strategic buys/sells (controlling returns)

Instead of recording the transaction on the date when cash is in your account, you record a "preliminary" transaction on the date that the stock goes ex-dividend. This is the date where you've *earned* the money. It's yours, you just won't *have it* until the payout date.

For example, here's a preliminary record of a `$ 0.73` dividend from a position in AAPL of 100 shares:

```
2019/02/08 AAPL (100)
  @ $ 0.73
```

Note that the cash amount is left blank to indicate that the transaction has not yet been realized (you don't have the money yet).

Then, at the payout date, you complete the transaction by finally entering the amount of cash that you received:

```
2019/02/08 AAPL (100)
  $ 73 @ $ 0.73
```

This method is recommended if you want to pursue a more active investing strategy (like dividend capturing or reinvesting dividends into the next upcoming payer for a quicker return).

You can extend the transaction with its payout date by applying a tag to the cash component.
```
2019/02/08 AAPL (100)
  [2019/02/14] $ 73 @ $ 0.73
```

In this particular example, the payout date only adds value to you, the reader of the journal.

However, if the cash was a different currency than the dividend, adding the date would also improve forecasted payout estimates based on the exchange rate (assuming that the cash was exchanged at payout, rather than at ex-date).

## Reports

The `report` command will show a chronological list of all dividend transactions. This includes both past, pending and [future transactions](#forecasts).

### Periods

The flag `--period` can be used to drill down and limit transactions within a date interval.

A period is specified through a simple syntax using `:` (colon) as a separator to indicate a starting and ending date.

Several shorthands are supported to ease usage. For example, the period `2019/01/01:2019/02/01` (i.e. entire January 2019) could also be specified as `2019/01`. It is automatically expanded to the previous longform. Similarly, the period shorthand `2019` will expand to `2019/01/01:2020/01/01`.

A period is always inclusive of its starting date, and exclusive of its ending date.

For example, the period `2019/01/01:2019/01/04` will include any transaction dated to either `2019/01/01`, `2019/01/02` or `2019/01/03`, but not `2019/01/04`.

Month and day does not have to be zero-padded. For example, `2019/1` is identical to `2019/01`.

You can use `:` with *only* an ending, or starting, date. In this case, the period will span from the very first transaction (oldest), up to ending date, or, from the starting date to the last (most recent) transaction, respectively. For example, the period `2019:` will include only transactions from 2019 and onwards.

You can format dates using dashes (`-`) if you prefer, e.g. `2019-01-01` is identical to `2019/01/01`.

### Grouping

There are several flags that can be used to control the appearance and grouping of transactions through the `report` command.

#### Annually

The flag `--annual` can be used to show you total income over the course of every year passed since the first recorded transaction.

```shell
$ dledger report example/simple.journal --annual
```

```console
               $ 304    2019
~              $ 308  < 2020/11
```

The report includes [forecasts](#forecasts) and preliminary records, as indicated by a `~` (tilde) prefix. In general, whenever you see a `~` to the left of an amount, this indicates that the amount is an *estimate*.

Taking a look at the last row, we might also notice that the date stands out from the others in two ways: 1) it is set in the future, and 2) it has a `<` next to it. Here, the `<` is to be read as a backwards facing arrow, indicating "by/before this date". So with this knowledge, the row now reads: "approximately $308 received by November 2020".

If a journal contains income of multiple currencies, the report is split in a section for each currency (unless `--in-currency` is specified, see [consolidating income reports](#consolidating-income-reports)).

#### Monthly

Similar to [`--annual`](#annually), the `--monthly` flag groups income received by month.

```shell
$ dledger report example/simple.journal --monthly
```

```
                $ 73    2019/02
                $ 77    2019/05
                $ 77    2019/08
                $ 77    2019/11
~               $ 77    2020/02
~               $ 77    2020/05
~               $ 77    2020/08
~               $ 77    2020/11
```

#### Quarterly

Similar to [`--annual`](#annually), the `--quarterly` flag groups income received by quarter.

```shell
$ dledger report example/simple.journal --quarterly
```

```
                $ 73    2019/Q1
                $ 77    2019/Q2
                $ 77    2019/Q3
                $ 77    2019/Q4
~               $ 77    2020/Q1
~               $ 77    2020/Q2
~               $ 77    2020/Q3
~               $ 77    2020/Q4
```

#### Trailing

The flag `--trailing` can be used to show you the total income rolling over trailing 12-month periods. This total is listed for every month passed since the very first transaction, through today.

This is a popular metric among dividend growth investors, as it (assuming that the strategy is implemented correctly), reveals a consistently rising amount of income over time.

```shell
$ dledger report example/simple.journal --trailing
```

```console
                $ 73  < 2019/03
                $ 73  < 2019/04
                $ 73  < 2019/05
               $ 150  < 2019/06
               $ 150  < 2019/07
               $ 150  < 2019/08
               $ 227  < 2019/09
               $ 227  < 2019/10
               $ 227  < 2019/11
               $ 304  < 2019/12
               $ 304  < 2020/01
~              $ 308    next 12m
```

Here, each row corresponds to the total income over the trailing 12-month period prior to the listed month (a trailing period is exclusive of the month it is trailing).

For example, in the above report, the first row represents the total income of the period ranging from `2018/03/01` (inclusive) through `2019/03/01` (exclusive). Similarly, the second row ranges from `2018/04/01` (inclusive) through `2019/04/01` (exclusive).

The report will include forecasted transactions unless `--without-forecast` is set.

The last row stands out, as it does not correspond to a trailing 12-month period, but instead represent the forecasted and future 12-month period, starting from today (inclusive).


#### Weight

The flag `--weight` can be used to weigh your income sources by ticker.

This can be useful in revealing companies that you might be overly dependent on. For example, in this overly simplified example, AAPL is 100% of our portfolio, and should they suffer a dividend cut, it would have a significant impact on our future income.

```shell
$ dledger report example/simple.journal --weight --period=2019
```

*Note the use of `--period` to only weigh income from 2019.*

```
               $ 304    100.00%    AAPL
```

Similarly, it can often be useful to weigh forecasted income instead of past income (as you buy/sell and change your positions, your future income will also change):

```shell
$ dledger report example/simple.journal --weight --period=tomorrow:
```

*Replace "tomorrow" with the date a day after today.*

```
~              $ 308    100.00%    AAPL
```

#### Sum

The flag `--sum` can be used to calculate the total (sum) of all income.

```shell
$ dledger report example/simple.journal --sum --without-forecast
```

*Note the use of `--without-forecast` to exclude any forecasted transactions.*

```
               $ 304
```

### Detailed transactions

The flag `--by-ticker` can be used to filter a report to only show transactions with a specific ticker. It also adds more details to each transaction (dividend and position).

```shell
$ dledger report example/simple.journal --by-ticker=AAPL
```

```
                $ 73    2019/02/14 AAPL           $ 0.73    (100)
                $ 77    2019/05/16 AAPL           $ 0.77    (100)
                $ 77    2019/08/15 AAPL           $ 0.77    (100)
                $ 77    2019/11/14 AAPL           $ 0.77    (100)
~               $ 77  < 2020/02/15 AAPL           $ 0.77    (100)
~               $ 77  < 2020/05/31 AAPL           $ 0.77    (100)
~               $ 77  < 2020/08/15 AAPL           $ 0.77    (100)
~               $ 77  < 2020/11/15 AAPL           $ 0.77    (100)
```

Ticker names can contain whitespace.

For example, to filter by ticker "NOVO B", you must wrap it in quotes:

```shell
$ dledger report ~/.journal --by-ticker="NOVO B"
```

### Forecasts

In addition to listing all past or pending transactions, reports also include forecasts (or projections).

These forecasts can provide you with an overview of future cashflow, based on past cashflow, and are always projected conservatively, aiming at keeping future dividends in line with recent distributions.

You can set `--without-forecast` to exclude forecasted transactions from a report entirely.

### Exchange rates

If you track any income in a currency other than the native currency for the distributing company, then an exchange rate will be determined and automatically applied to all forecasted transactions.

To determine and apply an exchange rate, a dividend must be recorded.

The exchange rate is always based on the latest recorded transaction and is *not* guaranteed to be current (i.e. `dledger` does not fetch external data).

#### Consolidating income reports

The flag `--in-currency` can be used to report all income in a specific currency. This can be particularly useful when you track and receive income in currency other than your domestic currency, but want to consolidate all reports into a single one.

This works by estimating how much the amount of cash received previously would be worth today, using the most recently known exchange rate; i.e. it does not determine what it was worth at the time of the transaction, but rather what it would be worth if exchanged today.

Income is not converted if an exchange rate is not available for a given currency pairing.

### Common/useful reports

#### Report only forecasted transactions

This can be achieved simply by using the [`--period`](#periods) flag. If you specify a period that only includes future dates, then the report will, by definition, only include forecasted transactions.

```shell
$ dledger report ~/.journal --period=tomorrow:
```

*Replace "tomorrow" with the date a day after today.*

In this example, the period will stretch from tomorrow (inclusive) through the last forecasted transaction.

#### Report forecasted income weights

Building on the [previous tip](#report-only-forecasted-transactions), you can apply a future period to weigh your forecasted income sources:

```shell
$ dledger report ~/.journal --period=tomorrow: --weight
```

*Replace "tomorrow" with the date a day after today.*

#### Next expected payouts

> This tip only applies to macOS/Linux

Sometimes it is nice to know when the next 5 or 10 expected payouts are due. This is not a built-in feature of `dledger`, but can still be achieved using existing system tools.

For this exact purpose, both macOS and Linux comes with a handy tool called `head`. This tool will read lines from the 'head' (or 'top') of an input source, until it reaches the end (or a specified limit, through the `-n` flag).

We can use this tool to list the next 5 payouts by piping a forecast report into `head`, like so:

```shell
$ dledger report ~/.journal --period=tomorrow: | head -n 5
```

*Replace "tomorrow" with the date a day after today.*

#### Most recent payouts

Similarly, the tool `tail` can be used for the same purpose, but instead of reading from the top, it reads from the bottom. This can be used to list the 5 most recent payouts:

```shell
dledger report ~/.journal --without-forecast | tail -n 5
```

*Note the use of `--without-forecast` to exclude any forecasted transactions.*

## Stats

The nifty little command `stats` will show you information on one or more journals.

```shell
$ dledger stats example/simple.journal
```

```console
 Journal 1: /Users/jhauberg/dledger/dledger/example/simple.journal
    Locale: ('da_DK', 'UTF-8')
   Records: 4
  Earliest: 2019/02/14
    Latest: 2019/11/14
   Tickers: 1
   Symbols: ['$']
```

This reveals some statistics and information on symbol/exchange rate and how `dledger` reads and expects numbers to be formatted (see [locale](#locale)).

## FAQ

#### I have a position in the same stock in multiple portfolios. How do I track this?

This is not supported. You can still track both in a single journal, but to avoid unexpected reports, you should combine each position and treat it as a single position. You can do this by consolidating the transactions.

For example, let's say you have two portfolios, each with a respective position of 100 and 50 shares in the fictional company ABC.

In this scenario, you would typically enter the following transactions:

```
2019/03/16 ABC (100)  # portfolio A
  $ 1

2019/03/16 ABC (50)   # portfolio B
  $ 0.5
```

However, these transactions contradict each other in regard to forecasting; do you have a current position of 50, or a 100?

*Note that this contradiction will stand as long as the transactions occur within the same report; i.e. you could split the transactions into separate journals, but you would also have to run individual reports per journal.*

To solve this issue, you can consolidate the individual transactions:

```
2019/03/16 ABC (150)
  $ 2
```

This clearly and explicitly states that your current, and total position, is 150 shares.
