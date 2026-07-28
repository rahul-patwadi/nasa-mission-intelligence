"""Retrieval-quality evaluation harness: two-layer, human-labeled precision@5.

Layer 1: for each eval question in scripts/eval_questions.json, run retrieval
through the existing query path (embed_chunks + vectorstore.query) and print
the top-K chunks (snippet, record_id, mission) as a readable report.

Layer 2: relevance labels are persisted per question in
scripts/eval_questions.json, keyed by Chroma's own chunk id
(f"{record_id}-{chunk_index}"), which stays stable across an
embedding-dimensionality change since chunking itself is untouched (see ADR
0006). precision@5 is computed only from those human labels. Any retrieved
chunk id with no stored label is scaffolded into the file as null and
reported as NEEDS LABEL -- it is excluded from the metric, never silently
scored as wrong.

The keyword/mission heuristic is a secondary, clearly-marked approximate
sanity check ("approx" column) -- it plays no part in the reported
precision@5.

Run from the repo root with:
    uv run python -m scripts.evaluate_retrieval

Then open scripts/eval_questions.json, fill in true/false for any null
labels, and re-run to get a real precision@5.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, cast

from app.core.embeddings import embed_chunks
from app.core.vectorstore import query as vectorstore_query

TOP_K = 5
QUESTIONS_PATH = Path(__file__).parent / "eval_questions.json"

logger = logging.getLogger(__name__)


def _load_questions() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads(QUESTIONS_PATH.read_text()))


def _save_questions(questions: list[dict[str, Any]]) -> None:
    QUESTIONS_PATH.write_text(json.dumps(questions, indent=2) + "\n")


def _approx_relevant(chunk: dict[str, Any], question: dict[str, Any]) -> bool:
    """Secondary, approximate sanity check only -- keyword + mission match."""
    expected_mission = question.get("expected_mission")
    if expected_mission and chunk["mission"] != expected_mission:
        return False
    keywords = question.get("expected_keywords") or []
    if not keywords:
        return True
    text_lower = chunk["text"].lower()
    return any(keyword.lower() in text_lower for keyword in keywords)


async def _run_question(question: dict[str, Any]) -> dict[str, Any]:
    [embedded] = await embed_chunks([{"text": question["question"]}])
    chunks = vectorstore_query(
        embedded["embedding"],
        mission_filter=question.get("mission_filter"),
        top_k=TOP_K,
    )

    labels = question.setdefault("labels", {})
    rows = []
    for chunk in chunks:
        chunk_id = f"{chunk['record_id']}-{chunk['chunk_index']}"
        if chunk_id not in labels:
            labels[chunk_id] = None  # scaffold for hand-labeling
        rows.append(
            {
                "chunk_id": chunk_id,
                "record_id": chunk["record_id"],
                "mission": chunk["mission"],
                "snippet": chunk["text"][:150].replace("\n", " "),
                "label": labels[chunk_id],
                "approx_relevant": _approx_relevant(chunk, question),
            }
        )

    labeled_rows = [row for row in rows if row["label"] is not None]
    precision_at_5 = (
        sum(1 for row in labeled_rows if row["label"]) / len(labeled_rows) if labeled_rows else None
    )

    return {
        "id": question["id"],
        "question": question["question"],
        "note": question.get("note", ""),
        "rows": rows,
        "labeled_count": len(labeled_rows),
        "precision_at_5": precision_at_5,
    }


def _print_report(result: dict[str, Any]) -> None:
    print(f"\n=== {result['id']} ===")
    print(f"Q: {result['question']}")
    if result["note"]:
        print(f"Expected: {result['note']}")
    print(f"{'#':<3}{'label':<13}{'approx':<10}{'mission':<10}{'record_id':<12}snippet")
    for i, row in enumerate(result["rows"], start=1):
        if row["label"] is None:
            label_str = "NEEDS LABEL"
        else:
            label_str = "relevant" if row["label"] else "not relevant"
        approx_str = "(match)" if row["approx_relevant"] else "(no match)"
        print(
            f"{i:<3}{label_str:<13}{approx_str:<10}{row['mission']:<10}"
            f"{row['record_id']!s:<12}{row['snippet']}"
        )
    if result["precision_at_5"] is None:
        print(f"precision@5: no labels yet ({result['labeled_count']}/{TOP_K} labeled)")
    else:
        print(
            f"precision@5: {result['precision_at_5']:.2f} ({result['labeled_count']}/{TOP_K} labeled)"
        )


async def run() -> None:
    questions = _load_questions()
    results = [await _run_question(question) for question in questions]
    for result in results:
        _print_report(result)

    _save_questions(questions)  # persist any newly-scaffolded NEEDS LABEL entries

    scored = [r for r in results if r["precision_at_5"] is not None]
    unlabeled_total = sum(TOP_K - r["labeled_count"] for r in results)

    print("\n=== summary ===")
    print(f"questions: {len(results)}")
    print(f"questions with at least one label: {len(scored)}")
    if scored:
        mean_precision = sum(r["precision_at_5"] for r in scored) / len(scored)
        print(f"mean precision@5 (over labeled questions): {mean_precision:.2f}")
    else:
        print("mean precision@5: no labeled questions yet")
    print(f"chunks needing labels this run: {unlabeled_total}")
    print(
        f"labels are stored in {QUESTIONS_PATH} -- fill in true/false for any null entries, then re-run."
    )


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())


if __name__ == "__main__":
    main()
