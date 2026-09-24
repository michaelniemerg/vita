# Vita — Actuarial Requirements Document (Draft for Review)

## Status of this document

This is a first-pass structure, not a finished requirements document. Per
your instruction, I haven't invented formulas, discount rates, mortality
tables, or other project-specific assumptions for Vita — none of those have
been discussed, and guessing at them would just be fabrication dressed up
as a requirements doc. What follows is:

1. The standard categories any life insurance pricing actuarial requirements
   document has to cover (this part is general actuarial practice, not
   specific to Vita — safe to state as fact), and
2. For each category, the specific open question that needs an answer
   before it can actually be filled in for Vita.

I'm not a licensed actuary, and this document doesn't substitute for review
by one — particularly before anything here informs real pricing or a
regulatory filing.

## What's established so far, from our conversation

- Vita combines three model modules — mortality, propensity-to-buy, and
  persistency — into a pricing engine, each with its own API as its own
  module.
- The pricing engine produces both a price and an ROI-style output, "from a
  life insurer's perspective" rather than a consumer-shopping perspective.
- The specific ROI metric has already been flagged as undefined — this
  document treats that as Question 9 below, not a decided input.
- "Real-time" simulation is a stated goal; the latency target itself is
  still an open decision elsewhere (in the to-do list), and it bears on
  Question 13 (scenario testing) below.
- Whether Vita uses real historical policy/claims data, licensed data, or
  synthetic/public data is still an open decision elsewhere in the to-do
  list, and it affects several sections below (particularly mortality basis
  and regulatory basis).

---

## 1. Product scope

Which life insurance products this document applies to — term, whole life,
universal life, indexed or variable products, group vs. individual — changes
almost every other section (a term policy's premium structure looks very
different from whole life's cash-value mechanics, for instance).

**Open question:** Which product type(s) is Vita pricing, at least for the
first version?

## 2. Mortality basis

Standard practice is to price against a defined mortality table or
assumption set — industry tables like the Society of Actuaries' 2017 CSO
tables are the current basis referenced in the NAIC Valuation Manual, often
with a company's own experience-based adjustment layered on top, and with
mortality improvement scales applied to project future years. Where the
assumption comes from and how it's structured (select-and-ultimate, by
duration, etc.) needs to be defined.

**Open questions:**
- Is Vita's "mortality model" meant to be an industry-table-based
  assumption, a fully company-experience-based model built from your own
  data (the way the PMPM risk-scoring work was), or a blend of both?
- Does it need to distinguish pricing mortality from valuation/reserve
  mortality, or is a single basis intended to serve both?

## 3. Persistency / lapse basis

Persistency (or its inverse, lapse) affects both pricing and reserving: how
long a policy is expected to stay in force changes the present value of
future premiums and claims. This is usually expressed as a lapse rate curve
by policy duration, sometimes made "dynamic" — sensitive to price changes
relative to a baseline expectation.

**Open questions:**
- Does the persistency model output a lapse curve by duration, a single
  retention probability, or something else?
- Should lapse be treated as dynamic (responsive to Vita's own pricing
  decisions) or static?

## 4. Propensity-to-buy's role

Propensity-to-buy could function two different ways in a pricing platform:
as an input to price optimization itself (e.g., adjusting price based on
predicted conversion, sometimes called price elasticity or demand
modeling), or purely as a volume forecast used to project new business for
ROI purposes, without feeding back into the price shown.

**Open question:** Which of these is intended — does propensity influence
the price itself, or only the volume assumption behind the ROI calculation?

## 5. Premium calculation structure

Standard actuarial practice separates a net premium (the pure cost of
providing the benefit, based on mortality and interest assumptions) from a
gross premium (net premium plus loadings for expenses, profit margin, and
risk margin). Which loadings apply and how they're structured is a design
decision, not something derivable from the model outputs alone.

**Open question:** What loading structure applies — expense loading, target
profit margin, risk margin — and has any of this been decided, even
roughly?

## 6. Reserve methodology

