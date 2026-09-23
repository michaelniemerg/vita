"""
policy_valuation.py

Computes the actuarial present value of a term policy's death benefit,
combining a mortality (qx) stream, a lapse stream, an interest rate (flat
or duration-varying), and propensity-to-buy into a single expected value.

METHODOLOGY (stated explicitly, since none of this is defined yet in
vita-actuarial-requirements.md — this is a specific modeling choice, not
a given formula):

1. Decrements. Death and lapse are treated as independent within each
   period: the probability of remaining in force through period t is
   (1 - qx[t]) * (1 - lapse[t]). This is the standard "independent rates"
   simplification used when working from already-estimated single-decrement
   rates, rather than building a true multiple-decrement table from raw
   exposure data.

2. Benefit timing. Discrete / end-of-period (curtate): a death occurring
   during period t is assumed to pay at the end of period t. The discount
   factor for period t is the cumulative product of each period's own
   one-period discount factor, 1 / (1 + rate[k]) for k = 1..t — this
   supports a duration-varying rate (a simple yield curve), not just a
   single flat rate, though a flat rate still works (it's just the
   special case where every rate[k] is equal). No mid-period or continuous
   timing assumption is applied.

3. Propensity to buy. Applied as a single multiplier on the total expected
   value — i.e., it represents the probability this policy is ever issued
   at all, applied once to the whole result. This is a modeling choice: an
   alternative design could apply it inside the survivorship chain instead
   (e.g., if "not buying" could also happen after year 1). Worth revisiting
   once the actuarial requirements document answers Question 4 (propensity's
   role in pricing vs. volume).

4. Scope. This is the actuarial present value of the DEATH BENEFIT only.
   It is not a premium and not a profit/ROI figure — those need loadings,
   expenses, and a defined ROI metric, all still open per
   vita-actuarial-requirements.md (Questions 5 and 9).
"""

import numbers
from dataclasses import dataclass, field
from typing import List, Sequence, Union


class PolicyValuationError(ValueError):
    """Raised when input data fails validation."""


@dataclass
class PeriodDetail:
    period: int
    in_force_prob: float       # probability of being in force at START of this period
    qx: float
    lapse: float
    interest_rate: float            # this period's own one-period rate
    expected_death_benefit: float   # undiscounted, before propensity scaling
    discount_factor: float          # cumulative, period 1..t
    present_value: float            # discounted, before propensity scaling


@dataclass
class PolicyValuationResult:
    value: float                       # headline number, after propensity scaling
    value_before_propensity: float     # APV of the death benefit alone
    schedule: List[PeriodDetail] = field(default_factory=list)


def _is_number(x):
    return isinstance(x, numbers.Real) and not isinstance(x, bool)


def _is_sequence(x):
    return isinstance(x, (list, tuple)) or (
        hasattr(x, "__len__") and hasattr(x, "__getitem__") and not isinstance(x, (str, bytes))
    )


def _normalize_interest_rate(interest_rate, term, errors):
    """
    Accepts either a single scalar rate (applied to every period) or a
    sequence of per-period rates (length must equal `term`). Returns a
    list of length `term`, or None if it couldn't be normalized (errors
    will have been appended in that case).
    """
    if _is_number(interest_rate):
        rate = interest_rate
        if rate <= -1.0:
            errors.append(
                f"interest_rate = {rate} must be > -1 "
                f"(otherwise the discount factor is undefined or non-positive)"
            )
            return None
        return [rate] * term

    if _is_sequence(interest_rate):
        rates = list(interest_rate)
        if len(rates) != term:
            errors.append(
                f"interest_rate has length {len(rates)}, expected {term} "
                f"(one rate per period) when given as a sequence"
            )
            return None
        bad = False
        for i, r in enumerate(rates):
            if not _is_number(r):
                errors.append(f"interest_rate[{i}] is not a number: {r!r}")
                bad = True
            elif r <= -1.0:
                errors.append(
                    f"interest_rate[{i}] = {r} must be > -1 "
                    f"(otherwise the discount factor is undefined or non-positive)"
                )
                bad = True
        return None if bad else rates

    errors.append(
        f"interest_rate must be a number or a sequence of numbers, got {interest_rate!r}"
    )
    return None


