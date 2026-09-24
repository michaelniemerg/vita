---
doc_id: pricing-engine-policy-valuation-testing
title: Testing and verification plan for the term policy death-benefit valuation calculator
module: pricing-engine
spec_id: pricing-engine-policy-valuation
spec_version: 0.2
status: draft
version: 0.1
owner_persona: actuary
reviewers: [actuary, architecture, data-engineer, product-owner]
created: 2026-09-23
last_updated: 2026-09-23
---

# Testing and verification plan: term policy death-benefit valuation calculator

## 1. Purpose

This document defines every check that must pass before the calculator specified in `modules/pricing-engine/specs/pricing engine module - spec.md` (the spec, v0.2) is considered correct. It is the spec's acceptance criteria (spec Section 8).

It covers:

- the test data, golden values, and numeric tolerance;
- every automated test, grouped by suite, with an ID that the traceability matrix (Section 10) maps back to the spec's requirements;
- the regression procedure that proves each change from the old code fixes what it claims to;
- the manual UAT check against the Excel workbook;
- the LLM-as-judge review and its rubric;
- the human sign-off gates and the evidence each one needs.

If this document and the spec disagree, the spec wins, and this document must be corrected.

## 2. Levels of checking

| Level | What it proves | Who / what runs it | Blocks |
|---|---|---|---|
| Unit tests | Each function does exactly what the spec says, including every validation message | pytest | Merge |
| Contract tests | Inputs, outputs, CSV rows, and run logs match the JSON Schemas in `contracts/` | pytest + jsonschema | Merge |
| Regression tests (golden) | The numbers for the sample policies have not changed | pytest | Merge |
| Regression tests (changes D1–D9) | Each change from the old code fixes the old behavior | pytest, run once against the old code and once against the new | Merge |
| Acceptance tests | The system behaves as a user sees it: `run()` and the CLI, end to end | pytest | Merge |
| Coverage | At least 90% of lines in `code/` are exercised | pytest-cov | Merge |
| Manual UAT | The Excel workbook independently reproduces the Python numbers | Actuary reviewer | Human sign-off |
| LLM-as-judge | The implementation matches the spec and nothing extra was added | Claude, using the rubric in Section 8 | Human sign-off |
| Human sign-off | A human has reviewed all of the above | Human actuary + code reviewer | Push and deploy |

A failure at any level blocks everything below it. No level substitutes for human sign-off (AGENTS.md hard rule: this spec touches core model logic).

## 3. Test environment

```yaml
python: "3.12"            # golden values were produced on CPython 3.12.6, Windows x64
working_directory: modules/pricing-engine/
test_dependencies:        # pinned exactly in requirements-dev.txt
  pytest: "8.x"
  pytest-cov: "latest compatible with the pinned pytest"
  jsonschema: "4.x"
install: pip install -r requirements-dev.txt
run_all: python -m pytest tests --cov=./code --cov-report=term-missing --cov-fail-under=90
```

`tests/conftest.py` adds `modules/pricing-engine/code/` to `sys.path` so tests can import `policy_valuation`, `run_from_csv`, and `run_log` the same way the scripts import each other. It also provides these pytest fixtures:

```yaml
fixtures_dir:         path to tests/fixtures/
durational_csv:       path to tests/fixtures/durational_assumptions.csv
policy_csv:           path to tests/fixtures/policy_assumptions.csv
valid_inputs:         dict of the baseline valid value_policy inputs (Section 4.4); a fresh copy per test
fixed_now:            datetime(2026, 9, 23, 14, 5, 9, tzinfo=timezone.utc)
no_git:               monkeypatches subprocess.run in run_log to raise FileNotFoundError
```

Tests that need any other CSV content write it to pytest's `tmp_path`. No test reads or writes outside `tmp_path` and `tests/fixtures/`. No test uses the network, production data, or carrier data.

### Test file layout

```
modules/pricing-engine/tests/
├── conftest.py
├── fixtures/
│   ├── durational_assumptions.csv     # byte-identical to input/durational_assumptions.csv
│   └── policy_assumptions.csv         # byte-identical to input/policy_assumptions.csv
├── test_policy_valuation.py           # CALC-*, VAL-*
├── test_run_from_csv.py               # LOAD-*, RUN-*
├── test_run_log.py                    # LOG-*
├── test_cli.py                        # CLI-*
├── test_contracts.py                  # CON-*
├── test_regression_golden.py          # GOLD-*
└── test_regression_changes.py         # REG-*
```

## 4. Test data

### 4.1 Sample data

`tests/fixtures/durational_assumptions.csv`:

```
duration,qx,persistency_rate,interest_rate
1,0.01,0.95,0.05
2,0.02,0.95,0.05
3,0.03,0.95,0.05
4,0.035,0.94,0.045
5,0.04,0.94,0.045
```

`tests/fixtures/policy_assumptions.csv`:

```
policy_id,term,propensity_to_buy,face_amount
POL-001,3,0.5,100000
POL-002,5,0.35,250000
```

Both files end with a single newline and contain no byte-order mark.

### 4.2 Numeric tolerance

Unless a test says **exactly**, a number matches when `pytest.approx(expected, rel=1e-12, abs=1e-12)` holds. "Exactly" means `==`.

### 4.3 Golden values

Produced by the old code (commit `43b3751`), reproduced independently by `uat/policy_valuation_uat.xlsx`, and recomputed on 2026-09-23 on CPython 3.12.6 with identical results. None of the spec v0.2 changes affect these values.