US life insurance reserves currently follow a principle-based approach
under the NAIC's VM-20 (for life products) rather than the older
formula-based approach, generally built on a company's own prudent
mortality, lapse, and expense assumptions rather than fixed tables alone.
Whether Vita needs an actual regulatory-compliant reserve calculation or
just an internal, simplified proxy for pricing purposes is a scope
decision.

**Open question:** Does Vita need to produce reserves that could hold up to
regulatory or audit scrutiny, or only an internal approximation used to
inform pricing decisions?

## 7. Discount rate / investment assumptions

Pricing and reserving both require discounting projected future cash flows
back to present value, which requires a rate — a risk-free rate, a
company's required rate of return, or an assumed investment portfolio
yield are all used in different contexts for different purposes.

**Open question:** What discount rate (or rates, if pricing and ROI use
different ones) should be used, and where does it come from?

## 8. Expense assumptions

Pricing needs an assumption for acquisition costs (commissions,
underwriting) and ongoing maintenance/administrative expenses. These are
typically either based on a company's actual expense experience or an
assumed expense schedule.

**Open question:** Where do expense assumptions come from — actual
historical expense data, an assumed schedule, or something else?

## 9. Profitability / ROI metric

Already flagged as undefined. Common candidates in life insurance pricing
include internal rate of return (IRR), present value of future profits
(PVFP), a loss ratio, a lapse-adjusted profit margin, or a payback/breakeven
period — these aren't interchangeable and measure different things.

**Open questions:**
- Which metric (or metrics) should "ROI" actually mean for Vita?
- Over what time horizon is it calculated — policy lifetime, a fixed
  projection period, or something else?

## 10. Regulatory basis and jurisdiction

Life insurance pricing and reserving are state-regulated in the US, under
NAIC model laws (and each state's own adoption of them), and typically
require rate filings and, for reserves, materials like an actuarial
memorandum. This ties directly to the still-open question elsewhere of
whether Vita is an internal decision-support tool or something closer to a
filing-support tool.

**Open question:** Does Vita need to produce anything filing-ready, or is
its output purely for internal decision-making with no regulatory filing
attached?

## 11. Risk margins / provision for adverse deviation (PAD)

Actuarial assumptions are typically padded with some deliberate
conservatism (a "provision for adverse deviation") to guard against
assumptions turning out worse than expected. How much conservatism to
build in, and where, is a judgment call tied to a company's risk appetite.

**Open question:** Is any margin for conservatism expected in Vita's
calculations, or are "best estimate" assumptions intended throughout?

## 12. Reinsurance

Not mentioned anywhere in our conversation so far. Ceded reinsurance
changes net pricing and net reserves materially if it applies.

**Open question:** Does reinsurance factor into Vita's pricing calculations
at all, now or later?

## 13. Sensitivity and scenario testing

This connects directly to the "real-time simulation" goal — running a
pricing strategy and seeing results back quickly implies varying some set
of inputs and observing the effect. Common dimensions in life insurance
include mortality shocks, lapse spikes, and interest rate scenarios.

**Open question:** What should actually be variable in a Vita simulation
run — which assumptions, and across what range?

## 14. Assumption governance and review cadence

Ties to the Actuary persona and the model-validation sign-off gate already
defined elsewhere: assumptions (mortality, lapse, expense, discount rate)
typically get revisited on some cadence, often an annual experience study,
with a defined sign-off before an updated assumption goes into production
pricing.

**Open question:** What review cadence is expected, and does it match the
model-validation sign-off gate already defined in the to-do list, or does
it need its own?

## 15. Pricing-run output and audit requirements

The to-do list already calls for a pricing-run log (model versions used,
input hash, output) for reproducibility. This section is about what
specifically needs to be in that output — beyond just a price, does a
pricing run need to output the reserve, the cash flow projection, the
assumptions used, or just the final numbers?

**Open question:** What exact fields does a single pricing run need to
produce and log?

---

## Summary of open questions

Fifteen open questions, one per section above. None of them have been
answered yet — this document is meant to make them concrete enough to
actually discuss, not to propose defaults.
