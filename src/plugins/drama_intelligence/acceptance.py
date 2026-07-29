from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence


class DramaSearchService(Protocol):
    workspace: str

    def status(self) -> dict[str, Any]: ...

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        drama_id: str | None = None,
        chunk_type: str | None = None,
    ) -> dict[str, Any]: ...


class DramaAcceptanceError(ValueError):
    """Raised when an acceptance dataset cannot produce trustworthy metrics."""


_RETRIEVAL_EXPECTATION_KEYS = (
    "drama_ids",
    "drama_titles",
    "source_refs",
    "source_ref_prefixes",
    "contains_any",
    "contains_all",
)


def _as_strings(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    for item in values:
        clean = " ".join(str(item or "").split())
        if clean and clean not in result:
            result.append(clean)
    return result


def _as_ints(value: Any) -> list[int]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[int] = []
    for item in values:
        try:
            number = int(item)
        except (TypeError, ValueError) as exc:
            raise DramaAcceptanceError(f"Invalid integer label: {item!r}") from exc
        if number not in result:
            result.append(number)
    return result


def _normalize_question(raw: Mapping[str, Any], *, line_number: int) -> dict[str, Any]:
    question_id = " ".join(str(raw.get("id") or f"q{line_number:04d}").split())
    query = " ".join(str(raw.get("query") or "").split())
    if not query:
        raise DramaAcceptanceError(f"Question {question_id!r} has an empty query")

    expected_raw = raw.get("expected")
    if not isinstance(expected_raw, Mapping):
        raise DramaAcceptanceError(f"Question {question_id!r} must contain an expected object")

    expected = {
        "drama_ids": _as_strings(expected_raw.get("drama_ids") or expected_raw.get("drama_id")),
        "drama_titles": _as_strings(
            expected_raw.get("drama_titles") or expected_raw.get("drama_title")
        ),
        "source_refs": _as_strings(expected_raw.get("source_refs") or expected_raw.get("source_ref")),
        "source_ref_prefixes": _as_strings(expected_raw.get("source_ref_prefixes")),
        "contains_any": _as_strings(expected_raw.get("contains_any")),
        "contains_all": _as_strings(expected_raw.get("contains_all")),
        "characters": _as_strings(expected_raw.get("characters")),
        "episode_numbers": _as_ints(
            expected_raw.get("episode_numbers") or expected_raw.get("episode_number")
        ),
    }
    if not any(expected[key] for key in _RETRIEVAL_EXPECTATION_KEYS):
        raise DramaAcceptanceError(
            f"Question {question_id!r} needs at least one retrieval label "
            f"({', '.join(_RETRIEVAL_EXPECTATION_KEYS)})"
        )

    try:
        limit = min(max(int(raw.get("limit", 5)), 1), 50)
    except (TypeError, ValueError) as exc:
        raise DramaAcceptanceError(f"Question {question_id!r} has an invalid limit") from exc

    drama_filter = " ".join(str(raw.get("drama_id") or "").split()) or None
    chunk_type = " ".join(str(raw.get("chunk_type") or "").split()) or None
    return {
        "id": question_id,
        "query": query,
        "limit": limit,
        "drama_id": drama_filter,
        "chunk_type": chunk_type,
        "expected": expected,
    }


def load_acceptance_questions(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path).expanduser().resolve(strict=True)
    if not source.is_file():
        raise DramaAcceptanceError(f"Acceptance dataset is not a file: {source}")

    questions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise DramaAcceptanceError(
                f"Invalid JSON on line {line_number}: {exc.msg}"
            ) from exc
        if not isinstance(raw, Mapping):
            raise DramaAcceptanceError(f"Line {line_number} must contain a JSON object")
        question = _normalize_question(raw, line_number=line_number)
        if question["id"] in seen_ids:
            raise DramaAcceptanceError(f"Duplicate question id: {question['id']}")
        seen_ids.add(question["id"])
        questions.append(question)

    if not questions:
        raise DramaAcceptanceError(f"No acceptance questions found in: {source}")
    return questions


def _haystack(result: Mapping[str, Any]) -> str:
    values = [
        result.get("text"),
        result.get("heading"),
        result.get("drama_title"),
        result.get("source_ref"),
    ]
    return "\n".join(str(value or "") for value in values)


def _retrieval_match(result: Mapping[str, Any], expected: Mapping[str, Sequence[Any]]) -> bool:
    drama_id = str(result.get("drama_id") or "")
    drama_title = str(result.get("drama_title") or "")
    source_ref = str(result.get("source_ref") or "")
    haystack = _haystack(result)

    drama_ids = list(expected.get("drama_ids") or [])
    if drama_ids and drama_id not in drama_ids:
        return False
    drama_titles = list(expected.get("drama_titles") or [])
    if drama_titles and drama_title not in drama_titles:
        return False
    source_refs = list(expected.get("source_refs") or [])
    if source_refs and source_ref not in source_refs:
        return False
    source_prefixes = list(expected.get("source_ref_prefixes") or [])
    if source_prefixes and not any(source_ref.startswith(prefix) for prefix in source_prefixes):
        return False
    contains_all = list(expected.get("contains_all") or [])
    if contains_all and not all(term in haystack for term in contains_all):
        return False
    contains_any = list(expected.get("contains_any") or [])
    if contains_any and not any(term in haystack for term in contains_any):
        return False
    return True


def _citation_valid(result: Mapping[str, Any]) -> bool:
    citation = result.get("citation")
    if not isinstance(citation, Mapping):
        return False
    locator = citation.get("source_locator")
    return bool(
        citation.get("source_ref")
        and citation.get("normalized_path")
        and isinstance(locator, Mapping)
        and locator.get("locator")
    )


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return round(float(ordered[rank - 1]), 3)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def run_acceptance(
    service: DramaSearchService,
    questions: Iterable[Mapping[str, Any]],
    *,
    minimum_dramas: int = 10,
    minimum_questions: int = 100,
    retrieval_target: float = 0.85,
    character_target: float = 0.90,
    episode_target: float = 0.85,
) -> dict[str, Any]:
    normalized = [
        _normalize_question(item, line_number=index)
        for index, item in enumerate(questions, start=1)
    ]
    if not normalized:
        raise DramaAcceptanceError("Acceptance question list is empty")

    status = service.status()
    structured = status.get("structured") if isinstance(status, Mapping) else {}
    drama_count = int((structured or {}).get("dramas") or 0)
    details: list[dict[str, Any]] = []
    latencies: list[float] = []
    retrieval_hits = 0
    top1_hits = 0
    citation_hits = 0
    character_labeled = 0
    character_correct = 0
    episode_labeled = 0
    episode_correct = 0

    started = datetime.now(timezone.utc)
    for question in normalized:
        before = time.perf_counter()
        response = service.search(
            question["query"],
            limit=question["limit"],
            drama_id=question["drama_id"],
            chunk_type=question["chunk_type"],
        )
        latency_ms = round((time.perf_counter() - before) * 1000, 3)
        latencies.append(latency_ms)
        results = list(response.get("results") or [])

        matched_rank = None
        matched: Mapping[str, Any] | None = None
        for rank, result in enumerate(results, start=1):
            if isinstance(result, Mapping) and _retrieval_match(result, question["expected"]):
                matched_rank = rank
                matched = result
                break

        hit = matched is not None
        retrieval_hits += int(hit)
        top1_hits += int(matched_rank == 1)
        citation_ok = bool(matched and _citation_valid(matched))
        citation_hits += int(citation_ok)

        expected_characters = list(question["expected"]["characters"])
        character_ok: bool | None = None
        if expected_characters:
            character_labeled += 1
            actual_characters = {
                str(value) for value in ((matched or {}).get("characters") or []) if str(value)
            }
            character_ok = bool(hit and set(expected_characters).issubset(actual_characters))
            character_correct += int(character_ok)

        expected_episodes = list(question["expected"]["episode_numbers"])
        episode_ok: bool | None = None
        if expected_episodes:
            episode_labeled += 1
            try:
                actual_episode = int((matched or {}).get("episode_number"))
            except (TypeError, ValueError):
                actual_episode = None
            episode_ok = bool(hit and actual_episode in expected_episodes)
            episode_correct += int(episode_ok)

        warnings = response.get("warnings") or []
        warning_codes = [
            str(item.get("code"))
            for item in warnings
            if isinstance(item, Mapping) and item.get("code")
        ]
        details.append(
            {
                "id": question["id"],
                "query": question["query"],
                "limit": question["limit"],
                "latency_ms": latency_ms,
                "retrieval_hit": hit,
                "top1_hit": matched_rank == 1,
                "matched_rank": matched_rank,
                "matched_chunk_id": (matched or {}).get("chunk_id"),
                "matched_drama_id": (matched or {}).get("drama_id"),
                "matched_source_ref": (matched or {}).get("source_ref"),
                "citation_valid": citation_ok,
                "character_correct": character_ok,
                "episode_correct": episode_ok,
                "warning_codes": warning_codes,
            }
        )

    retrieval_rate = _ratio(retrieval_hits, len(normalized))
    top1_rate = _ratio(top1_hits, len(normalized))
    citation_rate = _ratio(citation_hits, len(normalized))
    character_rate = _ratio(character_correct, character_labeled)
    episode_rate = _ratio(episode_correct, episode_labeled)

    gates = {
        "minimum_dramas": drama_count >= int(minimum_dramas),
        "minimum_questions": len(normalized) >= int(minimum_questions),
        "retrieval_accuracy": bool(
            retrieval_rate is not None and retrieval_rate >= float(retrieval_target)
        ),
        "character_accuracy": bool(
            character_rate is not None and character_rate >= float(character_target)
        ),
        "episode_event_accuracy": bool(
            episode_rate is not None and episode_rate >= float(episode_target)
        ),
    }
    finished = datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "workspace": str(getattr(service, "workspace", status.get("workspace", "unknown"))),
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "dataset": {
            "question_count": len(normalized),
            "fingerprint": hashlib.sha256(
                json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "character_labeled": character_labeled,
            "episode_labeled": episode_labeled,
        },
        "corpus": {
            "drama_count": drama_count,
            "revision": (structured or {}).get("revision") or status.get("revision"),
            "semantic_state": status.get("semantic"),
        },
        "targets": {
            "minimum_dramas": int(minimum_dramas),
            "minimum_questions": int(minimum_questions),
            "retrieval_accuracy": float(retrieval_target),
            "character_accuracy": float(character_target),
            "episode_event_accuracy": float(episode_target),
        },
        "metrics": {
            "retrieval_hits": retrieval_hits,
            "retrieval_accuracy": retrieval_rate,
            "top1_accuracy": top1_rate,
            "citation_accuracy": citation_rate,
            "character_correct": character_correct,
            "character_accuracy": character_rate,
            "episode_correct": episode_correct,
            "episode_event_accuracy": episode_rate,
            "latency_ms": {
                "mean": round(statistics.fmean(latencies), 3) if latencies else None,
                "p50": _percentile(latencies, 0.50),
                "p95": _percentile(latencies, 0.95),
                "max": round(max(latencies), 3) if latencies else None,
            },
        },
        "gates": gates,
        "overall_pass": all(gates.values()),
        "questions": details,
    }


def write_acceptance_report(
    report: Mapping[str, Any],
    output_directory: str | Path,
) -> dict[str, str]:
    output = Path(output_directory).expanduser().resolve(strict=False)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output / f"drama-acceptance-{stamp}.json"
    markdown_path = output / f"drama-acceptance-{stamp}.md"

    json_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    temporary_json = json_path.with_suffix(".json.tmp")
    temporary_json.write_text(json_text, encoding="utf-8")
    temporary_json.replace(json_path)

    metrics = report.get("metrics") or {}
    gates = report.get("gates") or {}
    dataset = report.get("dataset") or {}
    corpus = report.get("corpus") or {}
    latency = metrics.get("latency_ms") or {}
    lines = [
        "# Drama Memory Owner-Data Acceptance",
        "",
        f"- Workspace: `{report.get('workspace')}`",
        f"- Overall: `{'PASS' if report.get('overall_pass') else 'FAIL'}`",
        f"- Drama count: `{corpus.get('drama_count')}`",
        f"- Question count: `{dataset.get('question_count')}`",
        f"- Dataset fingerprint: `{dataset.get('fingerprint')}`",
        "",
        "## Metrics",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Retrieval accuracy | `{metrics.get('retrieval_accuracy')}` |",
        f"| Top-1 accuracy | `{metrics.get('top1_accuracy')}` |",
        f"| Citation accuracy | `{metrics.get('citation_accuracy')}` |",
        f"| Character accuracy | `{metrics.get('character_accuracy')}` |",
        f"| Episode-event accuracy | `{metrics.get('episode_event_accuracy')}` |",
        f"| Search latency p50 | `{latency.get('p50')} ms` |",
        f"| Search latency p95 | `{latency.get('p95')} ms` |",
        f"| Search latency max | `{latency.get('max')} ms` |",
        "",
        "## Gates",
        "",
    ]
    for name, passed in gates.items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    failed = [item for item in report.get("questions") or [] if not item.get("retrieval_hit")]
    lines.extend(
        [
            "",
            "## Failed retrieval questions",
            "",
        ]
    )
    if failed:
        for item in failed:
            lines.append(f"- `{item.get('id')}` {item.get('query')}")
    else:
        lines.append("- None")

    temporary_markdown = markdown_path.with_suffix(".md.tmp")
    temporary_markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary_markdown.replace(markdown_path)
    return {"json": str(json_path), "markdown": str(markdown_path)}