```yaml
POL-001:
  value_before_propensity: 4927.6462585034005
  value: 2463.8231292517003
  schedule:
    - {period: 1, in_force_prob: 1.0,                expected_death_benefit: 1000.0,             discount_factor: 0.9523809523809523, present_value: 952.3809523809523}
    - {period: 2, in_force_prob: 0.9405,             expected_death_benefit: 1881.0,             discount_factor: 0.9070294784580498, present_value: 1706.1224489795918}
    - {period: 3, in_force_prob: 0.8756054999999999, expected_death_benefit: 2626.8164999999995, discount_factor: 0.863837598531476,  present_value: 2269.1428571428564}
POL-002:
  value_before_propensity: 23945.01495361781
  value: 8380.755233766233
  schedule:
    - {period: 1, in_force_prob: 1.0,                expected_death_benefit: 2500.0,             discount_factor: 0.9523809523809523, present_value: 2380.9523809523807}
    - {period: 2, in_force_prob: 0.9405,             expected_death_benefit: 4702.5,             discount_factor: 0.9070294784580498, present_value: 4265.306122448979}
    - {period: 3, in_force_prob: 0.8756054999999999, expected_death_benefit: 6567.041249999999,  discount_factor: 0.863837598531476,  present_value: 5672.857142857142}
    - {period: 4, in_force_prob: 0.80687046825,      expected_death_benefit: 7060.116597187501,  discount_factor: 0.8266388502693551, present_value: 5836.166666666668}
    - {period: 5, in_force_prob: 0.7319122017495749, expected_death_benefit: 7319.12201749575,   discount_factor: 0.7910419619802442, present_value: 5789.732640692641}
```

Each schedule entry's `qx`, `lapse`, and `interest_rate` must equal the sample data for that duration, with `lapse = 1.0 - persistency_rate` computed in Python.

The golden values may be changed only by a spec change that is approved by a human, and the change must be recorded in this document's version history.

### 4.4 Baseline valid inputs for validation tests

```python
valid_inputs = dict(qx=[0.1, 0.2], lapse=[0.05, 0.05], propensity_to_buy=0.5,
                    term=2, interest_rate=0.05, benefit_amount=1000.0)
```

Each VAL test starts from a fresh copy and changes only what the test states.

## 5. Automated tests

Scenarios use Gherkin. Each scenario is one pytest test (a Scenario Outline is one test with `pytest.mark.parametrize`). The test function's docstring starts with the scenario ID, for example `"""CALC-04: ..."""`, so the traceability matrix can be checked by searching the code.

"Raises with message M" means the stated exception is raised and M appears as one complete `- ` line (for `PolicyValuationError`) or as a substring (for `CSVLoadError`) of its message.

### 5.1 Calculation (`test_policy_valuation.py`)

```gherkin
Feature: value_policy calculation

  Scenario: CALC-01 Single year, no discounting
    Given qx [0.1], lapse [0.0], propensity 1.0, term 1, interest_rate 0.0, benefit_amount 1000.0
    When value_policy is called
    Then value is 100.0 and value_before_propensity is 100.0

  Scenario: CALC-02 Lapse reduces the in-force probability for the next year only
    Given qx [0.1, 0.1], lapse [0.5, 0.0], propensity 1.0, term 2, interest_rate 0.0, benefit_amount 1.0
    When value_policy is called
    Then schedule[0].expected_death_benefit is 0.1
    And schedule[1].in_force_prob is 0.45
    And value_before_propensity is 0.145

  Scenario: CALC-03 A death in year t is discounted for t full years
    Given qx [0.5], lapse [0.0], propensity 1.0, term 1, interest_rate 0.1, benefit_amount 110.0
    When value_policy is called
    Then schedule[0].discount_factor is 1/1.1
    And value is 50.0

  Scenario: CALC-04 Year-by-year interest rates compound
    Given qx [0.1, 0.2], lapse [0.0, 0.0], propensity 0.5, term 2, interest_rate [0.0, 0.2], benefit_amount 1000.0
    When value_policy is called
    Then schedule[0].discount_factor is exactly 1.0
    And schedule[0].present_value is 100.0
    And schedule[1].discount_factor is 1/1.2
    And schedule[1].present_value is 150.0
    And value_before_propensity is 250.0
    And value is 125.0

  Scenario: CALC-05 A scalar rate equals the same rate repeated
    Given the POL-002 inputs with interest_rate 0.05 as a scalar
    And the POL-002 inputs with interest_rate [0.05, 0.05, 0.05, 0.05, 0.05]
    When value_policy is called on each
    Then the two results are exactly equal, including every schedule field

  Scenario: CALC-06 Defaults mean no discounting and a unit benefit
    Given qx [0.1, 0.2], lapse [0.0, 0.0], propensity 1.0, term 2, and no interest_rate or benefit_amount
    When value_policy is called
    Then every schedule discount_factor is exactly 1.0
    And value_before_propensity is 0.1 + 0.9 * 0.2

  Scenario: CALC-07 Zero propensity
    Given the POL-001 inputs with propensity 0.0
    When value_policy is called
    Then value is exactly 0.0
    And value_before_propensity matches the POL-001 golden value

  Scenario: CALC-08 Zero mortality
    Given qx [0.0] * 5, lapse [0.05] * 5, propensity 0.5, term 5, interest_rate 0.05, benefit_amount 1000.0
    When value_policy is called
    Then value and value_before_propensity are exactly 0.0

  Scenario: CALC-09 Certain death in year 1
    Given qx [1.0, 0.5], lapse [0.0, 0.0], propensity 1.0, term 2, interest_rate 0.0, benefit_amount 1.0
    When value_policy is called
    Then schedule[1].in_force_prob is exactly 0.0
    And value_before_propensity is exactly 1.0

  Scenario: CALC-10 Zero interest is accepted and means no discounting
    Given qx [0.1], lapse [0.0], propensity 1.0, term 1, interest_rate 0.0, benefit_amount 1.0
    When value_policy is called
    Then schedule[0].discount_factor is exactly 1.0

  Scenario: CALC-11 The schedule echoes the inputs
    Given the POL-002 inputs
    When value_policy is called
    Then the schedule has 5 entries with period 1 to 5 in order
    And each entry's qx, lapse, and interest_rate exactly equal the inputs for that year

  Scenario: CALC-12 Inputs are not modified
    Given qx, lapse, and interest_rate lists
    When value_policy is called
    Then each list equals a copy taken before the call

  Scenario: CALC-13 No side effects
    Given valid inputs
    When value_policy is called with capsys capturing output
    Then nothing is written to standard output or standard error

  Scenario: CALC-14 Lapse in year t does not reduce year-t deaths (end-of-year lapse timing)
    Given qx [0.1, 0.1], lapse [0.9, 0.0], propensity 1.0, term 2, interest_rate 0.0, benefit_amount 1.0
    When value_policy is called
    Then schedule[0].expected_death_benefit is 0.1 (the full year-1 deaths, not reduced by year-1 lapses)
    And schedule[1].in_force_prob is 0.09
    And value_before_propensity is 0.109

  Scenario: CALC-15 Largest allowed term
    Given qx [0.001] * 100, lapse [0.0] * 100, propensity 1.0, term 100, interest_rate 0.0, benefit_amount 1.0
    When value_policy is called
    Then the schedule has 100 entries
    And value_before_propensity is 1 - 0.999 ** 100
```

