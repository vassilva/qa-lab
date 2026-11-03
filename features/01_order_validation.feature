@regression @gateway
Feature: Order validation in the Order Entry Gateway
  As an exchange
  I want to reject invalid orders before they reach the order book
  So that the market is protected from participants' mistakes

  Acceptance criteria:
    AC-V01  The quantity must be between 1 and 10,000 (inclusive)
    AC-V02  The price must be positive, a multiple of 0.01 and within ±10% of the reference price (limits accepted)
    AC-V03  An order that is already fully filled cannot be cancelled
    AC-V04  Only known symbols are accepted

  Background:
    Given a clean market with business date "2026-11-02"

  @AC-V01 @high @boundary
  Scenario Outline: Quantity limits
    When order "B1" to buy <quantity> "EDP" at 4.50 EUR is submitted
    Then order "B1" has status "<status>"

    Examples:
      | quantity | status   |
      | 0        | REJECTED |
      | 1        | NEW      |
      | 10000    | NEW      |
      | 10001    | REJECTED |

  @AC-V02 @high
  Scenario Outline: Rejection for an invalid price
    When order "B1" to buy 100 "EDP" at <price> EUR is submitted
    Then order "B1" is rejected with reason "<reason>"

    Examples:
      | price | reason                     |
      | 4.505 | Price not on tick size     |
      | 4.96  | Price outside price bands  |
      | 4.04  | Price outside price bands  |
      | 0     | Invalid price              |

  @AC-V02 @high @boundary
  Scenario Outline: Price band limits are accepted
    When order "B1" to buy 100 "EDP" at <price> EUR is submitted
    Then order "B1" has status "NEW"

    Examples:
      | price |
      | 4.05  |
      | 4.95  |

  @AC-V03 @medium
  Scenario: An order that is already filled cannot be cancelled
    Given an existing order "S1" to sell 100 "EDP" at 4.50 EUR
    And an existing order "B1" to buy 100 "EDP" at 4.50 EUR
    When the participant tries to cancel order "S1"
    Then the cancellation is refused

  @AC-V04 @medium
  Scenario: Unknown symbol is rejected
    When order "B1" to buy 100 "XPTO" at 4.50 EUR is submitted
    Then order "B1" is rejected with reason "Unknown symbol"
