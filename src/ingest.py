"""Extract PE6201 source documents into page-aware retrieval chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from docx import Document
from pypdf import PdfReader


@dataclass(frozen=True)
class SourceUnit:
    source_id: str
    source_path: str
    source_name: str
    page: int | None
    unit_index: int
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_id: str
    source_path: str
    source_name: str
    page: int | None
    unit_index: int
    chunk_index: int
    text: str
    character_count: int


def normalise_text(text: str) -> str:
    """Remove extraction artefacts while preserving paragraph boundaries."""
    text = text.replace("\x00", "")
    text = text.replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    cleaned: list[str] = []
    blank = False
    for line in lines:
        if line:
            cleaned.append(line)
            blank = False
        elif cleaned and not blank:
            cleaned.append("")
            blank = True
    return "\n".join(cleaned).strip()


def extract_pdf(path: Path, source_id: str, source_path: str) -> list[SourceUnit]:
    reader = PdfReader(str(path))
    units: list[SourceUnit] = []
    for index, page in enumerate(reader.pages, start=1):
        text = normalise_text(page.extract_text() or "")
        if text:
            units.append(SourceUnit(source_id, source_path, path.name, index, index, text))
    return units


def extract_docx(path: Path, source_id: str, source_path: str) -> list[SourceUnit]:
    document = Document(str(path))
    blocks: list[str] = []
    blocks.extend(p.text for p in document.paragraphs if p.text.strip())
    for table_index, table in enumerate(document.tables, start=1):
        rows = []
        for row in table.rows:
            cells = [normalise_text(cell.text) for cell in row.cells]
            rows.append(" | ".join(cells))
        blocks.append(f"Table {table_index}\n" + "\n".join(rows))
    text = normalise_text("\n\n".join(blocks))
    return [SourceUnit(source_id, source_path, path.name, None, 1, text)] if text else []


def extract_txt(path: Path, source_id: str, source_path: str) -> list[SourceUnit]:
    text = normalise_text(path.read_text(encoding="utf-8"))
    return [SourceUnit(source_id, source_path, path.name, None, 1, text)] if text else []


def extract_source(path: Path, source_id: str, source_path: str) -> list[SourceUnit]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path, source_id, source_path)
    if suffix == ".docx":
        return extract_docx(path, source_id, source_path)
    if suffix in {".txt", ".md"}:
        return extract_txt(path, source_id, source_path)
    raise ValueError(f"Unsupported source format: {path}")


def choose_break(text: str, start: int, target_end: int, minimum_end: int) -> int:
    """Prefer a paragraph, sentence, or word boundary near the target size."""
    if target_end >= len(text):
        return len(text)
    candidates = []
    for marker in ("\n\n", ". ", "? ", "! ", "; ", " "):
        pos = text.rfind(marker, minimum_end, target_end + 1)
        if pos >= 0:
            candidates.append(pos + len(marker))
    return max(candidates) if candidates else target_end


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be at least 0 and smaller than chunk_size")
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        target_end = min(start + chunk_size, len(text))
        minimum_end = min(start + int(chunk_size * 0.65), target_end)
        end = choose_break(text, start, target_end, minimum_end)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        next_start = max(0, end - overlap)
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks


def make_chunks(units: Iterable[SourceUnit], chunk_size: int, overlap: int) -> list[Chunk]:
    output: list[Chunk] = []
    for unit in units:
        for index, text in enumerate(split_text(unit.text, chunk_size, overlap), start=1):
            identity = f"{unit.source_id}|{unit.page}|{unit.unit_index}|{index}|{text}"
            digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:12]
            output.append(
                Chunk(
                    chunk_id=f"{unit.source_id}-{digest}",
                    source_id=unit.source_id,
                    source_path=unit.source_path,
                    source_name=unit.source_name,
                    page=unit.page,
                    unit_index=unit.unit_index,
                    chunk_index=index,
                    text=text,
                    character_count=len(text),
                )
            )
    return output


def write_jsonl(path: Path, records: Iterable[Chunk]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
            count += 1
    return count


def build_corpus(manifest_path: Path, output_path: Path, chunk_size: int, overlap: int) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    configured_root = os.getenv("PE6201_SOURCE_ROOT", manifest["source_root"])
    source_root = Path(configured_root).expanduser()
    if not source_root.is_absolute():
        source_root = (manifest_path.parent / source_root).resolve()
    all_units: list[SourceUnit] = []
    source_stats: list[dict] = []

    for entry in manifest["documents"]:
        relative = entry["path"]
        absolute = source_root / relative
        if not absolute.exists():
            raise FileNotFoundError(f"Manifest source does not exist: {absolute}")
        units = extract_source(absolute, entry["id"], relative)
        chunks = make_chunks(units, chunk_size, overlap)
        all_units.extend(units)
        source_stats.append(
            {
                "source_id": entry["id"],
                "path": relative,
                "units": len(units),
                "chunks": len(chunks),
                "characters": sum(len(unit.text) for unit in units),
            }
        )

    all_chunks = make_chunks(all_units, chunk_size, overlap)
    count = write_jsonl(output_path, all_chunks)
    return {
        "output": str(output_path),
        "sources": len(source_stats),
        "units": len(all_units),
        "chunks": count,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "source_stats": source_stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stats", type=Path)
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=180)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = build_corpus(args.manifest, args.output, args.chunk_size, args.overlap)
    if args.stats:
        args.stats.parent.mkdir(parents=True, exist_ok=True)
        args.stats.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
