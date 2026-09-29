"""Transparent threshold-based bottleneck and automation ranking rules."""

from __future__ import annotations

from .miner import HONESTY_BOUNDARY

WAIT_THRESHOLD_MINUTES = 10.0
QUEUE_THRESHOLD = 2.0
SUITABILITY_TERMS = (
    "payment_validation",
    "shipping_label_creation",
    "invoice_data_entry",
    "address_validation",
    "email_notification",
)
SCORING_FORMULA = (
    "score = 0.35 * repetition + 0.25 * manual_actor_share + "
    "0.20 * duration_factor + 0.20 * rule_suitability"
)


def find_bottlenecks(graph: dict) -> dict:
    findings = []
    for activity, metrics in graph["activities"].items():
        wait = metrics["median_wait_minutes"]
        queue = metrics["mean_queue_length"]
        if wait >= WAIT_THRESHOLD_MINUTES or queue >= QUEUE_THRESHOLD:
            impact = max(wait / WAIT_THRESHOLD_MINUTES, queue / QUEUE_THRESHOLD)
            evidence = []
            if wait >= WAIT_THRESHOLD_MINUTES:
                evidence.append("median_wait_minutes")
            if queue >= QUEUE_THRESHOLD:
                evidence.append("mean_queue_length")
            findings.append({
                "activity": activity,
                "impact_score": round(impact, 3),
                "median_wait_minutes": wait,
                "mean_queue_length": queue,
                "max_queue_length": metrics["max_queue_length"],
                "evidence_fields": evidence,
                "evidence_pointer": f"graph.activities.{activity}",
            })
    findings.sort(key=lambda row: (-row["impact_score"], row["activity"]))
    return {
        "honesty_boundary": graph.get("honesty_boundary", HONESTY_BOUNDARY),
        "thresholds": {
            "median_wait_minutes_gte": WAIT_THRESHOLD_MINUTES,
            "mean_queue_length_gte": QUEUE_THRESHOLD,
            "impact_score": "max(median_wait_minutes / 10, mean_queue_length / 2)",
        },
        "findings": findings,
    }


def score_targets(graph: dict) -> dict:
    activities = graph["activities"]
    max_count = max((metrics["event_count"] for metrics in activities.values()), default=1)
    max_duration = max((metrics["median_duration_minutes"] for metrics in activities.values()), default=0)
    ranking = []
    for activity, metrics in activities.items():
        repetition = metrics["event_count"] / max_count
        manual_share = metrics["manual_actor_share"]
        duration_factor = metrics["median_duration_minutes"] / max_duration if max_duration else 0.0
        rule_suitability = float(any(term in activity.lower() for term in SUITABILITY_TERMS))
        score = 0.35 * repetition + 0.25 * manual_share + 0.20 * duration_factor + 0.20 * rule_suitability
        ranking.append({
            "activity": activity,
            "score": round(score, 4),
            "rank": 0,
            "inputs": {
                "event_count": metrics["event_count"],
                "repetition": round(repetition, 4),
                "manual_actor_share": manual_share,
                "median_duration_minutes": metrics["median_duration_minutes"],
                "duration_factor": round(duration_factor, 4),
                "rule_suitability": rule_suitability,
                "suitability_terms_matched": [term for term in SUITABILITY_TERMS if term in activity.lower()],
            },
        })
    ranking.sort(key=lambda row: (-row["score"], row["activity"]))
    for index, row in enumerate(ranking, start=1):
        row["rank"] = index
    return {
        "honesty_boundary": graph.get("honesty_boundary", HONESTY_BOUNDARY),
        "formula": SCORING_FORMULA,
        "weights": {
            "repetition": 0.35,
            "manual_actor_share": 0.25,
            "duration_factor": 0.20,
            "rule_suitability": 0.20,
        },
        "rule_suitability_terms": list(SUITABILITY_TERMS),
        "ranking": ranking,
    }
