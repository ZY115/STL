"""Frozen D37 Stage II v0 specification matrix and typed-AST compiler."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple


SIGNAL_ID = "nearest_hazard_center_distance_public"
AUTHOR = "Codex_stage2_draft_2026-08-12"

RECOVERY_PARAMETERS: Tuple[Tuple[float, float, int, int], ...] = (
    (0.45, 0.55, 79, 20),
    (0.35, 0.50, 40, 10),
    (0.40, 0.60, 60, 15),
    (0.50, 0.65, 90, 20),
    (0.55, 0.75, 100, 25),
    (0.30, 0.45, 30, 10),
    (0.40, 0.55, 80, 15),
    (0.50, 0.70, 60, 20),
)
AVOIDANCE_PARAMETERS: Tuple[Tuple[float, int], ...] = (
    (0.20, 20),
    (0.25, 30),
    (0.30, 40),
    (0.35, 50),
    (0.40, 60),
    (0.45, 80),
    (0.50, 100),
    (0.55, 120),
)
FAMILY_PREFIXES = ("br", "rp", "ba", "and", "or")
FAMILY_NAMES = {
    "br": "hysteretic_bounded_recovery",
    "rp": "recovery_plus_persistence",
    "ba": "bounded_avoidance",
    "and": "conjunction",
    "or": "disjunction",
}

_PRESERVED_BR_LANGUAGE: Dict[int, Tuple[str, Tuple[str, str]]] = {
    1: (
        "Whenever the agent enters closer than 0.45 simulator units to the nearest hazard, it must reach at least 0.55 units away within 79 environment steps.",
        (
            "After entering the nearest-hazard warning zone below 0.45 units, recover to a distance of 0.55 units or more no later than 79 steps.",
            "If a new warning episode begins because nearest-hazard distance falls under 0.45, return to at least 0.55 within the next 79 environment steps, including the deadline step.",
        ),
    ),
    2: (
        "Whenever the agent enters closer than 0.35 simulator units to the nearest hazard, it must reach at least 0.50 units away within 40 environment steps.",
        (
            "After nearest-hazard distance drops below 0.35 units, recover to 0.50 units or farther within 40 steps.",
            "A new warning episode under 0.35 must be followed by recovery to at least 0.50 by the inclusive 40-step deadline.",
        ),
    ),
    3: (
        "Whenever the agent enters closer than 0.40 simulator units to the nearest hazard, it must reach at least 0.60 units away within 60 environment steps.",
        (
            "When nearest-hazard distance first becomes less than 0.40 units, regain a distance of 0.60 units or more within 60 steps.",
            "Every new below-0.40 warning episode requires recovery to at least 0.60 by its inclusive 60-step deadline.",
        ),
    ),
    4: (
        "Whenever the agent enters closer than 0.50 simulator units to the nearest hazard, it must reach at least 0.65 units away within 90 environment steps.",
        (
            "After a new nearest-hazard warning below 0.50 units, move back to 0.65 units or farther within 90 steps.",
            "If distance to the nearest hazard falls under 0.50 while no warning is active, recover to at least 0.65 by the inclusive 90-step deadline.",
        ),
    ),
    5: (
        "Whenever the agent enters closer than 0.55 simulator units to the nearest hazard, it must reach at least 0.75 units away within 100 environment steps.",
        (
            "When a new warning begins below 0.55 units from the nearest hazard, recover to 0.75 units or farther within 100 steps.",
            "Each new nearest-hazard entry under 0.55 requires reaching at least 0.75 by the inclusive 100-environment-step deadline.",
        ),
    ),
}


def _number(value: float) -> str:
    return format(float(value), ".15g")


def predicate(comparator: str, threshold: float) -> Dict[str, Any]:
    if comparator not in {"lt", "ge"}:
        raise ValueError(f"unsupported predicate comparator: {comparator}")
    return {
        "node_type": "predicate",
        "signal_id": SIGNAL_ID,
        "comparator": comparator,
        "threshold": float(threshold),
    }


def warning_entry(threshold: float) -> Dict[str, Any]:
    return {
        "node_type": "warning_entry",
        "predicate": predicate("lt", threshold),
        "trigger_mode": "hysteretic_warning_episode",
    }


def bounded_recovery_ast(d_warn: float, d_safe: float, deadline: int) -> Dict[str, Any]:
    return {
        "node_type": "globally",
        "interval": None,
        "child": {
            "node_type": "implies",
            "left": warning_entry(d_warn),
            "right": {
                "node_type": "eventually",
                "interval": {"lower": 0, "upper": int(deadline), "inclusive": True},
                "child": predicate("ge", d_safe),
            },
        },
    }


def recovery_persistence_ast(
    d_warn: float,
    d_safe: float,
    deadline: int,
    persistence: int,
) -> Dict[str, Any]:
    ast = bounded_recovery_ast(d_warn, d_safe, deadline)
    eventually = ast["child"]["right"]
    eventually["child"] = {
        "node_type": "globally",
        "interval": {"lower": 0, "upper": int(persistence), "inclusive": True},
        "child": predicate("ge", d_safe),
    }
    return ast


def bounded_avoidance_ast(threshold: float, horizon: int) -> Dict[str, Any]:
    return {
        "node_type": "globally",
        "interval": {"lower": 0, "upper": int(horizon), "inclusive": True},
        "child": predicate("ge", threshold),
    }


def boolean_ast(operator: str, left: Mapping[str, Any], right: Mapping[str, Any]) -> Dict[str, Any]:
    if operator not in {"and", "or"}:
        raise ValueError(f"unsupported Boolean operator: {operator}")
    return {"node_type": operator, "left": dict(left), "right": dict(right)}


def compile_typed_ast(ast: Mapping[str, Any]) -> str:
    """Compile the closed D37 typed fragment to one canonical STL string."""

    node_type = ast.get("node_type")
    if node_type == "predicate":
        if ast.get("signal_id") != SIGNAL_ID or ast.get("comparator") not in {"lt", "ge"}:
            raise ValueError("invalid typed predicate")
        symbol = "<" if ast["comparator"] == "lt" else ">="
        return f"d {symbol} {_number(float(ast['threshold']))}"
    if node_type == "warning_entry":
        if ast.get("trigger_mode") != "hysteretic_warning_episode":
            raise ValueError("invalid warning-entry trigger mode")
        return f"e({compile_typed_ast(ast['predicate'])})"
    if node_type in {"eventually", "globally"}:
        interval = ast.get("interval")
        operator = "F" if node_type == "eventually" else "G"
        if interval is None:
            if node_type != "globally":
                raise ValueError("only global always may omit an interval")
            return f"G({compile_typed_ast(ast['child'])})"
        if set(interval) != {"lower", "upper", "inclusive"}:
            raise ValueError("invalid temporal interval fields")
        if interval["lower"] != 0 or interval["inclusive"] is not True:
            raise ValueError("D37 requires inclusive intervals beginning at zero")
        upper = interval["upper"]
        if isinstance(upper, bool) or not isinstance(upper, int) or upper <= 0:
            raise ValueError("temporal upper bound must be a positive integer")
        return f"{operator}_[0,{upper}]({compile_typed_ast(ast['child'])})"
    if node_type == "implies":
        return f"{compile_typed_ast(ast['left'])} -> {compile_typed_ast(ast['right'])}"
    if node_type in {"and", "or"}:
        symbol = "AND" if node_type == "and" else "OR"
        return (
            f"({compile_typed_ast(ast['left'])}) {symbol} "
            f"({compile_typed_ast(ast['right'])})"
        )
    raise ValueError(f"unsupported typed-AST node: {node_type!r}")


def _split(prefix: str, index: int) -> str:
    if prefix == "or":
        return "structure_test"
    if index <= 5:
        return "train"
    if index <= 7:
        return "validation"
    return "parameter_test"


def _language(prefix: str, index: int) -> Tuple[str, Tuple[str, str]]:
    d_warn, d_safe, deadline, persistence = RECOVERY_PARAMETERS[index - 1]
    avoidance, avoidance_horizon = AVOIDANCE_PARAMETERS[index - 1]
    warn = f"{d_warn:.2f}"
    safe = f"{d_safe:.2f}"
    avoid = f"{avoidance:.2f}"
    if prefix == "br" and index in _PRESERVED_BR_LANGUAGE:
        return _PRESERVED_BR_LANGUAGE[index]
    if prefix == "br":
        return (
            f"Whenever the agent newly enters closer than {warn} simulator units to the nearest hazard, it must reach at least {safe} units away within {deadline} environment steps, including the deadline.",
            (
                f"After a new nearest-hazard warning below {warn} units, recover to {safe} units or farther no later than {deadline} steps afterward.",
                f"Each inactive-to-warning entry with nearest-hazard distance under {warn} requires a return to at least {safe} by the inclusive {deadline}-step deadline.",
            ),
        )
    if prefix == "rp":
        return (
            f"Whenever the agent newly enters closer than {warn} simulator units to the nearest hazard, it must start within {deadline} environment steps a period that stays at least {safe} units away through the following {persistence} steps, with both bounds inclusive.",
            (
                f"After each new below-{warn} nearest-hazard warning, begin no later than {deadline} steps afterward an uninterrupted interval from its start through {persistence} further steps at distance {safe} or greater.",
                f"A warning entry under {warn} must be followed within the inclusive {deadline}-step window by recovery to at least {safe}, maintained for the inclusive duration from 0 to {persistence} steps.",
            ),
        )
    if prefix == "ba":
        return (
            f"From environment step 0 through step {avoidance_horizon}, inclusive, the agent must always remain at least {avoid} simulator units from the nearest hazard.",
            (
                f"Keep nearest-hazard distance at {avoid} units or greater at every sample in the inclusive interval from step 0 to step {avoidance_horizon}.",
                f"During the first bounded interval [0,{avoidance_horizon}] in environment steps, never let the distance to the nearest hazard fall below {avoid} simulator units.",
            ),
        )
    connective = "both" if prefix == "and" else "at least one of"
    word = "and" if prefix == "and" else "or"
    canonical = (
        f"The trajectory must satisfy {connective} these complete requirements: "
        f"(A) every new entry below {warn} units from the nearest hazard is followed by recovery to at least {safe} within {deadline} steps, including the deadline; {word} "
        f"(B) nearest-hazard distance remains at least {avoid} units at every step from 0 through {avoidance_horizon}, inclusive."
    )
    paraphrase_one = (
        f"Require {'both clauses together' if prefix == 'and' else 'one complete clause or the other'}: "
        f"(A) a new below-{warn} warning recovers to {safe} or farther by {deadline} inclusive steps, {word} "
        f"(B) all samples in [0,{avoidance_horizon}] stay at least {avoid} units from the nearest hazard."
    )
    paraphrase_two = (
        f"The full bounded-recovery rule (warning under {warn}, safety at {safe}, deadline {deadline}) "
        f"{word} the full bounded-avoidance rule (distance at least {avoid} throughout inclusive steps 0 to {avoidance_horizon}) "
        f"must {'both hold' if prefix == 'and' else 'have at least one branch hold'}."
    )
    return canonical, (paraphrase_one, paraphrase_two)


def _grounding(prefix: str) -> Dict[str, Any]:
    value: Dict[str, Any] = {
        "object": "nearest_hazard",
        "signal_id": SIGNAL_ID,
        "distance_unit": "simulator_length_unit",
        "time_unit": "environment_step",
        "finite_trace_terminal_semantics": "unresolved_obligations_are_positive_gold_events",
    }
    if prefix in {"br", "rp", "and", "or"}:
        value.update(
            {
                "warning_comparator": "lt",
                "recovery_comparator": "ge",
                "trigger_mode": "hysteretic_warning_episode",
                "deadline_inclusive": True,
            },
        )
    if prefix in {"ba", "and", "or"}:
        value.update({"avoidance_comparator": "ge", "avoidance_interval_inclusive": True})
    if prefix == "rp":
        value["persistence_interval_inclusive"] = True
    if prefix in {"and", "or"}:
        value["boolean_scope"] = "complete_formula_branches"
    return value


def build_specifications() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for prefix in FAMILY_PREFIXES:
        for index in range(1, 9):
            d_warn, d_safe, deadline, persistence = RECOVERY_PARAMETERS[index - 1]
            avoidance, avoidance_horizon = AVOIDANCE_PARAMETERS[index - 1]
            recovery_ast = bounded_recovery_ast(d_warn, d_safe, deadline)
            avoidance_ast = bounded_avoidance_ast(avoidance, avoidance_horizon)
            if prefix == "br":
                ast = recovery_ast
                parameters = {
                    "d_warn": d_warn,
                    "d_safe": d_safe,
                    "deadline_steps": deadline,
                }
            elif prefix == "rp":
                ast = recovery_persistence_ast(d_warn, d_safe, deadline, persistence)
                parameters = {
                    "d_warn": d_warn,
                    "d_safe": d_safe,
                    "deadline_steps": deadline,
                    "persistence_steps": persistence,
                }
            elif prefix == "ba":
                ast = avoidance_ast
                parameters = {
                    "avoidance_threshold": avoidance,
                    "avoidance_horizon_steps": avoidance_horizon,
                }
            else:
                ast = boolean_ast(prefix, recovery_ast, avoidance_ast)
                parameters = {
                    "d_warn": d_warn,
                    "d_safe": d_safe,
                    "deadline_steps": deadline,
                    "avoidance_threshold": avoidance,
                    "avoidance_horizon_steps": avoidance_horizon,
                }
            canonical, paraphrases = _language(prefix, index)
            spec_id = f"{prefix}-v0-{index:03d}"
            preserved = prefix == "br" and index <= 5
            records.append(
                {
                    "spec_id": spec_id,
                    "canonical_natural_language": canonical,
                    "paraphrases": list(paraphrases),
                    "typed_ast": ast,
                    "gold_stl": compile_typed_ast(ast),
                    "formula_family": FAMILY_NAMES[prefix],
                    "grounding_schema": _grounding(prefix),
                    "parameter_values": parameters,
                    "semantic_pair_id": f"{spec_id}__language-equivalence",
                    "contrast_group_id": f"d37-index-{index:03d}",
                    "semantic_contrast_type": (
                        "stage1_calibrated_reference"
                        if prefix == "br" and index == 1
                        else "frozen_parameter_or_structure_contrast"
                    ),
                    "allowed_online_use": prefix == "br" and index == 1,
                    "online_use_status": (
                        "stage1_calibrated_online"
                        if prefix == "br" and index == 1
                        else "offline_only_pending_feasibility"
                    ),
                    "split": _split(prefix, index),
                    "annotation_author": (
                        "project_draft_2026-08-12" if preserved else AUTHOR
                    ),
                    "independent_reviewer": "Yuhang" if preserved else None,
                    "review_status": (
                        "independently_reviewed"
                        if preserved
                        else "machine_validated_pending_independent_review"
                    ),
                    "source_or_generation_record": (
                        "D36 Stage II v0 foundation; preserved D37 review record"
                        if preserved
                        else "D37 frozen matrix implemented from STAGE2_CONTINUOUS_WORK_ORDER"
                    ),
                },
            )
    return records


def build_review_records(specifications: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    preserved_time = "2026-08-12T21:38:22-07:00"
    base_check_names = (
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
    records = []
    for spec in specifications:
        preserved = str(spec["spec_id"]) in {f"br-v0-{index:03d}" for index in range(1, 6)}
        records.append(
            {
                "spec_id": spec["spec_id"],
                "reviewer": "Yuhang" if preserved else None,
                "status": "approved" if preserved else "pending",
                "checks": {
                    name: True if preserved else None for name in base_check_names
                },
                "disagreement_notes": None,
                "reviewed_at": preserved_time if preserved else None,
            },
        )
    return records


__all__ = [
    "AVOIDANCE_PARAMETERS",
    "FAMILY_NAMES",
    "FAMILY_PREFIXES",
    "RECOVERY_PARAMETERS",
    "SIGNAL_ID",
    "bounded_avoidance_ast",
    "bounded_recovery_ast",
    "build_review_records",
    "build_specifications",
    "compile_typed_ast",
    "recovery_persistence_ast",
]
