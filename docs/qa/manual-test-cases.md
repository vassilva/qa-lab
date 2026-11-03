# Manual test cases · QA Lab

They complement the automated tests where a human eye adds value: the web page, the user
experience, reading logs and reports, and checks in UAT before the go/no-go.
Run on the mini exchange page (QA `localhost:8000` or UAT `localhost:9000`) and in the Linux terminal.

| ID | Title | Acceptance criterion | Automated? |
| --- | --- | --- | --- |
| TC-M01 | Trade shows in the book, in trades and in settlement | AC-N01, AC-L01 | Partly (BDD covers the API, not the page) |
| TC-M02 | Partial fill visible in the order book | AC-N02 | Partly |
| TC-M03 | Clear rejection messages for the user | AC-V01, AC-V02 | Partly |
| TC-M04 | Cancel an order from the book | AC-V03 | No |
| TC-M05 | End of day on the page and CSV report on the server | AC-L03 | Partly (the CSV is not checked) |
| TC-M06 | Hold and release from the page | AC-L04 | Partly |
| TC-M07 | Business date: refuse weekend and holiday | AC-L06, AC-L02 | Partly |
| TC-M08 | Cross-system reconciliation and integrity checks | AC-L05 | Yes (BDD) |
| TC-M09 | Same environment badge and version in QA and UAT | OBJ-4 | Partly (smoke) |
| TC-M10 | Component-tagged logs let you follow an order across the three services | Defect support | No |

---

### TC-M01 · Trade shows in the book, in trades and in settlement
**Preconditions:** QA environment, **Reset environment** clicked, symbol EDP selected.

1. Quantity 100, price 4.50 → **Sell**.
2. Quantity 100, price 4.55 → **Buy**.

**Expected:** the sell order leaves the book; **Trades** shows 1 trade of 100 at **4.50** with the business date;
**Settlement instructions** shows a `PENDING` instruction with intended settlement at T+2 business days; both orders are `FILLED`.

### TC-M02 · Partial fill visible in the order book
1. Sell 100 EDP at 4.50. 2. Buy 40 EDP at 4.50.

**Expected:** the same order stays on the ask side with **60**; the sell order is `PARTIALLY_FILLED` with 60 remaining; the trade is for 40.

### TC-M03 · Clear rejection messages
1. Buy 10,001 EDP at 4.50. 2. Buy 100 EDP at 4.505. 3. Buy 100 EDP at 4.96.

**Expected:** each order shows `REJECTED` in the orders table with its reason (`Invalid quantity`, `Price not on tick size`,
`Price outside price bands`); "Last API response" shows HTTP 422; none enters the book.

### TC-M04 · Cancel an order from the book
1. Buy 100 EDP at 4.40. 2. On the bid side, click the order's ✕.

**Expected:** the order leaves the book and becomes `CANCELLED`; the API responds HTTP 200. Repeating the cancel on an already filled order (via the API)
returns HTTP 409.

### TC-M05 · End of day and CSV report
1. Execute a trade (TC-M01). 2. Click **Run end of day (EOD)** three times (starting on a Monday).
3. In the Linux terminal: `ls /var/log/qa-lab/eod/` and `cat /var/log/qa-lab/eod/settlement_<date>.csv`.

**Expected:** the instruction only becomes `SETTLED` at the end of day of its intended date; the business date always moves to the next business day;
there is one CSV per EOD, with the instruction and the right status.

### TC-M06 · Hold and release
1. Execute a trade. 2. On the instruction, click **Hold**. 3. Run end of day until the intended date has passed.
4. Click **Release** and run one more end of day.

**Expected:** while held, the instruction is not settled (the log records `NOT settled on its intended date`); after the release, it settles at the next EOD.

### TC-M07 · Invalid business date
1. Set the business date to a Saturday. 2. Set it to 2026-12-25.

**Expected:** both refused (HTTP 400, with a message that explains why); the business date does not change.

### TC-M08 · Cross-system reconciliation and integrity checks
1. Execute several trades (including partial fills). 2. Click **Reconcile systems**.
3. In the SQL console, run the preset **[Trading] Executed qty vs. order (integrity)**.

**Expected:** the reconciliation shows `"ok": true` with no missing, orphan or mismatched trades; the preset returns 0 rows.

### TC-M09 · Same environment, same version
1. Open QA and UAT side by side after an approved pipeline.

**Expected:** **QA** (blue) and **UAT** (yellow) badges with **the same version**, matching the build name in Jenkins.

### TC-M10 · Follow an order through the logs
1. Run TC-M02. 2. In the terminal: `grep -h -e O00001 -e T00001 -e S00001 /var/log/qa-lab/*.log | sort`.

**Expected:** you can follow the order through the gateway (`[OEG]`), the engine (`[ME]`), the outbox (`[OUTBOX]`) and settlement (`[SETTLEMENT]`), with consistent times and quantities.

---

## Exploratory session (charter)

**Mission:** explore unusual order combinations in the Matching Engine for 30 minutes, to find unexpected behaviour
in price, quantities or settlement.

**Ideas:** several orders at the same price with alternating sides; market orders against a book with several price levels;
cancelling a partially filled order; quantities and prices at the limits; end of day with no trades; switching symbol halfway;
T2S in `reject_symbol` mode for one symbol while others settle.

**Notes:** time-stamped notes of what was done, what was observed, and questions or defects. Defects → `docs/defects/`.

## Execution log

| Version | Environment | Date | Run by | TC-M01 | M02 | M03 | M04 | M05 | M06 | M07 | M08 | M09 | M10 | Defects |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.6.0-… | QA | | | | | | | | | | | | | |
| 0.6.0-… | QA (challenge mode) | | | | | | | | | | | | | |

Legend: ✓ passed · ✗ failed (give the defect) · — not run.