The "POL-001 inputs" and "POL-002 inputs" are the values the sample CSVs produce: the first `term` rows of the durational file, `lapse = 1.0 - persistency_rate`, the per-duration interest rates as a list, and the policy's propensity and face amount.

### 5.2 Validation (`test_policy_valuation.py`)

```gherkin
Feature: value_policy validation

  Scenario Outline: VAL-01 A single invalid input is rejected with a specific message
    Given valid inputs
    When <field> is set to <value> and value_policy is called
    Then it raises PolicyValuationError with message <message>

    Examples:
      | id  | field             | value            | message |
      | a   | term              | 0                | term must be an integer from 1 to 100, got 0 |
      | b   | term              | 101              | term must be an integer from 1 to 100, got 101 |
      | c   | term              | True             | term must be an integer from 1 to 100, got True |
      | d   | term              | 2.0              | term must be an integer from 1 to 100, got 2.0 |
      | e   | qx                | [0.1]            | qx has length 1, expected 2 (one value per policy year) |
      | f   | qx                | None             | qx must be a sequence of numbers, got None |
      | g   | lapse             | "abc"            | lapse must be a sequence of numbers, got 'abc' |
      | h   | qx                | [0.1, 1.5]       | qx[1] = 1.5 is outside [0, 1] |
      | i   | qx                | [0.1, "a"]       | qx[1] is not a number: 'a' |
      | j   | qx                | [0.1, True]      | qx[1] is not a number: True |
      | k   | qx                | [0.1, nan]       | qx[1] = nan is not finite |
      | l   | lapse             | [0.05, -0.1]     | lapse[1] = -0.1 is outside [0, 1] |
      | m   | lapse             | [0.05, inf]      | lapse[1] = inf is not finite |
      | n   | lapse             | [0.05, 0.9]      | qx[1] + lapse[1] = 1.1 > 1 — death and lapse probabilities for the same policy year cannot sum past 1 |
      | o   | propensity_to_buy | 1.2              | propensity_to_buy = 1.2 is outside [0, 1] |
      | p   | propensity_to_buy | nan              | propensity_to_buy = nan is not finite |
      | q   | propensity_to_buy | "0.5"            | propensity_to_buy is not a number: '0.5' |
      | r   | interest_rate     | -0.01            | interest_rate = -0.01 is outside [0, 0.2] (annual rate as a decimal, e.g. 0.05 for 5%) |
      | s   | interest_rate     | 0.21             | interest_rate = 0.21 is outside [0, 0.2] (annual rate as a decimal, e.g. 0.05 for 5%) |
      | t   | interest_rate     | 5                | interest_rate = 5 is outside [0, 0.2] (annual rate as a decimal, e.g. 0.05 for 5%) |
      | u   | interest_rate     | inf              | interest_rate = inf is not finite |
      | v   | interest_rate     | nan              | interest_rate = nan is not finite |
      | w   | interest_rate     | [0.05]           | interest_rate has length 1, expected 2 (one rate per policy year) when given as a sequence |
      | x   | interest_rate     | [0.05, -0.01]    | interest_rate[1] = -0.01 is outside [0, 0.2] (annual rate as a decimal, e.g. 0.05 for 5%) |
      | y   | interest_rate     | [0.05, "x"]      | interest_rate[1] is not a number: 'x' |
      | z   | interest_rate     | [0.05, inf]      | interest_rate[1] = inf is not finite |
      | aa  | interest_rate     | "0.05"           | interest_rate must be a number or a sequence of numbers, got '0.05' |
      | ab  | benefit_amount    | 0                | benefit_amount = 0 must be positive |
      | ac  | benefit_amount    | -5               | benefit_amount = -5 must be positive |
      | ad  | benefit_amount    | 100000001.0      | benefit_amount = 100000001.0 exceeds the maximum of 100,000,000 |
      | ae  | benefit_amount    | nan              | benefit_amount = nan is not finite |
      | af  | benefit_amount    | inf              | benefit_amount = inf is not finite |
      | ag  | benefit_amount    | "1000"           | benefit_amount is not a number: '1000' |

  Scenario: VAL-02 All violations are reported together, in rule order
    Given valid inputs
    When term is 0, propensity_to_buy is 1.2, and benefit_amount is -5
    Then exactly one PolicyValuationError is raised
    And its message starts with "Invalid policy valuation inputs:"
    And its "- " lines are exactly, in order:
      | term must be an integer from 1 to 100, got 0 |
      | propensity_to_buy = 1.2 is outside [0, 1]    |
      | benefit_amount = -5 must be positive          |

  Scenario: VAL-03 A bad scalar interest rate is still reported when term is invalid
    Given valid inputs
    When term is 0 and interest_rate is -0.5
    Then the message contains both the term message and "interest_rate = -0.5 is outside [0, 0.2] (annual rate as a decimal, e.g. 0.05 for 5%)"

  Scenario: VAL-04 One message per element
    Given valid inputs
    When qx is [nan, 2.0]
    Then the message contains "qx[0] = nan is not finite" and "qx[1] = 2.0 is outside [0, 1]"
    And it does not contain "qx[0] = nan is outside"

  Scenario: VAL-05 Boundary values are accepted
    Given qx [0.0, 1.0], lapse [1.0, 0.0], propensity 1.0, term 2, interest_rate 0.2, benefit_amount 100000000
    When value_policy is called
    Then no error is raised

  Scenario: VAL-06 Interest rate boundaries in a sequence are accepted
    Given valid inputs with interest_rate [0.0, 0.2]
    When value_policy is called
    Then no error is raised

  Scenario: VAL-07 NumPy inputs are accepted
    Given valid inputs with qx, lapse, and interest_rate as numpy arrays
    When value_policy is called
    Then no error is raised
    And the result exactly equals the result for the same inputs as lists
    # Skipped with pytest.importorskip("numpy") if NumPy is not installed; NumPy is not a required dependency.

  Scenario: VAL-08 PolicyValuationError is a ValueError
    Given any invalid input
    When value_policy is called
    Then the exception is an instance of ValueError

  Scenario: VAL-09 Limits are the documented constants
    Then policy_valuation.MAX_TERM == 100
    And MIN_INTEREST_RATE == 0.0 and MAX_INTEREST_RATE == 0.20
    And MAX_BENEFIT_AMOUNT == 100_000_000
```

