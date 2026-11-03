@regression @integration
Feature: Integration between Trading, Settlement and T2S
  As a post-trade team
  I want each trade to reach Settlement exactly once and to be settled at T2S
  So that both systems always reconcile, even when something fails

  Acceptance criteria:
    AC-I01  Each trade publishes a TradeExecuted event that follows contract v1
    AC-I02  An event delivered twice does not create a second instruction (idempotency)
    AC-I03  A message that breaks the contract goes to the dead letter queue and creates no instruction
    AC-I04  If Settlement is unavailable, trading continues and the instructions arrive when it recovers
    AC-I05  An instruction rejected by T2S becomes FAILED with the reason and is recycled at the next end of day
    AC-I06  If T2S is unavailable, nothing is settled and the instructions settle when it is back

  Background:
    Given a clean market with business date "2026-11-02"

  @AC-I01 @critical @smoke
  Scenario: The trade reaches Settlement with the same data
    When a trade of 100 "EDP" at 4.50 EUR is executed
    Then the published event follows the TradeExecuted v1 contract
    And a settlement instruction is created for "2026-11-04" with status "PENDING"
    And Trading and Settlement reconcile with no differences

  @AC-I02 @critical
  Scenario: A duplicate event does not create a second instruction
    Given a trade of 100 "EDP" at 4.50 EUR is executed
    When the trade event is delivered again
    Then the trade still has a single settlement instruction

  @AC-I03 @high
  Scenario: A message outside the contract goes to the dead letter queue
    When a message with quantity 0 and no event identifier is published
    Then the message appears in the Settlement rejected events
    And there are no settlement instructions

  @AC-I04 @critical
  Scenario: Settlement unavailable: trading continues and instructions arrive later
    Given Settlement has stopped consuming events
    When a trade of 100 "GALP" at 15.20 EUR is executed without waiting for Settlement
    Then the reconciliation shows the trade missing in Settlement
    When Settlement starts consuming events again
    Then Trading and Settlement reconcile with no differences

  @AC-I05 @high
  Scenario: Rejection by T2S and recycling at the next end of day
    Given a trade of 100 "EDP" at 4.50 EUR is executed
    And T2S rejects the instructions for "EDP"
    When the end of day is run 3 times
    Then the instruction has status "FAILED"
    When T2S is back to normal
    And the end of day is run
    Then the instruction is settled on "2026-11-05"

  @AC-I06 @high
  Scenario: T2S unavailable at end of day
    Given a trade of 100 "NOS" at 3.80 EUR is executed
    And T2S is unavailable
    When the end of day is run 3 times
    Then the instruction has status "FAILED"
    When T2S is back to normal
    And the end of day is run
    Then the instruction is settled on "2026-11-05"
