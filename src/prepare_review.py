"""Create an A/B-labelled review template and aggregate supplied judgements.

Reviewer identity and effective blinding cannot be established by this script.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


REVIEW_FIELDS = [
    "case_id",
    "category",
    "condition_blind",
    "question",
    "expected_answer",
    "model_answer",
    "expected_source_id",
    "model_citations",
    "expected_abstention",
    "model_abstained",
    "answer_score",
    "citation_score",
    "review_notes",
]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def condition_code(case_id: str, condition: str) -> str:
    """Deterministically alternate labels so the reviewer does not see raw/RAG."""
    case_number = int(case_id.split("-")[-1])
    raw_is_a = case_number % 2 == 1
    if condition == "raw":
        return "A" if raw_is_a else "B"
    return "B" if raw_is_a else "A"


def prepare(results_path: Path, output_path: Path) -> None:
    rows = read_jsonl(results_path)
    review_rows = []
    for row in rows:
        review_rows.append(
            {
                "case_id": row["case_id"],
                "category": row["category"],
                "condition_blind": condition_code(row["case_id"], row["condition"]),
                "question": row["question"],
                "expected_answer": row["expected_answer"],
                "model_answer": row["answer"],
                "expected_source_id": row["expected_source_id"],
                "model_citations": " | ".join(row["cited_sources"]),
                "expected_abstention": row["expected_abstention"],
                "model_abstained": row["abstained"],
                "answer_score": "",
                "citation_score": "",
                "review_notes": "",
            }
        )
    review_rows.sort(key=lambda row: (row["case_id"], row["condition_blind"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(review_rows)


def decode_condition(case_id: str, blind: str) -> str:
    case_number = int(case_id.split("-")[-1])
    raw_is_a = case_number % 2 == 1
    if blind == "A":
        return "raw" if raw_is_a else "rag"
    return "rag" if raw_is_a else "raw"


def aggregate(review_path: Path, output_path: Path) -> None:
    with review_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    totals = defaultdict(lambda: {"reviewed": 0, "answer_correct": 0, "citation_correct": 0})
    categories = defaultdict(
        lambda: defaultdict(lambda: {"reviewed": 0, "answer_correct": 0, "citation_correct": 0})
    )
    for row in rows:
        if row["answer_score"] not in {"0", "1"} or row["citation_score"] not in {"0", "1"}:
            continue
        condition = decode_condition(row["case_id"], row["condition_blind"])
        answer_score = int(row["answer_score"])
        citation_score = int(row["citation_score"])
        for bucket in (totals[condition], categories[condition][row["category"]]):
            bucket["reviewed"] += 1
            bucket["answer_correct"] += answer_score
            bucket["citation_correct"] += citation_score
    payload = {
        "scoring": "Supplied binary judgements: 1 correct, 0 incorrect. Reviewer identity and effective blinding are not established by A/B labels.",
        "overall": dict(totals),
        "by_category": {condition: dict(value) for condition, value in categories.items()},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--results", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    score = subparsers.add_parser("aggregate")
    score.add_argument("--review", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "create":
        prepare(args.results, args.output)
    else:
        aggregate(args.review, args.output)


if __name__ == "__main__":
    main()
