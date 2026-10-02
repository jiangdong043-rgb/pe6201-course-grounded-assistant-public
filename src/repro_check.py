"""Run offline reproducibility and repository-safety checks."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{32,}"),
]


def result(name: str, ok: bool, detail: str) -> dict:
    return {"check": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def scan_secrets(project: Path) -> list[Path]:
    findings: list[Path] = []
    ignored_parts = {".git", ".venv", "venv", "__pycache__"}
    ignored_suffixes = {".npz", ".png", ".pdf", ".docx", ".pyc"}
    for path in project.rglob("*"):
        if not path.is_file() or ignored_parts.intersection(path.parts) or path.suffix.lower() in ignored_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            findings.append(path.relative_to(project))
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--require-derived-data", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    checks: list[dict] = []

    checks.append(result("Python version", sys.version_info >= (3, 10), sys.version.split()[0]))
    for module in ("docx", "pypdf", "fastembed"):
        checks.append(result(f"Dependency {module}", importlib.util.find_spec(module) is not None, "installed" if importlib.util.find_spec(module) else "missing"))

    required = [
        "config/model_settings.json",
        "config/retrieval_settings.json",
        "config/source_manifest.json",
        "data/evaluation_40.json",
        "src/ingest.py",
        "src/generation.py",
        "src/run_experiment.py",
    ]
    missing = [path for path in required if not (project / path).exists()]
    checks.append(result("Required repository files", not missing, "all present" if not missing else f"missing: {missing}"))

    evaluation = json.loads((project / "data/evaluation_40.json").read_text(encoding="utf-8"))
    cases = evaluation.get("cases", [])
    categories = Counter(case.get("category") for case in cases)
    expected_categories = {"requirements", "deadlines", "submission_information", "concepts"}
    eval_ok = len(cases) == 40 and set(categories) == expected_categories and all(categories[name] == 10 for name in expected_categories)
    checks.append(result("Frozen evaluation", eval_ok, f"{len(cases)} cases; {dict(sorted(categories.items()))}"))

    manifest = json.loads((project / "config/source_manifest.json").read_text(encoding="utf-8"))
    portable = not Path(manifest["source_root"]).is_absolute()
    checks.append(result("Portable source root", portable, manifest["source_root"]))

    derived = [
        project / "data/processed/chunks_700.jsonl",
        project / "data/processed/bge_small_embeddings_700.npz",
    ]
    derived_present = all(path.exists() for path in derived)
    checks.append(result("Derived retrieval data", derived_present or not args.require_derived_data, "present" if derived_present else "not included; rebuild from authorised sources"))

    formal = project / "results/formal/raw_vs_rag_results.jsonl"
    if formal.exists():
        rows = [json.loads(line) for line in formal.read_text(encoding="utf-8").splitlines() if line.strip()]
        pairs = Counter((row.get("case_id"), row.get("condition")) for row in rows)
        formal_ok = len(rows) == 80 and len(pairs) == 80 and all(count == 1 for count in pairs.values())
        checks.append(result("Formal experiment records", formal_ok, f"{len(rows)} unique condition records"))
    else:
        checks.append(result("Formal experiment records", True, "not included; can be regenerated"))

    secret_files = scan_secrets(project)
    checks.append(result("Committed API-key scan", not secret_files, "no key-like strings found" if not secret_files else f"review: {[str(p) for p in secret_files]}"))

    failed = [check for check in checks if check["status"] == "FAIL"]
    payload = {"project": str(project), "checks": checks, "passed": len(checks) - len(failed), "failed": len(failed)}
    print(json.dumps(payload, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