In row n, the test builds the expected string with `f"{0.2 + 0.9}"` rather than typing `1.1`, so it matches whatever float `repr` Python produces.

### 5.3 CSV loading (`test_run_from_csv.py`)

```gherkin
Feature: CSV loaders

  Scenario: LOAD-01 Sample files load
    Given the sample CSV files
    When both loaders are called
    Then the durational loader returns 5 DurationRow in duration order
    And the policy loader returns 2 PolicyRow: POL-001 then POL-002

  Scenario: LOAD-02 Missing required column
    Given a durational CSV whose header lacks interest_rate
    When load_durational_assumptions is called
    Then CSVLoadError is raised with message exactly "<path>: missing required column(s): ['interest_rate']"

  Scenario: LOAD-03 Missing required column in the policy file
    Given a policy CSV whose header lacks face_amount and term
    When load_policy_assumptions is called
    Then CSVLoadError is raised with message exactly "<path>: missing required column(s): ['face_amount', 'term']"

  Scenario: LOAD-04 Extra columns and any column order are accepted
    Given a durational CSV with columns interest_rate,note,qx,duration,persistency_rate and the sample values
    When run() is called with the sample policy CSV
    Then the results match the golden values

  Scenario: LOAD-05 Rows out of order are sorted
    Given the sample durational CSV with its data rows in reverse order
    When run() is called with the sample policy CSV
    Then the results match the golden values

  Scenario: LOAD-06 Duplicate duration
    Given a durational CSV where row 3 repeats duration 1
    When load_durational_assumptions is called
    Then CSVLoadError is raised and its message contains "row 3: duplicate duration 1"

  Scenario: LOAD-07 Gap in durations
    Given a durational CSV with durations 1, 2, 4
    When load_durational_assumptions is called
    Then its message contains "durations must be contiguous starting at 1 with no gaps — found [1, 2, 4], expected [1, 2, 3]"

  Scenario: LOAD-08 Non-integer duration
    Given a durational CSV where row 2 has duration "1.0"
    When load_durational_assumptions is called
    Then its message contains "row 2: duration = '1.0' is not an integer"

  Scenario: LOAD-09 Persistency out of range
    Given a durational CSV where row 2 has persistency_rate 1.2
    When load_durational_assumptions is called
    Then its message contains "row 2: persistency_rate = 1.2 is outside [0, 1]"

  Scenario: LOAD-10 Non-numeric and non-finite values, all reported together
    Given a durational CSV where row 2 has qx "abc", row 3 has interest_rate "nan", and row 4 has persistency_rate "inf"
    When load_durational_assumptions is called
    Then one CSVLoadError is raised
    And its message contains "row 2: qx = 'abc' is not a number"
    And its message contains "row 3: interest_rate = 'nan' is not finite"
    And its message contains "row 4: persistency_rate = 'inf' is not finite"
    And its message starts with "Invalid durational assumptions file:"

  Scenario: LOAD-11 File saved by Excel with a byte-order mark
    Given the sample durational and policy CSVs written to tmp_path with a leading UTF-8 byte-order mark
    When both loaders are called
    Then 5 and 2 rows are returned and no error is raised

  Scenario: LOAD-12 File that is not UTF-8
    Given a policy CSV written to tmp_path in cp1252 containing the policy_id "POL-é"
    When load_policy_assumptions is called
    Then CSVLoadError is raised with message exactly "<path>: file is not valid UTF-8 text"

  Scenario: LOAD-13 Unreadable file
    Given a path that does not exist
    When load_durational_assumptions is called
    Then CSVLoadError is raised and its message starts with "<path>: file cannot be read:"

  Scenario: LOAD-14 Duplicate and empty policy IDs
    Given a policy CSV where row 3 repeats POL-001 and row 4 has an empty policy_id
    When load_policy_assumptions is called
    Then one CSVLoadError is raised
    And its message contains "duplicate policy_id 'POL-001'"
    And its message contains "policy_id is empty"

  Scenario Outline: LOAD-15 Invalid term in the policy file
    Given a policy CSV where POL-001 has term <raw>
    When load_policy_assumptions is called
    Then its message contains "term = <repr> is not a positive integer"

    Examples:
      | raw | repr  |
      | 3.5 | '3.5' |
      | 0   | '0'   |
      | -1  | '-1'  |
      | abc | 'abc' |

  Scenario: LOAD-16 Non-finite values in the policy file
    Given a policy CSV where POL-001 has face_amount "inf" and POL-002 has propensity_to_buy "nan"
    When load_policy_assumptions is called
    Then its message contains "face_amount = 'inf' is not finite"
    And its message contains "propensity_to_buy = 'nan' is not finite"

  Scenario: LOAD-17 Header-only files
    Given durational and policy CSVs with a header and no data rows
    When each loader is called
    Then each returns an empty list
```

