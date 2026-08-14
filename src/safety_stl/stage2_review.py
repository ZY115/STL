"""Human-review packet rendering for the frozen Stage II specification registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping


CHECKS = (
    "object",
    "signal",
    "operator",
    "comparator",
    "threshold",
    "deadline",
    "equality",
    "terminal_semantics",
    "paraphrase_equivalence",
)


def _read(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _compact_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def render_review_packet(root: Path) -> str:
    """Render all not-yet-approved records without asserting human judgment."""

    specifications: List[Dict[str, Any]] = _read(root / "specifications.json")
    reviews = {record["spec_id"]: record for record in _read(root / "reviews.json")}
    pending = [
        record
        for record in specifications
        if reviews[record["spec_id"]]["status"] != "approved"
    ]
    reviewer_counts: Dict[str, int] = {}
    for review in reviews.values():
        if review["status"] == "approved":
            reviewer = str(review["reviewer"])
            reviewer_counts[reviewer] = reviewer_counts.get(reviewer, 0) + 1
    reviewer_summary = ", ".join(
        f"{reviewer}: {count}" for reviewer, count in sorted(reviewer_counts.items())
    )
    lines = [
        "# Stage II v0 Independent Human Review Packet",
        "",
        "- Generated from the frozen D37 specification registry.",
        f"- Records in this packet: **{len(pending)} pending / {len(specifications)} total**.",
        f"- Current approved-review provenance: {reviewer_summary}.",
        "- The reviewer must be a named human different from `annotation_author`.",
        "- This packet contains specifications only; it does not release held-out trace labels.",
        "- Record decisions in `reviews.json`; do not edit Gold semantics silently.",
        "",
        "For each record, check all nine fields and add an adjudication note for every disagreement.",
        "The owner selected a prospective parameter amendment for the six known logical aliases.",
        "Any specification changed by that amendment returns to pending review automatically.",
        "",
    ]
    for index, spec in enumerate(pending, start=1):
        review = reviews[spec["spec_id"]]
        lines.extend(
            [
                f"## {index}. `{spec['spec_id']}` — {spec['formula_family']} / {spec['split']}",
                "",
                f"- Author: `{spec['annotation_author']}`",
                f"- Online status: `{spec['online_use_status']}`",
                f"- Canonical: {spec['canonical_natural_language']}",
                f"- Paraphrase 1: {spec['paraphrases'][0]}",
                f"- Paraphrase 2: {spec['paraphrases'][1]}",
                f"- Gold STL: `{spec['gold_stl']}`",
                f"- Parameters: `{_compact_json(spec['parameter_values'])}`",
                f"- Typed AST: `{_compact_json(spec['typed_ast'])}`",
                "",
                "Checklist:",
                "",
            ],
        )
        for check in CHECKS:
            marker = "x" if review["checks"][check] is True else " "
            lines.append(f"- [{marker}] {check}")
        lines.extend(
            [
                "",
                "Reviewer name: ____________________",
                "",
                "Decision (`approved` / `changes_required`): ____________________",
                "",
                "Disagreement/adjudication notes: ________________________________________________",
                "",
            ],
        )
    return "\n".join(lines).rstrip() + "\n"


__all__ = ["CHECKS", "render_review_packet"]
