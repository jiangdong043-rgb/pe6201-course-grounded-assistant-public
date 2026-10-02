"""Semantic and BM25+semantic hybrid retrieval for the PE6201 corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

from retrieval import BM25Index, SearchHit, evaluate, load_jsonl, reciprocal_rank


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class SemanticIndex:
    def __init__(
        self,
        chunks: list[dict],
        model_name: str = DEFAULT_MODEL,
        cache_path: Path | None = None,
    ):
        self.chunks = chunks
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)
        if cache_path and cache_path.exists():
            cached = np.load(cache_path, allow_pickle=False)
            self.embeddings = cached["embeddings"]
            if len(self.embeddings) != len(chunks):
                raise ValueError("Embedding cache does not match the chunk corpus")
        else:
            self.embeddings = np.asarray(
                list(self.model.embed([chunk["text"] for chunk in chunks])), dtype=np.float32
            )
            self.embeddings = self._normalise(self.embeddings)
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(cache_path, embeddings=self.embeddings)

    @staticmethod
    def _normalise(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        query_vector = np.asarray(list(self.model.query_embed([query])), dtype=np.float32)
        query_vector = self._normalise(query_vector)[0]
        scores = self.embeddings @ query_vector
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [
            SearchHit(rank=rank, score=float(scores[index]), chunk=self.chunks[int(index)])
            for rank, index in enumerate(order, start=1)
        ]


class HybridIndex:
    """Reciprocal-rank fusion of BM25 and semantic rankings."""

    def __init__(self, bm25: BM25Index, semantic: SemanticIndex, rrf_k: int = 60):
        self.bm25 = bm25
        self.semantic = semantic
        self.rrf_k = rrf_k
        self.chunks = bm25.chunks

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        candidate_k = min(max(top_k * 5, 20), len(self.chunks))
        rankings = [
            self.bm25.search(query, candidate_k),
            self.semantic.search(query, candidate_k),
        ]
        fused: dict[str, float] = {}
        chunks: dict[str, dict] = {}
        for ranking in rankings:
            for hit in ranking:
                chunk_id = hit.chunk["chunk_id"]
                fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (self.rrf_k + hit.rank)
                chunks[chunk_id] = hit.chunk
        ordered = sorted(fused.items(), key=lambda item: (-item[1], item[0]))[:top_k]
        return [
            SearchHit(rank=rank, score=score, chunk=chunks[chunk_id])
            for rank, (chunk_id, score) in enumerate(ordered, start=1)
        ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--eval", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chunks = load_jsonl(args.chunks)
    cases = json.loads(args.eval.read_text(encoding="utf-8"))["cases"]
    semantic = SemanticIndex(chunks, model_name=args.model, cache_path=args.cache)
    bm25 = BM25Index(chunks)
    hybrid = HybridIndex(bm25, semantic)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = {
        "semantic": evaluate(semantic, cases, args.top_k),
        "hybrid": evaluate(hybrid, cases, args.top_k),
    }
    for name, result in results.items():
        result["retriever"] = name
        result["embedding_model"] = args.model
        path = args.output_dir / f"{name}_dev_top{args.top_k}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        name: {
            "hits": result["hits"],
            "cases": result["cases"],
            "recall_at_k": result["recall_at_k"],
            "mrr": result["mrr"],
            "misses": [row["id"] for row in result["results"] if not row["hit_at_k"]],
        }
        for name, result in results.items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