### 5.4 Batch run (`test_run_from_csv.py`)

```gherkin
Feature: run()

  Scenario: RUN-01 Policy term longer than the durational table
    Given the sample durational CSV and a policy CSV with POL-009 term 6
    When run() is called
    Then CSVLoadError is raised
    And its message contains "Policy 'POL-009' has term=6, but <durational_path> only has 5 duration(s) of assumptions"

  Scenario: RUN-02 All failing policies are reported together
    Given the sample durational CSV and a policy CSV with, in order:
      | POL-A | term 3 | propensity 0.5 | face_amount 0         |
      | POL-B | term 2 | propensity 0.5 | face_amount 1000      |
      | POL-C | term 9 | propensity 0.5 | face_amount 1000      |
    When run() is called
    Then one CSVLoadError is raised
    And its message starts with "Valuation failed for 2 of 3 policies:"
    And it contains "Policy 'POL-A' failed valuation: Invalid policy valuation inputs:"
    And it contains "Policy 'POL-C' has term=9"
    And it does not mention POL-B
    And no result list is returned

  Scenario: RUN-03 Load errors in both files are reported together
    Given a durational CSV with a duplicate duration and a policy CSV with a duplicate policy_id
    When run() is called
    Then one CSVLoadError is raised
    And its message contains "Invalid durational assumptions file:" before "Invalid policy assumptions file:"

  Scenario: RUN-04 A durational load error still loads the policy file
    Given a durational CSV that is missing a column and a valid policy CSV
    When run() is called with load_policy_assumptions wrapped by a spy
    Then the spy was called once
    And CSVLoadError is raised with only the durational error

  Scenario: RUN-05 A shorter term uses the first rows only
    Given the sample durational CSV and a policy with term 3
    When run() is called with value_policy wrapped by a spy
    Then value_policy received qx [0.01, 0.02, 0.03], lapse built from persistency [0.95, 0.95, 0.95], and interest_rate [0.05, 0.05, 0.05]

  Scenario: RUN-06 Lapse is 1 - persistency
    Given the sample files
    When run() is called
    Then for POL-002, schedule[t].lapse == 1.0 - persistency_rate[t] exactly, for every t

  Scenario: RUN-07 Empty policy file
    Given the sample durational CSV and a policy CSV with a header and no rows
    When run() is called
    Then an empty list is returned

  Scenario: RUN-08 run() has no output and writes no files
    Given the sample files and an empty tmp_path as working directory
    When run() is called with capsys capturing output
    Then nothing is printed and tmp_path is still empty
```

### 5.5 Run log (`test_run_log.py`)

```gherkin
Feature: run metadata and run log

  Scenario: LOG-01 Metadata fields
    Given the sample files and fixed_now
    When collect_run_metadata is called
    Then run_id is "valuation-run-20260923T140509Z"
    And started_at_utc is "2026-09-23T14:05:09Z"
    And spec_id is "pricing-engine-policy-valuation"
    And inputs is [durational, policy] with the paths exactly as given

  Scenario: LOG-02 File fingerprints
    Given the sample files
    When collect_run_metadata is called
    Then each input's sha256 equals hashlib.sha256 of the file's bytes, as lowercase hex

  Scenario: LOG-03 Unreadable input file
    Given a durational path that does not exist
    When collect_run_metadata is called
    Then that input's sha256 is None and no exception is raised

  Scenario: LOG-04 Git available
    Given the tests are running inside the Vita git repository
    When collect_run_metadata is called
    Then code_commit is a 40-character lowercase hex string
    And code_dirty is True or False
    # Skipped if git is not on PATH.

  Scenario: LOG-05 Git unavailable
    Given no_git
    When collect_run_metadata is called
    Then code_commit is None and code_dirty is None and no exception is raised

  Scenario: LOG-06 Spec version matches the spec
    When the frontmatter of "specs/pricing engine module - spec.md" is read
    Then its version equals run_log.SPEC_VERSION
    And its spec_id equals run_log.SPEC_ID

  Scenario: LOG-07 Success log
    Given fixed_now and the results of run() on the sample files
    When write_run_log(tmp_path, metadata, results=results) is called
    Then it returns tmp_path / "valuation-run-20260923T140509Z.json"
    And the file is valid UTF-8 JSON ending in a newline
    And log_format_version is 1, status is "success", error_message is null
    And results[i].policy equals dataclasses.asdict of each PolicyRow
    And results[i].result equals dataclasses.asdict of each PolicyValuationResult, with every number exactly equal after a JSON round trip

  Scenario: LOG-08 Failure log
    Given fixed_now
    When write_run_log(tmp_path, metadata, error_message="boom") is called
    Then status is "failed", error_message is "boom", and results is []

  Scenario: LOG-09 Both or neither of results and error_message
    When write_run_log is called with both, and again with neither
    Then each call raises ValueError and no file is written

  Scenario: LOG-10 Existing logs are never overwritten
    Given tmp_path already contains "valuation-run-20260923T140509Z.json" with content "keep"
    When write_run_log is called twice with the same metadata
    Then the files "-2.json" and "-3.json" are created
    And the original file still contains "keep"

  Scenario: LOG-11 Non-finite numbers cannot be written
    Given a results list containing a float nan (built by hand, bypassing validation)
    When write_run_log is called
    Then ValueError is raised
```

