---
spec_id: <module>-<short-slug>            # e.g. pricing-engine-yield-curve-support
title: <Feature title>
module: <mortality | propensity | persistency | pricing-engine | quote-intel | mcp-server | ui>
status: draft                              # draft -> reviewed -> approved -> implemented
version: 0.1
owner_persona: <persona writing this spec>
reviewers: []                              # personas that must sign off before status = approved
touches_core_model_logic: <true | false>   # true if this touches pricing-engine, mortality,
                                            # propensity, or persistency model logic or parameters
created: <YYYY-MM-DD>
last_updated: <YYYY-MM-DD>
---

# <Feature title>

## 1. Problem statement
What problem does this solve, in one or two sentences. State the problem, not the solution.

## 2. Background
The "why" behind this spec: what led to it, what happens if it's not built, and any context
the implementing agent needs to make good judgment calls on the parts this spec doesn't
cover explicitly.

## 3. Intended users
Who uses this — a persona, an internal team, an external carrier, an end customer. Be
specific; "users" alone isn't enough for the agent to design around.

## 4. Out of scope
List explicitly what this spec does not cover. Anything not listed here but also not covered
in section 6 is a gap — flag it as an open question in section 9 rather than assuming an
answer.

## 5. Requirements
Functional requirements, broken into discrete, numbered items. Each one should be specific
enough that a person could tell whether it was met just by reading it.

1. ...
2. ...

## 6. Technical design

### Data / schema
Tables, fields, types, and relationships this feature reads or writes. Note which are new
and which already exist.

### API contract
Reference the authoritative contract in `contracts/<module>/`. If the contract doesn't exist
yet, sketch the request/response shape here and note that the OpenAPI/JSON Schema file
still needs to be written — the file in `contracts/` is authoritative once it exists, not this
section.

### Tools and libraries
Specific tools/libraries this feature depends on, with version numbers.

## 7. Visual aids
Diagrams (sequence, data flow, state) where they clarify the design faster than prose.
Link to a file or embed as Mermaid/ASCII. Optional if the feature is simple enough that a
diagram wouldn't add anything.

## 8. Acceptance criteria
Written as Gherkin scenarios (Scenario / Given / When / Then). Each criterion must be
specific enough to become a test case directly — if you can't turn it into a test, it isn't
specific enough yet. Include edge cases, not just the happy path.

```gherkin
Scenario: <name>
  Given <starting state>
  When <action>
  Then <expected outcome>

Scenario: <edge case name>
  Given <starting state>
  When <action>
  Then <expected outcome>
```

## 9. Open questions
Anything unresolved. List as questions, not as assumed answers — leave it for a human to
resolve rather than inventing a default.

## 10. Sign-off
- [ ] Persona review(s) complete: <list personas from `reviewers`>
- [ ] LLM-as-judge review passed (routine changes only)
- [ ] Human sign-off obtained — **required** if `touches_core_model_logic: true`, regardless
      of judge score
