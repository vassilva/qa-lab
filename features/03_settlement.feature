@regression @settlement
Feature: T+2 settlement of trades
  As a settlement system
  I want to settle each trade two business days after the trade date
  So that securities and cash are exchanged on the right date, following the TARGET2 calendar

  Acceptance criteria:
    AC-L01  Each trade creates a PENDING instruction for T+2 business days (weekends do not count)
    AC-L02  TARGET2 closing days (Christmas, Easter, 1 January, 1 May, 26 December) do not count
    AC-L03  The end of day (EOD) only settles instructions that reached their intended settlement date
    AC-L04  A held instruction is not settled until it is released
    AC-L05  Every trade has a settlement instruction (cross-system reconciliation)
    AC-L06  The business date can only be a business day

  @AC-L01 @AC-L02 @critical
  Scenario Outline: T+2 settlement date calculation
    Given a clean market with business date "<trade date>"
    When a trade of 100 "EDP" at 4.50 EUR is executed
    Then a settlement instruction is created for "<settlement date>" with status "PENDING"

    Examples: Normal business days and weekends
      | trade date | settlement date | note                       |
      | 2026-11-02 | 2026-11-04      | Monday → Wednesday         |
      | 2026-11-05 | 2026-11-09      | Thursday → Monday          |
      | 2026-11-06 | 2026-11-10      | Friday → Tuesday           |

    Examples: TARGET2 holidays
      | trade date | settlement date | note                       |
      | 2026-12-23 | 2026-12-28      | Christmas and 26 December  |
      | 2027-03-25 | 2027-03-31      | Good Friday and Easter     |

  @AC-L03 @critical @smoke
  Scenario: The instruction only settles at the end of day of its intended date
    Given a clean market with business date "2026-11-06"
    And a trade of 100 "EDP" at 4.50 EUR is executed
    When the end of day is run
    Then the instruction has status "PENDING"
    And the business date becomes "2026-11-09"
    When the end of day is run
    Then the instruction has status "PENDING"
    When the end of day is run
    Then the instruction is settled on "2026-11-10"

  @AC-L04 @high
  Scenario: A held instruction is not settled until it is released
    Given a clean market with business date "2026-11-02"
    And a trade of 100 "EDP" at 4.50 EUR is executed
    When the instruction is put on hold
    And the end of day is run 3 times
    Then the instruction has status "ON_HOLD"
    When the instruction is released
    And the end of day is run
    Then the instruction is settled on "2026-11-05"

  @AC-L05 @critical
  Scenario: Reconciliation: every trade has a settlement instruction
    Given a clean market with business date "2026-11-02"
    And an existing order "S1" to sell 300 "GALP" at 15.20 EUR
    And an existing order "B1" to buy 100 "GALP" at 15.20 EUR
    And an existing order "B2" to buy 200 "GALP" at 15.25 EUR
    Then there are 2 trades
    And every trade has a settlement instruction
    And the executed quantity of each order matches the trades

  @AC-L06 @medium
  Scenario: The business date cannot be a weekend
    Given a clean market with business date "2026-11-06"
    When someone tries to set the business date to "2026-11-07"
    Then the request is refused with status 400
    And the business date is still "2026-11-06"