### 5.6 Command line (`test_cli.py`)

CLI tests call `run_from_csv.main(argv)` directly, with `builtins.input` replaced by a scripted answer list and output captured by `capsys`, except CLI-01, which runs the script as a real subprocess.

```gherkin
Feature: command-line tool

  Scenario: CLI-01 End to end with all paths as arguments
    Given the sample CSVs and an empty tmp_path as log folder
    When "python code/run_from_csv.py <durational> <policy> <tmp_path>" is run as a subprocess from modules/pricing-engine/
    Then the exit code is 0
    And standard error is empty
    And standard output lines 7 to 10 are exactly:
      """
      policy_id  term propensity  face_amount          value
      --------------------------------------------------------
      POL-001       3       0.50      100,000       2,463.82
      POL-002       5       0.35      250,000       8,380.76
      """
    And the last line is "Run log written to <path>" and that file exists in tmp_path
    And the log's status is "success"

  Scenario: CLI-02 Report header
    Given fixed metadata (via monkeypatching collect_run_metadata) with code_commit "0123456789abcdef0123456789abcdef01234567", code_dirty True, and known sha256 values
    When main is called with all three paths
    Then the first five lines of standard output are exactly:
      """
      Run:        valuation-run-20260923T140509Z
      Spec:       pricing-engine-policy-valuation v0.2
      Code:       0123456789ab (uncommitted changes)
      Durational: <durational path>  sha256 <first 12 hex of its sha256>
      Policy:     <policy path>  sha256 <first 12 hex of its sha256>
      """
    And line 6 is empty

  Scenario: CLI-03 Unknown code version
    Given metadata with code_commit None and code_dirty None
    When main is called
    Then the Code line is exactly "Code:       unknown"

  Scenario: CLI-04 Prompts for every missing path, in order
    Given no arguments and scripted answers [durational, policy, tmp_path]
    When main is called
    Then input() was called with the prompts, in order:
      | Path to durational assumptions CSV: |
      | Path to policy assumptions CSV:     |
      | Folder for the run log:             |
    And the exit code is 0

  Scenario: CLI-05 Prompts only for paths not given
    Given the durational path as the only argument and scripted answers [policy, tmp_path]
    When main is called
    Then input() was called only with the policy and log folder prompts

  Scenario: CLI-06 Empty answer asks again
    Given no arguments and scripted answers ["", "   ", durational, policy, tmp_path]
    When main is called
    Then the durational prompt was shown 3 times
    And the exit code is 0

  Scenario: CLI-07 Nonexistent path asks again
    Given no arguments and scripted answers ["nope.csv", durational, policy, "no_such_folder", tmp_path]
    When main is called
    Then standard error contains "File not found: nope.csv" and "Folder not found: no_such_folder"
    And the exit code is 0

  Scenario: CLI-08 Quotes from "Copy as path" are removed
    Given no arguments and scripted answers ['"<durational>"', ' "<policy>" ', tmp_path]
    When main is called
    Then the exit code is 0

  Scenario: CLI-09 End of input
    Given no arguments and an input() that raises EOFError
    When main is called
    Then the exit code is 1
    And standard error contains "No input received; stopping."
    And no log file exists

  Scenario: CLI-10 Too many arguments
    When main is called with 4 arguments
    Then the exit code is 1
    And standard error contains "usage: python code/run_from_csv.py [DURATIONAL_CSV] [POLICY_CSV] [LOG_FOLDER]"

  Scenario: CLI-11 Nonexistent argument paths stop before valuation
    When main is called with a missing durational file, a valid policy file, and a missing log folder
    Then the exit code is 1
    And standard error contains "File not found: <durational>" and "Folder not found: <log folder>"
    And standard output is empty
    And input() was never called

  Scenario: CLI-12 Invalid data writes a failure log and a clean error
    Given a policy CSV with a duplicate policy_id and a tmp_path log folder, all given as arguments
    When main is called
    Then the exit code is 1
    And standard output is empty
    And standard error contains "duplicate policy_id"
    And standard error contains "Run log written to"
    And standard error does not contain "Traceback"
    And tmp_path contains one log with status "failed" whose error_message contains "duplicate policy_id"

  Scenario: CLI-13 Log cannot be written on a successful run
    Given valid inputs and write_run_log monkeypatched to raise OSError("disk full")
    When main is called
    Then the exit code is 1
    And standard output is empty
    And standard error contains "Could not write run log to <folder>: disk full"

  Scenario: CLI-14 Unexpected errors have no traceback
    Given run monkeypatched to raise RuntimeError("kaboom")
    When main is called
    Then the exit code is 1
    And standard error is exactly "Unexpected error: RuntimeError: kaboom\n"
    And standard error does not contain "Traceback"

  Scenario: CLI-15 Empty policy file
    Given the sample durational CSV and a header-only policy CSV
    When main is called
    Then the exit code is 0
    And the table has only its two header lines
```

### 5.7 Contracts (`test_contracts.py`)

