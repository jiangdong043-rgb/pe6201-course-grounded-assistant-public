"""Dependency-free BM25 retrieval for the PE6201 chunk corpus."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@dataclass(frozen=True)
class SearchHit:
    rank: int
    score: float
    chunk: dict


class BM25Index:
    """Small-corpus Okapi BM25 index with deterministic ranking."""

    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        if not chunks:
            raise ValueError("Cannot build an index from an empty corpus")
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.term_frequencies: list[Counter[str]] = []
        self.document_frequencies: Counter[str] = Counter()
        self.document_lengths: list[int] = []

        for chunk in chunks:
            terms = tokenize(chunk["text"])
            counts = Counter(terms)
            self.term_frequencies.append(counts)
            self.document_lengths.append(len(terms))
            self.document_frequencies.update(counts.keys())

        self.document_count = len(chunks)
        self.average_document_length = sum(self.document_lengths) / self.document_count

    def inverse_document_frequency(self, term: str) -> float:
        frequency = self.document_frequencies.get(term, 0)
        return math.log(1.0 + (self.document_count - frequency + 0.5) / (frequency + 0.5))

    def score(self, query: str, document_index: int) -> float:
        query_terms = Counter(tokenize(query))
        term_counts = self.term_frequencies[document_index]
        document_length = self.document_lengths[document_index]
        normalisation = self.k1 * (
            1.0 - self.b + self.b * document_length / self.average_document_length
        )
        score = 0.0
        for term, query_frequency in query_terms.items():
            frequency = term_counts.get(term, 0)
            if frequency == 0:
                continue
            numerator = frequency * (self.k1 + 1.0)
            denominator = frequency + normalisation
            score += self.inverse_document_frequency(term) * numerator / denominator
            score *= 1.0 + math.log(query_frequency)
        return score

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        scored = [(self.score(query, index), index) for index in range(self.document_count)]
        scored = [(score, index) for score, index in scored if score > 0]
        scored.sort(key=lambda item: (-item[0], self.chunks[item[1]]["chunk_id"]))
        return [
            SearchHit(rank=rank, score=score, chunk=self.chunks[index])
            for rank, (score, index) in enumerate(scored[:top_k], start=1)
        ]


def reciprocal_rank(
    hits: Iterable[SearchHit], source_id: str, pages: list[int] | None
) -> float:
    for hit in hits:
        source_matches = hit.chunk["source_id"] == source_id
        page_matches = pages is None or hit.chunk["page"] in pages
        if source_matches and page_matches:
            return 1.0 / hit.rank
    return 0.0


def evaluate(index: BM25Index, cases: list[dict], top_k: int) -> dict:
    rows = []
    category_totals: defaultdict[str, dict[str, float]] = defaultdict(
        lambda: {"cases": 0, "hits": 0, "reciprocal_rank_sum": 0.0}
    )

    for case in cases:
        hits = index.search(case["question"], top_k=top_k)
        expected_pages = case.get("expected_pages")
        if expected_pages is None and case.get("expected_page") is not None:
            expected_pages = [case["expected_page"]]
        rr = reciprocal_rank(hits, case["expected_source_id"], expected_pages)
        is_hit = rr > 0
        stats = category_totals[case["category"]]
        stats["cases"] += 1
        stats["hits"] += int(is_hit)
        stats["reciprocal_rank_sum"] += rr
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "expected_source_id": case["expected_source_id"],
                "expected_page": case.get("expected_page"),
                "expected_pages": expected_pages,
                "hit_at_k": is_hit,
                "reciprocal_rank": rr,
                "hits": [
                    {
                        "rank": hit.rank,
                        "score": round(hit.score, 6),
                        "chunk_id": hit.chunk["chunk_id"],
                        "source_id": hit.chunk["source_id"],
                        "page": hit.chunk["page"],
                        "preview": " ".join(hit.chunk["text"].split())[:300],
                    }
                    for hit in hits
                ],
            }
        )

    total = len(cases)
    hits = sum(row["hit_at_k"] for row in rows)
    reciprocal_rank_sum = sum(row["reciprocal_rank"] for row in rows)
    category_summary = {}
    for category, stats in sorted(category_totals.items()):
        count = int(stats["cases"])
        category_summary[category] = {
            "cases": count,
            "hits": int(stats["hits"]),
            "recall_at_k": stats["hits"] / count if count else 0.0,
            "mrr": stats["reciprocal_rank_sum"] / count if count else 0.0,
        }

    return {
        "retriever": "okapi_bm25",
        "top_k": top_k,
        "cases": total,
        "hits": hits,
        "recall_at_k": hits / total if total else 0.0,
        "mrr": reciprocal_rank_sum / total if total else 0.0,
        "by_category": category_summary,
        "results": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--eval", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chunks = load_jsonl(args.chunks)
    index = BM25Index(chunks)

    if args.query:
        hits = index.search(args.query, top_k=args.top_k)
        payload = [
            {
                "rank": hit.rank,
                "score": round(hit.score, 6),
                **hit.chunk,
            }
            for hit in hits
        ]
    elif args.eval:
        cases = json.loads(args.eval.read_text(encoding="utf-8"))["cases"]
        payload = evaluate(index, cases, args.top_k)
    else:
        raise SystemExit("Provide either --query or --eval")

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