def validate_inputs(qx, lapse, propensity_to_buy, term, interest_rate, benefit_amount):
    """Raises PolicyValuationError with every problem found, not just the first."""
    errors = []

    if not isinstance(term, int) or isinstance(term, bool) or term <= 0:
        errors.append(f"term must be a positive integer, got {term!r}")
        term_ok = False
    else:
        term_ok = True

    if term_ok:
        if len(qx) != term:
            errors.append(f"qx has length {len(qx)}, expected {term} (one value per period)")
        if len(lapse) != term:
            errors.append(f"lapse has length {len(lapse)}, expected {term} (one value per period)")

    for i, q in enumerate(qx):
        if not _is_number(q):
            errors.append(f"qx[{i}] is not a number: {q!r}")
        elif not (0.0 <= q <= 1.0):
            errors.append(f"qx[{i}] = {q} is outside [0, 1]")

    for i, l in enumerate(lapse):
        if not _is_number(l):
            errors.append(f"lapse[{i}] is not a number: {l!r}")
        elif not (0.0 <= l <= 1.0):
            errors.append(f"lapse[{i}] = {l} is outside [0, 1]")

    if len(qx) == len(lapse):
        for i, (q, l) in enumerate(zip(qx, lapse)):
            if _is_number(q) and _is_number(l) and (q + l) > 1.0:
                errors.append(
                    f"qx[{i}] + lapse[{i}] = {q + l} > 1 — death and lapse "
                    f"probabilities for the same period shouldn't sum past 1"
                )

    if not _is_number(propensity_to_buy):
        errors.append(f"propensity_to_buy is not a number: {propensity_to_buy!r}")
    elif not (0.0 <= propensity_to_buy <= 1.0):
        errors.append(f"propensity_to_buy = {propensity_to_buy} is outside [0, 1]")

    normalized_rates = None
    if term_ok:
        normalized_rates = _normalize_interest_rate(interest_rate, term, errors)
    else:
        # Still sanity-check a scalar rate even if term is bad, for a clearer error set.
        if _is_number(interest_rate) and interest_rate <= -1.0:
            errors.append(f"interest_rate = {interest_rate} must be > -1")

    if not _is_number(benefit_amount):
        errors.append(f"benefit_amount is not a number: {benefit_amount!r}")
    elif benefit_amount <= 0:
        errors.append(f"benefit_amount = {benefit_amount} must be positive")

    if errors:
        raise PolicyValuationError(
            "Invalid policy valuation inputs:\n- " + "\n- ".join(errors)
        )

    return normalized_rates


def value_policy(
    qx: List[float],
    lapse: List[float],
    propensity_to_buy: float,
    term: int,
    interest_rate: Union[float, Sequence[float]] = 0.0,
    benefit_amount: float = 1.0,
) -> PolicyValuationResult:
    """
    Computes the actuarial present value of a term policy's death benefit,
    scaled by the probability the policy is actually purchased.

    See the module docstring for the methodology and the assumptions it
    embeds — none of this is Vita's decided actuarial approach yet, it's a
    stated, specific set of choices so the number is reproducible and
    arguable.

    Parameters
    ----------
    qx : list of float
        Probability of death in each period, given in force at the start
        of that period. Length must equal `term`.
    lapse : list of float
        Probability of lapse in each period, given in force (alive) at the
        start of that period. Length must equal `term`.
    propensity_to_buy : float
        Probability, in [0, 1], that this policy is actually purchased.
        Applied once, as a multiplier on the total expected value.
    term : int
        Number of periods (e.g., years) the policy covers.
    interest_rate : float or sequence of float, optional
        Either a single per-period discount rate applied to every period
        (defaults to 0, no discounting), or a sequence of length `term`
        giving each period's own one-period rate (a simple yield curve).
    benefit_amount : float, optional
        Death benefit paid on death. Defaults to 1 (unit benefit).

    Returns
    -------
    PolicyValuationResult
        `.value` is the headline number (after propensity scaling).
        `.value_before_propensity` is the raw APV of the death benefit.
        `.schedule` is the full period-by-period breakdown, for audit and
        debugging — this is the kind of detail the pricing-run log
        (vita-setup-todo.md, Section 6) would want captured.
    """
    rates = validate_inputs(qx, lapse, propensity_to_buy, term, interest_rate, benefit_amount)

    in_force = 1.0        # probability of being in force at the START of the current period
    cum_discount = 1.0    # cumulative discount factor through the END of the current period
    total_pv = 0.0
    schedule = []

    for t in range(1, term + 1):
        q = qx[t - 1]
        l = lapse[t - 1]
        r = rates[t - 1]

        cum_discount *= 1.0 / (1.0 + r)

        expected_death_benefit = in_force * q * benefit_amount
        pv = expected_death_benefit * cum_discount
        total_pv += pv

        schedule.append(
            PeriodDetail(
                period=t,
                in_force_prob=in_force,
                qx=q,
                lapse=l,
                interest_rate=r,
                expected_death_benefit=expected_death_benefit,
                discount_factor=cum_discount,
                present_value=pv,
            )
        )

        # Update in-force probability for the NEXT period: survive death AND don't lapse.
        in_force *= (1.0 - q) * (1.0 - l)

    value = total_pv * propensity_to_buy

    return PolicyValuationResult(
        value=value,
        value_before_propensity=total_pv,
        schedule=schedule,
    )
