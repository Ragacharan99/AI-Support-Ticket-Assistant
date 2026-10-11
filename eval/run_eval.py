"""Run a real-provider evaluation; this module is intentionally excluded from pytest."""

import json
import time
from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path

from app.services.ai_analyzer import AnalysisError, analyze_ticket

EVAL_DIR = Path(__file__).parent
RESULTS_PATH = EVAL_DIR / "results.json"
URGENCY_LEVELS = {"low": 0, "medium": 1, "high": 2, "critical": 3}
# These eight tickets are never represented in the system prompt and are the
# default scorecard. Keep them out of prompt-development decisions.
HOLDOUT_IDS = {6, 11, 16, 17, 21, 24, 26, 28}


def percent(numerator: int, denominator: int) -> float:
    return round((numerator / denominator * 100) if denominator else 0.0, 2)


def build_report(results: list[dict]) -> tuple[dict, list[dict]]:
    """Calculate metrics from completed tickets, including failed API calls."""
    category_totals = defaultdict(int)
    category_correct = defaultdict(int)
    category_hits = urgency_hits = urgency_near_hits = failures = 0

    for result in results:
        category = result["expected_category"]
        category_totals[category] += 1
        category_hits += result["category_correct"]
        urgency_hits += result["urgency_correct"]
        urgency_near_hits += result["urgency_within_one"]
        failures += "error" in result
        if result["category_correct"]:
            category_correct[category] += 1

    total = len(results)
    breakdown = {
        category: {
            "total": category_totals[category],
            "correct": category_correct[category],
            "accuracy": percent(category_correct[category], category_totals[category]),
        }
        for category in sorted(category_totals)
    }
    metrics = {
        "completed": total,
        "category_accuracy": percent(category_hits, total),
        "urgency_exact_match_accuracy": percent(urgency_hits, total),
        "urgency_within_one_level_accuracy": percent(urgency_near_hits, total),
        "failure_count": failures,
        "per_category": breakdown,
    }
    misclassified = [
        result for result in results if not result["category_correct"] or not result["urgency_correct"]
    ]
    return metrics, misclassified


def save_results(results: list[dict]) -> None:
    """Checkpoint all completed work so interruption never loses prior calls."""
    metrics, _ = build_report(results)
    RESULTS_PATH.write_text(json.dumps({"metrics": metrics, "results": results}, indent=2), encoding="utf-8")


def print_report(results: list[dict]) -> None:
    """Print metrics and every non-exact result for the completed subset."""
    metrics, misclassified = build_report(results)
    print(f"Completed: {metrics['completed']}")
    print(f"Category accuracy: {metrics['category_accuracy']}%")
    print(f"Urgency exact-match accuracy: {metrics['urgency_exact_match_accuracy']}%")
    print(f"Urgency within-one-level accuracy: {metrics['urgency_within_one_level_accuracy']}%")
    print(f"Failures: {metrics['failure_count']}")
    print("Per-category breakdown:")
    for category, values in metrics["per_category"].items():
        print(f"  {category}: {values['correct']}/{values['total']} ({values['accuracy']}%)")
    print("Misclassified tickets:")
    for result in misclassified:
        print(
            f"  {result['id']}: expected ({result['expected_category']}, {result['expected_urgency']}), "
            f"got ({result['got_category']}, {result['got_urgency']})"
        )


def main() -> None:
    parser = ArgumentParser(description="Evaluate ticket classification with the configured real AI provider.")
    parser.add_argument(
        "--include-development",
        action="store_true",
        help="Run all 30 tickets instead of the eight-ticket holdout scorecard.",
    )
    args = parser.parse_args()
    all_tickets = json.loads((EVAL_DIR / "tickets.json").read_text(encoding="utf-8"))
    tickets = all_tickets if args.include_development else [ticket for ticket in all_tickets if ticket["id"] in HOLDOUT_IDS]
    dataset_name = "all tickets" if args.include_development else "holdout"
    results: list[dict] = []

    print(f"Running {dataset_name} evaluation ({len(tickets)} tickets).", flush=True)

    try:
        for index, ticket in enumerate(tickets, start=1):
            print(f"[{index}/{len(tickets)}] analyzing: {ticket['subject']}...", flush=True)
            result = {
                "id": ticket["id"],
                "expected_category": ticket["expected_category"],
                "expected_urgency": ticket["expected_urgency"],
            }
            try:
                analysis = analyze_ticket(ticket["subject"], ticket["body"])
                is_category_correct = analysis.category == ticket["expected_category"]
                is_urgency_correct = analysis.urgency == ticket["expected_urgency"]
                is_urgency_near = (
                    abs(URGENCY_LEVELS[analysis.urgency] - URGENCY_LEVELS[ticket["expected_urgency"]]) <= 1
                )
                result.update(
                    {
                        "got_category": analysis.category,
                        "got_urgency": analysis.urgency,
                        "category_correct": is_category_correct,
                        "urgency_correct": is_urgency_correct,
                        "urgency_within_one": is_urgency_near,
                    }
                )
                print(f"  result: {analysis.category}, {analysis.urgency}", flush=True)
            except AnalysisError as exc:
                result.update(
                    {
                        "got_category": None,
                        "got_urgency": None,
                        "category_correct": False,
                        "urgency_correct": False,
                        "urgency_within_one": False,
                        "error": str(exc),
                    }
                )
                print(f"  failure: {exc}", flush=True)

            results.append(result)
            save_results(results)
            if index < len(tickets):
                time.sleep(1)
    except KeyboardInterrupt:
        save_results(results)
        print("\nInterrupted; results through the last completed ticket were saved.", flush=True)

    print_report(results)


if __name__ == "__main__":
    main()
