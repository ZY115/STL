# Package Manifest

## Purpose

This handoff package contains the durable research context required to continue the project on another computer or Codex account.

It intentionally excludes LaTeX temporary files and bulk raw trajectories. The
environment-inspection and rule-and-monitor milestones are complete. Tested
monitor code, a runnable visualization surface, and stable evidence are tracked;
wrapper and training code do not yet exist.

## Root documents

| File | Purpose |
|---|---|
| `README.md` | Project summary, current status, reading order, and immediate next step |
| `AGENTS.md` | Persistent project instructions automatically read by Codex |
| `PROJECT_CONTEXT.md` | Full reasoning history and evolution from the original end-to-end idea to Stage I |
| `DECISIONS.md` | Confirmed, open, and deferred research decisions |
| `HANDOFF_PROMPT.md` | First prompts to use with Codex on a new computer |
| `MANIFEST.md` | Description of package contents |
| `CHECKSUMS.sha256` | Integrity hashes for all packaged files |
| `environment.stage1.yml` | Exact resolved Conda and pip environment |
| `pyproject.toml` | Installable local Stage I Python package metadata |

## Project documents

| File | Purpose |
|---|---|
| `docs/PROJECT_INTRODUCTION.md` | Short Chinese and English introduction for group sharing |
| `docs/CURRENT_STAGE1_STATUS.md` | Detailed Chinese status, visualization interpretation, remaining work, and next milestone acceptance criteria |
| `docs/stage1_plan.md` | Detailed Stage I engineering plan and resource list |
| `docs/environment_setup.md` | Tested setup commands, versions, and isolation notes |
| `docs/environment_inspection.md` | Public API, distance definition, and smoke-test results |
| `docs/stage1_rule_monitor_spec.md` | Normative rule semantics, monitor contract, calibration protocol, tests, and Ubuntu work order |
| `docs/rule_calibration_report.md` | Formal calibration protocol, evidence, selected parameters, and limitations |
| `docs/monitor_agreement_report.md` | Online/oracle/RTAMT agreement result |
| `docs/visualization.md` | One-command live/video runner, outputs, verification, and limitations |
| `docs/problem-definition/safety_stl_problem_definition.pdf` | One-page formal problem definition |
| `docs/problem-definition/safety_stl_problem_definition.tex` | TeX source for the problem definition |

## Slides

| File | Purpose |
|---|---|
| `docs/slides/stage1_experiment_plan_slides.pdf` | Final 9-page staged experiment plan |
| `docs/slides/stage1_experiment_plan_slides.tex` | TeX source for the Stage I plan slides |
| `docs/slides/literature_review_three_papers_slides_6p.pdf` | Condensed 6-page literature-to-problem narrative |
| `docs/slides/literature_review_three_papers_slides_6p.tex` | TeX source for the condensed slides |
| `docs/slides/literature_review_three_papers_slides_9p.pdf` | Earlier 9-page detailed literature narrative |
| `docs/slides/literature_review_three_papers_slides_9p.tex` | TeX source for the detailed slides |

## Core papers

| File | Role |
|---|---|
| `references/papers/2023_NL2TL.pdf` | Natural language to temporal logic |
| `references/papers/2025_DeepLTL.pdf` | Executing complex LTL specifications with RL |
| `references/papers/2018_Safe_RL_via_Shielding.pdf` | Alternative runtime safety enforcement |
| `references/papers/2026_UAV_NL_STL_MILP_Repair.pdf` | NL-to-STL translation and repair in a UAV application |

## Additional literature

`references/papers/related/` contains papers gathered during the 2023-2026 novelty and feasibility review.

`references/extracted-text/` contains searchable text extracted from those papers. These files are analysis aids; the PDFs remain authoritative.

## Selected code references

`references/code-notes/` contains selected upstream files inspected during planning:

- `PPO-LTL-selected/`;
- `safety-gymnasium-selected/`.

These are reference snapshots, not project implementation code.

## Stage I implementation

| Path | Purpose |
|---|---|
| `configs/stage1_rule.yaml` | Fixed machine-readable calibrated rule |
| `scripts/collect_rule_calibration.py` | Formal controlled/random data collection and parameter selection |
| `scripts/generate_monitor_fixtures.py` | Stable environment fixture generation |
| `scripts/run_monitor_agreement.py` | Machine-readable agreement evaluation and report generation |
| `scripts/run_stage1_demo.py` | Python environment/monitor visualization entry point |
| `scripts/visualize_stage1.sh` | One-command Conda-aware launcher |
| `src/safety_stl/signals.py` | Public hazard-lidar distance extraction |
| `src/safety_stl/monitor.py` | Causal online bounded-recovery monitor |
| `src/safety_stl/oracle.py` | Independent direct enumerator and RTAMT window check |
| `src/safety_stl/visualization.py` | Live viewer, annotated video, controller, and independent logs |
| `tests/` | Signal, semantic-boundary, oracle agreement, visualization, and stable-fixture tests |

## Excluded files

The package excludes:

- `.aux`;
- `.log`;
- `.nav`;
- `.snm`;
- `.toc`;
- `.out`;
- `.fls`;
- `.fdb_latexmk`;
- `.DS_Store`;
- unrelated slide templates;
- raw generated CSV files below `results/`;
- OmniSafe wrapper and training implementation not yet completed.

## Generated outputs

`results/.gitignore` keeps raw generated CSV trajectories out of the
research-document history. The local environment inspection produced CSV and
MP4 files under `results/environment_inspection/`. Git retains the two compact
MP4 renderings, the directory README, and the JSON summary. The summary includes
statistics and SHA-256 hashes for both tracked videos and ignored raw CSV
artifacts.

The formal calibration adds `results/rule_calibration/summary.json`, which
contains candidate statistics and hashes for 60 ignored raw trajectories. The
agreement milestone tracks `results/monitor_agreement/summary.json` and three
minimal fixtures under `tests/fixtures/`. The visualization runner tracks one
compact annotated MP4, its summary, and a README under
`results/visualization/`; regenerated trajectory CSV files remain ignored.

## Future additions

The rule-and-monitor completion gate has passed. The next bounded addition is
the OmniSafe cost wrapper and a small integration smoke test. Main training
configuration/results wait for predeclared quantitative success criteria;
language-layer code remains deferred beyond Stage I.