```gherkin
Feature: JSON Schema contracts

  Scenario: CON-01 Every schema is a valid draft 2020-12 schema
    When each of the five files in contracts/ is loaded
    Then jsonschema.Draft202012Validator.check_schema passes for each

  Scenario: CON-02 Sample inputs match the input schema
    Given the POL-001 and POL-002 inputs as JSON objects
    Then each validates against policy-valuation.input.schema.json

  Scenario Outline: CON-03 Out-of-limit inputs fail the input schema
    Given the POL-001 inputs with <field> set to <value>
    Then validation against policy-valuation.input.schema.json fails

    Examples:
      | field          | value          |
      | term           | 101            |
      | term           | 0              |
      | interest_rate  | 0.21           |
      | interest_rate  | -0.01          |
      | interest_rate  | [0.05, 0.25]   |
      | benefit_amount | 100000001      |
      | benefit_amount | 0              |
      | qx             | [0.1, 1.5]     |

  Scenario: CON-04 Golden results match the output schema
    Given dataclasses.asdict of each golden result
    Then each validates against policy-valuation.output.schema.json

  Scenario: CON-05 Sample CSV rows match the CSV row schemas
    Given each loaded sample row as a dict of its required columns
    Then each validates against its CSV row schema

  Scenario: CON-06 Run logs match the run log schema
    Given the success log from LOG-07 and the failure log from LOG-08
    Then each validates against valuation-run-log.schema.json

  Scenario: CON-07 The run log schema rejects inconsistent logs
    Given a log with status "failed" and a non-empty results list
    And a log with status "success" and a non-null error_message
    Then each fails validation against valuation-run-log.schema.json

  Scenario: CON-08 Sample files in input/ match the test fixtures
    Then input/durational_assumptions.csv is byte-identical to tests/fixtures/durational_assumptions.csv
    And input/policy_assumptions.csv is byte-identical to tests/fixtures/policy_assumptions.csv
```

CON-08 keeps the README example and the golden values tied to the same data.

### 5.8 Golden-value regression (`test_regression_golden.py`)

```gherkin
Feature: golden values

  Scenario: GOLD-01 Sample policies through run()
    Given the sample CSV files
    When run() is called
    Then two results are returned in the order POL-001, POL-002
    And each value, value_before_propensity, and every schedule field matches Section 4.3 within the tolerance

  Scenario: GOLD-02 Sample policies through value_policy directly
    Given the POL-001 and POL-002 inputs
    When value_policy is called on each
    Then the results exactly equal those from GOLD-01

  Scenario: GOLD-03 Sample policies through the CLI
    Given the sample CSV files
    When the CLI is run
    Then the log's results match Section 4.3 within the tolerance
```

## 6. Regression procedure for the changes from the old code

AGENTS.md requires that a bug fix comes with a regression test that fails before the fix and passes after it. Spec Section 5.4 lists nine changes (D1–D9). `tests/test_regression_changes.py` holds one or more tests for each, and each test's docstring names its change.

| Test | Change | Checks | Expected on old code (`43b3751`) |
|---|---|---|---|
| REG-D1a | D1 | `value_policy` with `interest_rate=[0.05, inf]` raises; message contains `interest_rate[1] = inf is not finite` | Fails: returns a result whose year-2 discount factor is 0 |
| REG-D1b | D1 | `value_policy` with `benefit_amount=nan` raises | Fails: returns `value` of nan |
| REG-D1c | D1 | Durational CSV with interest_rate `inf` raises `CSVLoadError` containing `is not finite` | Fails: loads |
| REG-D2 | D2 | `value_policy(qx=None, ...)` raises `PolicyValuationError`, not `TypeError` | Fails: `TypeError` |
| REG-D3 | D3 | The sample durational CSV written with a UTF-8 byte-order mark loads | Fails on Windows: missing column `duration` |
| REG-D4 | D4 | CLI with a duplicate policy_id: stderr has no `Traceback` | Fails: traceback printed |
| REG-D5a | D5 | `term=101` raises | Fails: accepted |
| REG-D5b | D5 | `interest_rate=-0.01` raises | Fails: accepted |
| REG-D5c | D5 | `interest_rate=0.21` raises | Fails: accepted |
| REG-D5d | D5 | `benefit_amount=100_000_001` raises | Fails: accepted |
| REG-D6 | D6 | Two failing policies are both named in one error | Fails: only the first is named |
| REG-D7 | D7 | A CLI run creates a log file in the chosen folder | Fails: no log |
| REG-D8 | D8 | A CLI run with no arguments calls `input()` | Fails: uses default file names |
| REG-D9 | D9 | `term=0` message is `term must be an integer from 1 to 100, got 0` | Fails: old message |

Procedure (done once, before the implementation is merged, and recorded as evidence):

1. Check out the old code into a temporary folder: `git worktree add <tmp> 43b3751`.
2. Run `python -m pytest tests/test_regression_changes.py` with `PRICING_ENGINE_CODE_DIR=<tmp>/modules/pricing-engine/code`. `conftest.py` uses this environment variable, when set, in place of `code/` on `sys.path`.
3. Record the result. Every REG test must fail. For REG-D7 and REG-D8, failing because `run_log` or `main` does not exist counts as a failure.
4. Run the same file against the new code. Every REG test must pass.
5. Remove the worktree.

REG-D3 depends on the platform default encoding. If the procedure is run on a system whose default is UTF-8, REG-D3 may pass on the old code; record the platform and note it in the evidence.

## 7. Manual UAT against the Excel workbook

The workbook `uat/policy_valuation_uat.xlsx` recomputes POL-001 and POL-002 with Excel formulas. It is an independent check that does not share any code with the Python calculator.

Procedure (actuary reviewer):

1. Run the CLI on the sample files in `input/` with a log folder of your choice.
2. Open the workbook in Excel and let it recalculate.
3. For each policy and each policy year, compare the workbook's in-force probability, expected death benefit, discount factor, and present value with the matching entry in the run log's `results[].result.schedule`, and compare the totals with `value_before_propensity` and `value`.
4. Every value must agree to at least 10 significant figures.
5. Record the run log file name, the workbook's file hash (SHA-256), the reviewer, the date, and the outcome.

Whether this check becomes an automated test is spec open question Q11.

## 8. LLM-as-judge review

Run after all automated tests pass and before human sign-off. It checks that the implementation matches the spec and contains nothing the spec does not ask for. It cannot replace human sign-off, and a failing result blocks sign-off.

