"""Run and resume paired raw-versus-RAG PE6201 experiments."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from generation import OpenRouterClient, build_retriever, load_json, run_condition


def load_completed(path: Path) -> dict[tuple[str, str], dict]:
    if not path.exists():
        return {}
    completed = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        completed[(row["case_id"], row["condition"])] = row
    return completed


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def summarise(rows: list[dict], model_settings: dict) -> dict:
    summary = {
        "model": model_settings["model"],
        "price_checked_on": model_settings["price_checked_on"],
        "conditions": {},
    }
    for condition in ("raw", "rag"):
        selected = [row for row in rows if row["condition"] == condition]
        if not selected:
            continue
        calls = len(selected)
        prompt_tokens = sum(row["prompt_tokens"] for row in selected)
        completion_tokens = sum(row["completion_tokens"] for row in selected)
        total_cost = sum(row["cost_usd"] for row in selected)
        latencies = sorted(row["latency_seconds"] for row in selected)
        p95_index = max(0, min(len(latencies) - 1, int(0.95 * len(latencies)) - 1))
        summary["conditions"][condition] = {
            "calls": calls,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_cost_usd": total_cost,
            "average_cost_per_question_usd": total_cost / calls,
            "projected_cost_per_1000_questions_usd": total_cost / calls * 1000,
            "average_latency_seconds": sum(latencies) / calls,
            "p95_latency_seconds": latencies[p95_index],
            "abstentions": sum(bool(row["abstained"]) for row in selected),
        }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--eval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--pause-seconds", type=float, default=0.5)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project = args.project.resolve()
    model_settings = load_json(project / "config/model_settings.json")
    retrieval_settings = load_json(project / "config/retrieval_settings.json")
    evaluation = load_json(args.eval)
    cases = evaluation["cases"]
    if args.case_id:
        wanted = set(args.case_id)
        cases = [case for case in cases if case["id"] in wanted]
    if args.limit is not None:
        cases = cases[: args.limit]

    if args.overwrite and args.output.exists():
        args.output.unlink()
    completed = load_completed(args.output)
    client = OpenRouterClient(model_settings)
    retriever = build_retriever(project, retrieval_settings)

    for case in cases:
        for condition in ("raw", "rag"):
            key = (case["id"], condition)
            if key in completed:
                print(f"skip {case['id']} {condition}: already completed")
                continue
            print(f"run  {case['id']} {condition}")
            result = run_condition(
                client,
                model_settings,
                case["question"],
                condition,
                retriever=retriever,
                top_k=retrieval_settings["top_k"],
            )
            row = {
                "case_id": case["id"],
                "category": case["category"],
                "expected_answer": case["expected_answer"],
                "required_facts": case["required_facts"],
                "expected_source_id": case["source_id"],
                "expected_page": case.get("source_page"),
                "expected_abstention": case["should_abstain"],
                **asdict(result),
            }
            append_jsonl(args.output, row)
            completed[key] = row
            if args.pause_seconds:
                time.sleep(args.pause_seconds)

    rows = list(load_completed(args.output).values())
    summary = summarise(rows, model_settings)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
