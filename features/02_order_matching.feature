@regression @matching
Feature: Order matching in the Matching Engine
  As a market participant
  I want my orders to be matched by price-time priority
  So that executions are fair and predictable

  Acceptance criteria:
    AC-N01  The trade is executed at the price of the order that was already resting in the book
    AC-N02  On a partial fill, the unfilled quantity stays in the book
    AC-N03  At the same price, the order that arrived first executes first
    AC-N04  An order that does not cross stays in the book and creates no trade
    AC-N05  A market order without a counterparty is cancelled and does not rest in the book

  Background:
    Given a clean market with business date "2026-11-02"

  @AC-N01 @critical @smoke
  Scenario: A crossing buy executes at the price of the resting sell
    Given an existing order "S1" to sell 100 "EDP" at 4.50 EUR
    When order "B1" to buy 100 "EDP" at 4.55 EUR is submitted
    Then order "B1" has status "FILLED"
    And there is 1 trade of 100 shares at 4.50 EUR
    And the ask side of "EDP" is empty

  @AC-N02 @critical
  Scenario: A partial fill leaves the remainder in the book
    Given an existing order "S1" to sell 100 "EDP" at 4.50 EUR
    When order "B1" to buy 40 "EDP" at 4.50 EUR is submitted
    Then order "B1" has status "FILLED"
    And order "S1" has status "PARTIALLY_FILLED" with 60 remaining

  @AC-N03 @critical
  Scenario: At the same price, the first to arrive executes first
    Given an existing order "B1" to buy 100 "EDP" at 4.48 EUR
    And an existing order "B2" to buy 100 "EDP" at 4.48 EUR
    When order "S1" to sell 100 "EDP" at 4.48 EUR is submitted
    Then order "B1" has status "FILLED"
    And order "B2" has status "NEW"

  @AC-N03 @critical
  Scenario: Best price has priority over arrival time
    Given an existing order "S1" to sell 100 "EDP" at 4.52 EUR
    And an existing order "S2" to sell 100 "EDP" at 4.51 EUR
    When order "B1" to buy 100 "EDP" at 4.55 EUR is submitted
    Then order "S2" has status "FILLED"
    And order "S1" has status "NEW"
    And there is 1 trade of 100 shares at 4.51 EUR

  @AC-N04 @high
  Scenario: An order that does not cross stays in the book
    Given an existing order "S1" to sell 100 "EDP" at 4.52 EUR
    When order "B1" to buy 100 "EDP" at 4.50 EUR is submitted
    Then order "B1" has status "NEW"
    And there are no trades

  @AC-N05 @high
  Scenario: A market order without a counterparty is cancelled
    When order "B1" to buy 100 "EDP" at market is submitted
    Then order "B1" has status "CANCELLED"
    And the bid side of "EDP" is empty