### 8.1 Inputs

Recorded with the result so the review can be reproduced:

```yaml
judge_model: the exact model ID used (for example claude-opus-5-5), recorded, not assumed
rubric_version: pricing-engine-policy-valuation-judge v1.0 (Section 8.2)
spec: "specs/pricing engine module - spec.md" at the commit under review
testing_doc: this document at the commit under review
diff: git diff between 43b3751 and the commit under review, restricted to modules/pricing-engine/
test_output: the full pytest output, including the coverage report
temperature: 0
```

### 8.2 Rubric v1.0

Each criterion is scored 1–5 with a one-paragraph justification that cites file and line.

| # | Criterion | 5 means | 1 means |
|---|---|---|---|
| J1 | Methodology | The calculation matches spec Section 6 (Methodology and timing, Calculation) exactly, including operation order | Any formula or timing differs |
| J2 | Validation | Every rule V1–V14 is implemented in order with the exact message text; limits use the named constants | A rule is missing or a message differs |
| J3 | Loaders and run() | Loader steps, error collection, and the all-failures behavior match the spec | Stops early or messages differ |
| J4 | Run log and CLI | Metadata, file naming, no-overwrite, prompts, stderr/stdout split, and exit codes match the spec | Any listed behavior differs |
| J5 | Scope | No features, dependencies, files, or refactors beyond the spec; runtime uses only the standard library | Unrequested changes present |
| J6 | Test fidelity | Every scenario in this document has a test with the matching ID; no test is skipped, weakened, or asserts less than the scenario states | Scenarios missing or weakened |
| J7 | Safety | No secrets, credentials, account IDs, environment-specific endpoints, or production data | Any present |

### 8.3 Pass threshold

The review passes only if every criterion scores 4 or 5, and J1, J5, and J7 each score 5. Any other result is a fail, and the judge's findings go back to implementation.

## 9. Sign-off gates and evidence

| Gate | Condition | Evidence to attach to the pull request |
|---|---|---|
| G1 Automated tests | All tests in Section 5 pass; coverage ≥ 90% | Full pytest output with the coverage report |
| G2 Regression proof | Section 6 procedure: all REG tests fail on the old code and pass on the new | Both pytest outputs and the platform used |
| G3 UAT | Section 7 comparison agrees for both policies | The UAT record from Section 7 step 5 |
| G4 LLM-as-judge | Section 8 passes | The inputs from 8.1, scores, and justifications |
| G5 Human sign-off | A human actuary approves the methodology and results; a human reviewer approves the code | Names and dates in the pull request |

G5 is required regardless of G4 (AGENTS.md hard rule). Nothing is pushed until all five gates pass.

## 10. Traceability matrix

Every spec requirement and change maps to at least one test or check.

| Spec item | Covered by |
|---|---|
| R1 value_policy signature and result | CALC-01, GOLD-02 |
| R2 collect all violations | VAL-02, VAL-03, VAL-04 |
| R3 scalar or sequence interest | CALC-04, CALC-05, VAL-01 w |
| R4 exact calculation | GOLD-01, GOLD-02, CALC-01–CALC-15, UAT |
| R5 result contents | CALC-11, GOLD-01 |
| R6 no side effects | CALC-12, CALC-13 |
| R7 input limits | VAL-01 a–b r–t ad, VAL-05, VAL-06, VAL-09, CALC-15 |
| R8 durational loader | LOAD-01, LOAD-02, LOAD-04–LOAD-11, LOAD-13, LOAD-17 |
| R9 policy loader | LOAD-01, LOAD-03, LOAD-12, LOAD-14–LOAD-17 |
| R10 loader error collection | LOAD-10, LOAD-14, LOAD-16 |
| R11 run() | GOLD-01, RUN-05–RUN-08 |
| R12 all failures together | RUN-01–RUN-04 |
| R13 CLI runs and reports | CLI-01, CLI-02, CLI-03, CLI-15, GOLD-03 |
| R14 prompts | CLI-04–CLI-09 |
| R15 run log on every run | CLI-01, CLI-11, CLI-12, LOG-07, LOG-08 |
| R16 CLI failure behavior | CLI-09–CLI-14 |
| R17 folder layout | CON-08; human review |
| R18 standard library only | J5; human review |
| R19 no Dockerfile | Human review |
| R20 contracts | CON-01–CON-07 |
| Methodology and timing rules 1–9 | CALC-02, CALC-03, CALC-09, CALC-14, GOLD-01, UAT, J1 |
| Glossary | J1; human review |
| D1 | REG-D1a–c, VAL-01 k m p u v z ae af, LOAD-10, LOAD-16 |
| D2 | REG-D2, VAL-01 f g |
| D3 | REG-D3, LOAD-11, LOAD-12 |
| D4 | REG-D4, CLI-12, CLI-14 |
| D5 | REG-D5a–d, VAL-01 b r s t ad, CON-03 |
| D6 | REG-D6, RUN-02, RUN-03 |
| D7 | REG-D7, LOG-01–LOG-11, CLI-12 |
| D8 | REG-D8, CLI-04–CLI-09 |
| D9 | REG-D9, VAL-01 |

## 11. Open questions

T1. Where should gate evidence be kept long term: only in the pull request, or also in the repository (for example under `ops/`)? The evidence table in Section 9 assumes the pull request.

T2. Should the judge model be pinned to one model ID in this document, or recorded per run as Section 8.1 does now?

T3. Spec Q11: should the Section 7 workbook comparison be automated (reading the workbook's cached values with a test-only library such as `openpyxl`)?

## 12. Version history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-23 | First draft, for spec v0.2. Carries forward the v0.1 spec's sample data, golden values, and scenarios; changes the negative-rate and 25%-rate scenarios to fit the 0–20% limit (D5); adds tests for D1–D9, run log, CLI prompts, and contracts. |
