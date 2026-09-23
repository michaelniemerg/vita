"""
run_from_csv.py

Loads the two input files and runs value_policy() for each policy row.

durational_assumptions.csv — shared basis, one row per duration:
    duration          : 1, 2, 3, ... with no gaps or duplicates
    qx                : mortality rate for that duration
    persistency_rate  : probability of REMAINING in force through that
                         duration (i.e., 1 - lapse rate). Stored as
                         persistency rather than lapse because that's the
                         more common way this kind of table is actually
                         published; converted to lapse internally, since
                         that's what value_policy() takes.
    interest_rate     : that duration's own one-period discount rate
                         (allows a simple yield curve, not just a flat
                         rate — value_policy() supports both).

policy_assumptions.csv — one row per policy being valued:
    policy_id         : identifier, for reporting only
    term              : how many durations of the shared basis to use
    propensity_to_buy : passed straight through to value_policy()
    face_amount       : passed straight through as benefit_amount

A policy's term can be shorter than the durational file's full length
(it uses the first `term` rows), but not longer — there's no assumption
data past what's in the file.
"""

import csv
import sys
from dataclasses import dataclass
from typing import Dict, List

from policy_valuation import PolicyValuationError, value_policy


class CSVLoadError(ValueError):
    """Raised when either input file fails validation."""


@dataclass
class DurationRow:
    duration: int
    qx: float
    persistency_rate: float
    interest_rate: float


@dataclass
class PolicyRow:
    policy_id: str
    term: int
    propensity_to_buy: float
    face_amount: float


def _parse_float(value, field_name, row_label, errors):
    try:
        return float(value)
    except (TypeError, ValueError):
        errors.append(f"{row_label}: {field_name} = {value!r} is not a number")
        return None


def load_durational_assumptions(path: str) -> List[DurationRow]:
    errors = []
    rows: List[DurationRow] = []
    seen_durations = set()

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"duration", "qx", "persistency_rate", "interest_rate"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise CSVLoadError(
                f"{path}: missing required column(s): {sorted(missing)}"
            )

        for i, raw in enumerate(reader, start=2):  # start=2: row 1 is the header
            row_label = f"{path}, row {i}"

            try:
                duration = int(raw["duration"])
            except (TypeError, ValueError):
                errors.append(f"{row_label}: duration = {raw['duration']!r} is not an integer")
                continue

            if duration in seen_durations:
                errors.append(f"{row_label}: duplicate duration {duration}")
            seen_durations.add(duration)

            qx = _parse_float(raw["qx"], "qx", row_label, errors)
            persistency = _parse_float(raw["persistency_rate"], "persistency_rate", row_label, errors)
            rate = _parse_float(raw["interest_rate"], "interest_rate", row_label, errors)

            if persistency is not None and not (0.0 <= persistency <= 1.0):
                errors.append(f"{row_label}: persistency_rate = {persistency} is outside [0, 1]")

            if None not in (qx, persistency, rate):
                rows.append(DurationRow(duration=duration, qx=qx, persistency_rate=persistency, interest_rate=rate))

    rows.sort(key=lambda r: r.duration)
    expected = list(range(1, len(rows) + 1))
    actual = [r.duration for r in rows]
    if actual != expected:
        errors.append(
            f"{path}: durations must be contiguous starting at 1 with no gaps — "
            f"found {actual}, expected {expected}"
        )

    if errors:
        raise CSVLoadError(f"Invalid durational assumptions file:\n- " + "\n- ".join(errors))

    return rows


def load_policy_assumptions(path: str) -> List[PolicyRow]:
    errors = []
    rows: List[PolicyRow] = []
    seen_ids = set()

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"policy_id", "term", "propensity_to_buy", "face_amount"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise CSVLoadError(
                f"{path}: missing required column(s): {sorted(missing)}"
            )

        for i, raw in enumerate(reader, start=2):
            row_label = f"{path}, row {i} (policy_id={raw.get('policy_id')!r})"
            policy_id = raw["policy_id"]

            if not policy_id:
                errors.append(f"{row_label}: policy_id is empty")
            elif policy_id in seen_ids:
                errors.append(f"{row_label}: duplicate policy_id {policy_id!r}")
            seen_ids.add(policy_id)

            try:
                term = int(raw["term"])
                if term <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"{row_label}: term = {raw['term']!r} is not a positive integer")
                term = None

            propensity = _parse_float(raw["propensity_to_buy"], "propensity_to_buy", row_label, errors)
            face_amount = _parse_float(raw["face_amount"], "face_amount", row_label, errors)

            if None not in (term, propensity, face_amount):
                rows.append(PolicyRow(policy_id=policy_id, term=term,
                                       propensity_to_buy=propensity, face_amount=face_amount))

    if errors:
        raise CSVLoadError(f"Invalid policy assumptions file:\n- " + "\n- ".join(errors))

    return rows


def run(durational_path: str, policy_path: str):
    durational = load_durational_assumptions(durational_path)
    policies = load_policy_assumptions(policy_path)

    max_duration = len(durational)
    results = []

    for policy in policies:
        if policy.term > max_duration:
            raise CSVLoadError(
                f"Policy {policy.policy_id!r} has term={policy.term}, but "
                f"{durational_path} only has {max_duration} duration(s) of assumptions"
            )

        basis = durational[: policy.term]
        qx = [d.qx for d in basis]
        lapse = [1.0 - d.persistency_rate for d in basis]
        interest_rate = [d.interest_rate for d in basis]

        try:
            result = value_policy(
                qx=qx,
                lapse=lapse,
                propensity_to_buy=policy.propensity_to_buy,
                term=policy.term,
                interest_rate=interest_rate,
                benefit_amount=policy.face_amount,
            )
        except PolicyValuationError as e:
            raise CSVLoadError(f"Policy {policy.policy_id!r} failed valuation: {e}")

        results.append((policy, result))

    return results


if __name__ == "__main__":
    durational_path = sys.argv[1] if len(sys.argv) > 1 else "durational_assumptions.csv"
    policy_path = sys.argv[2] if len(sys.argv) > 2 else "policy_assumptions.csv"

    results = run(durational_path, policy_path)

    print(f"{'policy_id':<10} {'term':>4} {'propensity':>10} {'face_amount':>12} {'value':>14}")
    print("-" * 56)
    for policy, result in results:
        print(
            f"{policy.policy_id:<10} {policy.term:>4} {policy.propensity_to_buy:>10.2f} "
            f"{policy.face_amount:>12,.0f} {result.value:>14,.2f}"
        )
