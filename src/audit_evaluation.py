"""Static quality audit for the frozen PE6201 evaluation set."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REQUIRED_FIELDS = {
    "id",
    "category",
    "question",
    "expected_answer",
    "required_facts",
    "source_id",
    "source_page",
    "should_abstain",
}
EXPECTED_CATEGORIES = {
    "requirements": "REQ-",
    "deadlines": "DDL-",
    "submission_information": "SUB-",
    "concepts": "CON-",
}


def normalised_words(text: str) -> set[str]:
    return {word.strip(".,:;!?()[]{}\"'").lower() for word in text.split() if word.strip()}


def jaccard(a: str, b: str) -> float:
    left, right = normalised_words(a), normalised_words(b)
    return len(left & right) / len(left | right) if left | right else 0.0


def audit(project: Path, evaluation_path: Path) -> dict:
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    manifest = json.loads((project / "config/source_manifest.json").read_text(encoding="utf-8"))
    cases = evaluation["cases"]
    source_ids = {entry["id"] for entry in manifest["documents"]}
    errors: list[str] = []
    warnings: list[str] = []

    if len(cases) != 40:
        errors.append(f"Expected 40 cases, found {len(cases)}")
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("Case IDs are not unique")

    counts = Counter(case.get("category") for case in cases)
    for category, prefix in EXPECTED_CATEGORIES.items():
        if counts[category] != 10:
            errors.append(f"{category} has {counts[category]} cases instead of 10")
        for case in cases:
            if case.get("category") == category and not str(case.get("id", "")).startswith(prefix):
                errors.append(f"{case.get('id')} has the wrong prefix for {category}")

    for case in cases:
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            errors.append(f"{case.get('id')} missing fields: {sorted(missing)}")
        if case.get("source_id") not in source_ids:
            errors.append(f"{case.get('id')} uses unknown source {case.get('source_id')}")
        if not case.get("question", "").strip().endswith("?"):
            warnings.append(f"{case.get('id')} question does not end in a question mark")
        if not case.get("expected_answer", "").strip():
            errors.append(f"{case.get('id')} has an empty expected answer")
        if not case.get("required_facts"):
            errors.append(f"{case.get('id')} has no required facts")

    near_duplicates = []
    for index, first in enumerate(cases):
        for second in cases[index + 1 :]:
            similarity = jaccard(first["question"], second["question"])
            if similarity >= 0.72:
                near_duplicates.append(
                    {"first": first["id"], "second": second["id"], "similarity": round(similarity, 3)}
                )
    if near_duplicates:
        warnings.append(f"Found {len(near_duplicates)} possible near-duplicate question pairs")

    abstentions = [case["id"] for case in cases if case["should_abstain"]]
    if len(abstentions) < 2:
        warnings.append("Fewer than two expected-abstention cases")

    return {
        "evaluation_name": evaluation.get("name"),
        "version": evaluation.get("version"),
        "status": evaluation.get("status"),
        "case_count": len(cases),
        "category_counts": dict(sorted(counts.items())),
        "unique_ids": len(set(ids)),
        "source_count": len({case["source_id"] for case in cases}),
        "expected_abstention_cases": abstentions,
        "near_duplicates": near_duplicates,
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--eval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = audit(args.project, args.eval)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
