# dledger: manual

This document provides a reference to the usage and inner workings of the [`dledger`](https://github.com/jhauberg/dledger) command-line interface tool.

## Introduction

`dledger` is a local-first, command-line tool for tracking and forecasting dividend income; hence the name "dividend" or "dollar ledger", both "dledger" for short.

In tradition of [ledger-likes](https://plaintextaccounting.org/#plain-text-accounting-apps) and [plain-text accounting](https://plaintextaccounting.org), `dledger` is small, portable and reliable, and operates on plain-text journals that are both easy to read and quick to edit- and most importantly, all yours.

## Getting Started

**Requires Python 3.8+**

The `dledger` program is built in Python and is supported on most major operating systems, including: macOS, Linux and Windows.

### Install

```shell
$ python3 setup.py install
```

| Dependency                   | Description                                  | Version | License |
| :--------------------------- | :------------------------------------------- | :------ | :------ |
| [docopt](http://docopt.org/) | Describe and parse a command-line interface. | 0.6.2   | MIT     |

If the installation is successful, you should now be able to run `dledger`:

```shell
$ dledger --version
```

```console
dledger 0.6.1
```

Depending on your Python setup, you might have to run `dledger` as a module:

```shell
$ python3 -m dledger --version
```

Similarly, you can also use the above command to run `dledger` without installing it (just navigate to project root).

### Usage

The `dledger` program has many commands, flags and arguments. You can get an overview of all usage patterns through `--help`:

```shell
$ dledger --help
```

This might seem overwhelming, but the typical usage is `$ dledger <command> <journal> <flags>`, where `<flags>` are always an optional set of flags.

For example, the most common command-line to run a report is simply:

```shell
$ dledger report ~/my.journal
```

This invokes `dledger` using the `report` command on the journal-file located at e.g. `/Users/jhauberg/my.journal`.

You can provide paths to more than one journal. For example, you might want to keep a journal per year:

```shell
$ dledger report ~/2018.journal ~/2019.journal
```

This produces a report that includes transactions from both journals, ordered chronologically.

# Journals

In the ledger-like universe, a journal is a simple [plain-text](https://en.wikipedia.org/wiki/Plain_text) file that you edit and format manually- by hand.

The journal is where you keep all your transactions. Each transaction is recorded in a compatible format and `dledger` is simply a tool to process and produce reports on these transactions.

There are no requirements on how you edit or name your journal files, nor which extension to use. A common practice is to apply the `.journal` extension.

Here's an [example journal-file](dledger/example/simple.journal), for reference:

```
# this file serves as an example journal for dledger

2019/02/14 AAPL (100)
  $ 73

2019/05/16 AAPL
  $ 77

2019/08/15 AAPL
  $ 77

2019/11/14 AAPL
  $ 77
```

*Note that the hashtag/pound-symbol here indicates a line that is a comment for the human reader; the program will just ignore it.*

The example journals might not report any forecasts if the latest record is more than a year old.

## Keeping journals

You can keep as many journals as you like.

Keeping more than one journal (e.g. one per year or similar) can be helpful if your transaction history is extensive.

### Keeping a single journal

If you only ever want to use one journal, you can omit the `journal` argument by declaring an environment variable named `DLEDGER_FILE` that points to your default journal-file:

```shell
export DLEDGER_FILE="~/my.journal"
```

This restricts you to a single journal (though it can still [include](#including-another-journal) other journals), but does simplify the command-line:


```shell
$ dledger report
```

If any `journal` path argument is provided, `DLEDGER_FILE` is ignored.

### Including another journal

Any journal can include other journals. This can be helpful for archival purposes and to keep things neat.

To include another journal you use the `include` directive:

```
# this file serves as an example journal for dledger

include simple.journal

2020/02/13 AAPL
  $ 77
```

The directive can exist anywhere in a journal, but it must be succeeded by whitespace and a valid journal path, and it must be on a single line.

The included records will be ordered chronologically, no matter the location of the directive.

## Transactions

A `dledger` compatible transaction consist (at minimum) of the following elements:

1) A date
2) A ticker
3) A position
4) A cash amount\*

<sup>\*only on dividend transactions</sup>

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

*Note that transactions can be entered in any order. For example, if you prefer, you can have newer transactions at the top, instead of the bottom, as chronology will be established automatically based on record dates.*

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

### Buy/sell transactions

A diligent investor will not only record their dividend transactions, but also their buy and sell transactions.

This will improve [forecasts](#forecasts) inbetween periods of dividend transactions, as payout estimates are essentially based on the calculation `position * dividend` (e.g. if you change your position but don't record it, it won't be noticeable until the next time you receive a dividend). 

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

### Special dividends

A company may occasionally choose to distribute additional cash through what is commonly referred to as a *special dividend*, or *extra dividend*. This is a non-recurring disitribution that is not considered part of the normal dividend schedule and frequency.

To record a special dividend transaction, you record the transaction like you normally would, except you also mark it with an asterisk (`*`).

```
2019/05/20 * ABC
  $ 10
```

This lets `dledger` know that this transaction is a one-time thing and should not be accounted for in forecasts.

### Interim dividends

Recording an interim dividend transaction is similar to [recording a special dividend](#special-dividends), except you mark it with a carat (`^`) instead.

```
2019/05/20 ^ ABC
  10 EUR
```

This indicates that the transaction *is* part of the schedule and *should* be accounted for in forecasts, but the dividend projection should be independent of the regular (final) dividend.

## Locale

For the best results, `dledger` requires a reasonably well-configured environment. This includes an expectation of a configured system locale.

For macOS and Linux, this typically means setting the `LC_ALL` variable to your preferred locale/language. For example, `export LC_ALL=da_DK.UTF-8` will set a danish locale.

The locale defines the rules on how `dledger` reads and understands numbers; specifically decimal/grouping separators (or, comma vs period).

In a case where no locale has been configured (or is incorrectly configured), `dledger` will default to a US locale (en-US), which expects a period to represent the decimal separator, and commas for grouping.

You can run the [`stats`](#stats) command to see which locale `dledger` is using.

## Importing transactions

`dledger` supports importing transactions from Nordnet (a Swedish bank).

```shell
$ dledger convert transactions.csv --type=nordnet
```

This process is not perfect. It is very likely that the transactional data will contain errors such as inconsistent use of decimal separator, incorrect dates or similar. However, `dledger` will do its best to import data correctly and will always inform you instead of making assumptions, letting you fix/correct any invalid or ambiguous data before proceeding.

Though many inconsistencies will automatically be discovered, not all will be. For example, your transaction data might contain shredded/erroneous or duplicate entries. These will still be imported. For the best results, you should always go through the resulting journal to make sure everything looks right.

Additionally, the import process does not take buy/sell transactions into account. Because of this, if you want better forecasts, the next step (optional) for you is to comb through `$ dledger report your.journal` and look for unexpected transactions for positions that should be closed, and then close them (by editing your journal). This is not required as closed positions will naturally fade as time passes.

## Tracking methods

Whenever you enter a record in your journal, you must associate a primary date with the entry. This date is the _entry date_. The date can be anything that makes sense to you, but it is also the date that forecasts will be based on\*.

In general, there are typically two methods to track your dividend income:

1. By payout date

2. By ex-dividend date

Both methods involve recording the cash you receive; the difference being *when* you record it, and which date you associate with each transaction. However, picking one method does not rule out benefits of the other; it's mostly a matter of preference.

<sup>\*You can base forecasts by payout- or ex-dividend dates instead with the `--by-payout-date` and `--by-ex-date` flags</sup>

### By payout date

This is the most straightforward method to track your dividend income. To put it simply: on the day you get the cash in your account, you record the transaction. That's it.

```
2019/02/14 AAPL (100)
  $ 73
```

This method requires the least amount of effort and is recommended if you just want to get an overview of your cashflow and when you can expect to have money in pocket in the future.

Note that even if you choose to go with this method, you can still record the ex-dividend date for good measure.

#### Extending records with additional dates

Here's an example extending the same transaction with a dividend component and an additional date to go with it (e.g. the *ex-dividend date*):

```
2019/02/14 AAPL (100)
  $ 73 @ $ 0.73 [2019/02/08]
```

This can be a useful extension for several reasons, as explained in the following section.

### By ex-dividend date

This method requires a more hands-on approach, but does provide some benefits to the diligent investor, including:

* Tax estimations (e.g. ex-date in 2019, but payout in 2020)
* Strategic buys/sells (controlling returns)

Instead of recording the transaction on the date when cash is in your account, you record a "preliminary" transaction on the day that the stock goes ex-dividend. This is the date where you've *earned* the money. It's yours, you just won't *have it* until the payout date.

For example, here's a preliminary record of a `$ 0.73` dividend from a position in AAPL of 100 shares:

```
2019/02/08 AAPL (100)
  @ $ 0.73
```

Note that the cash amount is left blank to indicate that the transaction has not yet been realized (you don't have the money yet).

Then, on the day of payout, you complete the transaction by finally entering the amount of cash that you received:

```
2019/02/08 AAPL (100)
  $ 73 @ $ 0.73
```

This method is recommended if you want to pursue a more active investing strategy (like dividend capturing or reinvesting dividends into the next upcoming payer for a quicker return).

You can extend the transaction with its payout date by applying an additional date to the cash component.

```
2019/02/08 AAPL (100)
  [2019/02/14] $ 73 @ $ 0.73
```

In this particular example, the payout date only adds value to you, the reader of the journal.

However, if the cash was a different currency than the dividend, adding the date would also improve forecasted payout estimates based on the exchange rate (assuming that the cash was exchanged at payout, rather than at ex-date).

# Reports

The `report` command will show a chronological list of all dividend transactions. This includes both past, pending and [future transactions](#forecasts).

Depending on the fidelity of your records and [tracking method](#tracking-methods) of choice, you have two additional options for the listing; you can order by either the payout (`--by-payout-date`) or ex-dividend date (`--by-ex-date`). These flags have no effect unless you [record these dates explicitly](#extending-records-with-additional-dates).

## Periods

The `--period` flag can be used to drill down and limit transactions within a date interval.

A period is specified through a simple syntax using `:` (colon) as a separator to indicate a starting and ending date.

Several shorthands are supported to ease usage. For example, the period `2019/01/01:2019/02/01` (i.e. entire January 2019) could also be specified as `2019/01`. It is automatically expanded to the previous longform. Similarly, the period shorthand `2019` will expand to `2019/01/01:2020/01/01`.

A period is always inclusive of its starting date, and exclusive of its ending date.

For example, the period `2019/01/01:2019/01/04` will include any transaction dated to either `2019/01/01`, `2019/01/02` or `2019/01/03`, but not `2019/01/04`.

Month and day does not have to be zero-padded. For example, `2019/1` is identical to `2019/01`.

You can use `:` with *only* an ending, or starting, date. In this case, the period will span from the very first transaction (oldest), up to ending date, or, from the starting date to the last (most recent) transaction, respectively. For example, the period `2019:` will include only transactions from 2019 and onwards.

You can format dates using dashes (`-`) if you prefer, e.g. `2019-01-01` is identical to `2019/01/01`.

## Grouping

There are several flags that can be used to control the appearance and grouping of transactions through the `report` command.

### Annually

The `--annual` flag can be used to show you total income over the course of every year passed since the first recorded transaction.

```shell
$ dledger report example/simple.journal --annual
```

```console
               $ 304    2019
~              $ 308  < 2020/11
```

The report includes [forecasts](#forecasts) and preliminary records, as indicated by a `~` (tilde) prefix. In general, whenever you see a `~` to the left of an amount, this indicates that the amount is an *estimate*.

Taking a look at the last row, we might also notice that the date stands out from the others in two ways: 1) it is set in the future, and 2) it has a `<` next to it. Here, the `<` is to be read as a backwards facing arrow, indicating "by/before this date". So with this knowledge, the row now reads: "approximately $308 received by November 2020".

If a journal contains income of multiple currencies, the report is split in a section for each currency (unless `--as-currency` is specified, see [consolidating income reports](#consolidating-income-reports)).

### Monthly

Similar to [`--annual`](#annually), the `--monthly` flag groups income received by month.

```shell
$ dledger report example/simple.journal --monthly
```

```console
                $ 73    2019/02
                $ 77    2019/05
                $ 77    2019/08
                $ 77    2019/11
~               $ 77    2020/02
~               $ 77    2020/05
~               $ 77    2020/08
~               $ 77    2020/11
```

### Quarterly

Similar to [`--annual`](#annually), the `--quarterly` flag groups income received by quarter.

```shell
$ dledger report example/simple.journal --quarterly
```

```console
                $ 73    2019/Q1
                $ 77    2019/Q2
                $ 77    2019/Q3
                $ 77    2019/Q4
~               $ 77    2020/Q1
~               $ 77    2020/Q2
~               $ 77    2020/Q3
~               $ 77    2020/Q4
```

### Trailing

The `--trailing` flag can be used to show you the total income rolling over trailing 12-month periods. This total is listed for every month passed since the very first transaction, through today.

This is a popular metric among dividend growth investors, as it can serve as a benchmark in performance of cashflow.


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

The last row stands out, as it does not correspond to a trailing 12-month period, but instead represent the forecasted and future 12-month period, starting from today (inclusive), and is effectively the sum of all future\* transactions.

<sup>\*Not including forecasted transactions dated prior to today.</sup>

If you're only interested in the last row, the result is effectively identical to applying [`--sum`](#sum) on the future period report:

```shell
$ dledger report example/simply.journal --sum --period=today:
```

```console
~              $ 308
```

### Weight

The `--weight` flag can be used to weigh your income sources by ticker.

This can be useful in revealing companies that you might be overly dependent on. For example, in this overly simplified example, AAPL is 100% of our portfolio, and should they suffer a dividend cut, it would have a significant impact on our future income.

```shell
$ dledger report example/simple.journal --weight --period=2019
```

*Note the use of `--period` to only weigh income from 2019.*

```console
               $ 304    100.00%    AAPL
```

Similarly, it can often be useful to weigh forecasted income instead of past income (as you buy/sell and change your positions, your future income will also change):

```shell
$ dledger report example/simple.journal --weight --period=tomorrow:
```

```console
~              $ 308    100.00%    AAPL
```

*Note that the [balance](#balance) command can preferably be used instead for this particular case.*

### Sum

The `--sum` flag can be used to calculate the total (sum) of all transactions in a report.

```shell
$ dledger report example/simple.journal --sum
```

Since reports by default include forecasted transactions, the sum also counts these:

```console
~              $ 608
```

You can apply `--without-forecast` to sum without forecasted transactions:

```shell
$ dledger report example/simple.journal --sum --without-forecast
```

```console
               $ 304
```

Similarly, you can reduce the number of transactions further by applying either `--period` or `--by-ticker`.

## Detailed transactions

The `--by-ticker` flag can be used to filter a report to only show transactions with a specific ticker. It also adds more details to each transaction (dividend and position).

```shell
$ dledger report example/simple.journal --by-ticker=AAPL
```

```console
                $ 73    2019/02/14 AAPL                  (100)           $ 0.73
                $ 77    2019/05/16 AAPL                  (100)           $ 0.77
                $ 77    2019/08/15 AAPL                  (100)           $ 0.77
                $ 77    2019/11/14 AAPL                  (100)           $ 0.77
~               $ 77 <~ 2020/02/15 AAPL                  (100)           $ 0.77
~               $ 77 <~ 2020/05/31 AAPL                  (100)           $ 0.77
~               $ 77 <~ 2020/08/15 AAPL                  (100)           $ 0.77
~               $ 77 <~ 2020/11/15 AAPL                  (100)           $ 0.77
```

You can provide partial ticker names if there's no ambiguity among other tickers. For example, the above report could also be run as:

```shell
$ dledger report example/simple.journal --by-ticker=AAP
```

Ticker names are case-sensitive; i.e. `--by-ticker=Aapl` does not produce the same report as above.

Ticker names can contain whitespace.

For example, to filter by ticker "NOVO B", you must wrap it in quotes:

```shell
$ dledger report ~/.journal --by-ticker="NOVO B"
```

## Forecasts

In addition to listing all past or pending transactions, reports also include forecasts (or projections).

These forecasts can provide you with an overview of future cashflow, based on past cashflow, and are always projected conservatively, aiming at keeping future dividends in line with recent distributions.

You can set `--without-forecast` to exclude forecasted transactions from a report entirely.

## Exchange rates

If you track any income in a currency other than the native currency for the distributing company, then an exchange rate will be determined and automatically applied to all forecasted transactions.

To determine and apply an exchange rate, a dividend must be recorded.

The exchange rate is always based on the latest recorded transaction and is *not* guaranteed to be current (i.e. `dledger` does not fetch external data).

### Consolidating income reports

The `--as-currency` flag can be used to report all income in a specific currency. This can be particularly useful when you track and receive income in currency other than your domestic currency, but want to consolidate all reports into a single one.

This works by estimating how much the amount of cash received previously would be worth today, using the most recently known exchange rate; i.e. it does not determine what it was worth at the time of the transaction, but rather what it would be worth if exchanged today.

Income is not converted if an exchange rate is not available for a given currency pairing.

## Common/useful reports

### Report only future transactions

This can be achieved by using the [`--period`](#periods) flag. Simply specify a period that only include future dates:

```shell
$ dledger report ~/.journal --period=tomorrow:
```

In this example, the period will stretch from tomorrow (inclusive) through the last transaction in the report.

*Note that this also includes pending transactions; i.e. transactions entered into the journal, but have yet to be realized.*

### Report future income weights

Building on the [previous tip](#report-only-future-transactions), you can apply a future period to weigh your future income sources:

```shell
$ dledger report ~/.journal --period=tomorrow: --weight
```

*Note that the [balance](#balance) command is typically more useful for this particular case.*

### Report how much you earned/received

> This tip only applies if your journal tracks ex-date information

Let's say you were wondering how much you _earned_ in a given period, compared to how much you _collected_ in cash in the same period.

You can figure this out by running two `--sum` reports (in this case, for the month of January 2020):

```shell
$ dledger report ~/.journal --period=2020/1 --sum --by-ex-date
```

The result of this report is how much you earned, but have yet to receive in a cash payout.

Then, you run the same report, but this time applying the `--by-payout-date` flag.

```shell
$ dledger report ~/.journal --period=2020/1 --sum --by-payout-date
```

Now you can compare the two results.

Note that you can omit either `--by-ex-date` or `--by-payout-date` if your primary transaction date corresponds to either (e.g. if your primary date corresponds to the ex-date, then you can omit `--by-ex-date`).

### Next expected payouts

> This tip only applies on macOS/Linux platforms

Sometimes it is nice to know when the next 5 or 10 expected payouts are due. This is not a built-in feature of `dledger`, but can still be achieved using existing system tools.

For this exact purpose, both macOS and Linux comes with a handy tool called `head`. This tool will read lines from the 'head' (or 'top') of an input source, until it reaches the end (or a specified limit, through the `-n` flag).

We can use this tool to list the next 5 payouts by piping a forecast report into `head`, like so:

```shell
$ dledger report ~/.journal --period=tomorrow: | head -n 5
```

### Most recent payouts

Similarly, the tool `tail` can be used for the same purpose, but instead of reading from the top, it reads from the bottom. This can be used to list the 5 most recent payouts:

```shell
dledger report ~/.journal --without-forecast | tail -n 5
```

*Note the use of `--without-forecast` to exclude any forecasted transactions.*

### Archiving/condensing old journals

The `print` command can be used to easily condense an entire journal.

This can reduce the journal's filesize and linecount drastically, but at the expense of being more difficult to read.

*Warning: this will also __remove all comments__!*

```shell
$ dledger print old.journal --condensed > archived.journal
```

This also ensures a consistent formatting and removes any redundant transactions.

# Balance

The `balance` command provides an overview of your projected future income over the next full 12 months, per ticker, along with an indication of drift from ideal weightings.

The "ideal" weight is considered to be the percentage split equally among every holding; i.e. if you have a portfolio of 100 different companies, then the ideal income weight for each ticker is 1%.

This is a conservative approach that is grounded in the belief that you cannot predict winners vs. losers, and thus should spread your risk equally. This approach should only be viewed as a guideline; it is not advice, and it is subject to personal consideration based on own beliefs and convictions.

By default, drift is indicated by the percentage difference/deviance from the ideal weight. You can show drift by amount (cash), or position (shares), by setting either `--by-amount`, or `--by-position`, respectively.

# Stats

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

# FAQ

## I have a position in company ABC in multiple portfolios; how do I track this?

**This is not supported.** You can choose to either keep a separate journal per portfolio, or keep one journal and consolidate the transactions.

For example, let's say you have two portfolios, each with a respective position of 100 and 50 shares in the fictional company ABC.

In this scenario, when a dividend hits, you would enter the following transactions:

```
2019/03/16 ABC (100)  # portfolio A
  $ 1

2019/03/16 ABC (50)   # portfolio B
  $ 0.5
```

However, these transactions are problematic in regard to forecasting; do you have a current position of 50, or a 100?

You can resolve this ambiguity by consolidating these transactions into one:

```
2019/03/16 ABC (150)
  $ 2
```

This explicitly states that your current, and total position (across all portfolios), is 150 shares.

*Note that even while keeping separate journals, the ambiguity will remain unless you also run separate reports.*

## Company ABC announced they will eliminate their dividend; how do I avoid including it in forecasts?

Unfortunately, this does tend to happen every now and then, and seeing forecasts that you know to be incorrect is frustrating and will skew the outlook of your future situation.

There are two solutions to this problem:

1) **Wait it out.** Forecasted distributions will disappear once a grace period has passed and no transactions have been recorded. However, for high frequency distributions (e.g. monthly) this can take up to a full year.
2) **Mark the position as closed.** This is typically preferable.

For example:

```
2018/12/16 ABC
  $ 1
2019/03/16 ABC
  $ 1

2019/06/01 ABC (0)  # dividend was eliminated indefinitely
```

It is good practice for your future self to leave a note as to why this line exists.

If the distribution resumes, you can simply remove this line. If you prefer to leave it for posterity, you must "open" the position again when recording the next distribution.

## Company ABC completed a split; what should I do?

A stock split is a purely technical event, and generally you do not have to do anything other than record your transactions as usual.

However, what _does_ change, is the number of shares you hold, and, typically, the dividend per share. So, depending on what you track, the next transaction you record should, at least, include the new number of shares held.

Here's an example when AAPL completed a 4-for-1 split during 2020:

```
2020/07/01 AAPL (10)    # initial purchase of 10 shares

2020/08/14 AAPL         # first dividend distribution
  [2020/08/13] $ 8.2
@ [2020/08/07] $ 0.82

2020/11/13 AAPL (40)    # second dividend distribution after a 4-for-1 split; position increased from 10 to 40
  [2020/11/12] $ 8.2    # note same exact payout as previous distribution
@ [2020/11/06] $ 0.205  # however, dividend has been adjusted from $0.82 previous, to $0.205 current
```

*Note that you might not want to record a split until the following dividend has been declared. If you do, you must estimate the expected dividend yourself to avoid it simply repeating past distributions without adjustment.*
