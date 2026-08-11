# Package Manifest

## Purpose

This handoff package contains the durable research context required to continue the project on another computer or Codex account.

It intentionally excludes LaTeX temporary files and bulk raw trajectories. The
environment-inspection, rule-and-monitor, visualization, and OmniSafe-wrapper
integration milestones are complete. Tested monitor/wrapper code, runnable
visualization, and stable smoke evidence are tracked; main training has not
started.

## Root documents

| File | Purpose |
|---|---|
| `README.md` | Project summary, current status, reading order, and immediate next step |
| `AGENTS.md` | Persistent project instructions automatically read by Codex |
| `PROJECT_CONTEXT.md` | Full reasoning history and evolution from the original end-to-end idea to Stage I |
| `DECISIONS.md` | Confirmed, open, and deferred research decisions |
| `EXPERIMENT_PROGRESS_CHANGELOG.md` | Standalone Chinese engineering progress and modification history without raw experiment data |
| `HANDOFF_PROMPT.md` | First prompts to use with Codex on a new computer |
| `MANIFEST.md` | Description of package contents |
| `CHECKSUMS.sha256` | Integrity hashes for all packaged files |
| `environment.stage1.yml` | Exact resolved Conda and pip environment |
| `pyproject.toml` | Installable local Stage I Python package metadata |

## Project documents

| File | Purpose |
|---|---|
| `docs/PROJECT_INTRODUCTION.md` | Short Chinese and English introduction for group sharing |
| `docs/END_TO_END_RESEARCH_PIPELINE.md` | Authoritative long-term map: revised objective, benchmark role, method baselines, WP1--WP7 inputs/outputs/gates, result branches, references, and status |
| `docs/research_direction_novelty_feasibility.md` | 2026-08-10 novelty correction, closest prior work, revised research question, theoretical feasibility, and staged experiment path |
| `docs/theory_and_revised_experiment_8.10.md` | 8.10 Chinese theory analysis and revised matched experiment design for explicit NL-to-STL versus direct learned cost |
| `docs/minimum_research_delivery_8.10.md` | Minimum teacher-facing research delivery: purpose, required artifacts, acceptance gates, and work-computer sequence |
| `docs/CURRENT_STAGE1_STATUS.md` | Detailed Chinese status, visualization interpretation, remaining work, and next milestone acceptance criteria |
| `docs/stage1_plan.md` | Detailed Stage I engineering plan and resource list |
| `docs/environment_setup.md` | Tested setup commands, versions, and isolation notes |
| `docs/environment_inspection.md` | Public API, distance definition, and smoke-test results |
| `docs/stage1_rule_monitor_spec.md` | Normative rule semantics, monitor contract, calibration protocol, tests, and Ubuntu work order |
| `docs/rule_calibration_report.md` | Formal calibration protocol, evidence, selected parameters, and limitations |
| `docs/monitor_agreement_report.md` | Online/oracle/RTAMT agreement result |
| `docs/visualization.md` | One-command live/video runner, outputs, verification, and limitations |
| `docs/omnisafe_integration_report.md` | Wrapper architecture, vector terminal order, tests, positive-cost probe, and PPO-Lagrangian smoke evidence |
| `docs/problem-definition/safety_stl_problem_definition.pdf` | One-page formal problem definition |
| `docs/problem-definition/safety_stl_problem_definition.tex` | TeX source for the problem definition |

## Slides

| File | Purpose |
|---|---|
| `docs/slides/stage1_current_progress_slides.pptx` | Editable 9-page 2026-08-10 pre-wrapper progress snapshot |
| `docs/slides/stage1_current_progress_slides.pdf` | Distribution copy of the 2026-08-10 pre-wrapper progress snapshot |
| `docs/slides/source/current-progress-deck/` | Archived editable-shape PPTX generator and source notes; rendered PNGs are reproducible cache and remain untracked |
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
| `references/papers/2026_UAV_NL_STL_MILP_Repair_8.10.pdf` | NL-to-STL translation and repair in a UAV application; filename dated for the 2026-08-10 review |

## Additional literature

`references/papers/related/` contains papers gathered during the 2023-2026 novelty and feasibility review. The closest papers collected for the 2026-08-10 positioning update use `_8.10.pdf` filenames and are indexed by `references/papers/related/CLOSEST_PRIOR_WORK_8.10.md`.

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
| `configs/omnisafe_integration_smoke.yaml` | Three condition IDs and bounded PPO-Lagrangian smoke configuration |
| `scripts/collect_rule_calibration.py` | Formal controlled/random data collection and parameter selection |
| `scripts/generate_monitor_fixtures.py` | Stable environment fixture generation |
| `scripts/run_monitor_agreement.py` | Machine-readable agreement evaluation and report generation |
| `scripts/run_stage1_demo.py` | Python environment/monitor visualization entry point |
| `scripts/visualize_stage1.sh` | One-command Conda-aware launcher |
| `scripts/run_omnisafe_integration_smoke.py` | Positive-cost routing probe and minimal PPO-Lagrangian rollout/update runner |
| `scripts/run_omnisafe_smoke.sh` | Conda-aware one-command integration-smoke launcher |
| `src/safety_stl/signals.py` | Public hazard-lidar distance extraction |
| `src/safety_stl/monitor.py` | Causal online bounded-recovery monitor |
| `src/safety_stl/oracle.py` | Independent direct enumerator and RTAMT window check |
| `src/safety_stl/visualization.py` | Live viewer, annotated video, controller, and independent logs |
| `src/safety_stl/omnisafe_env.py` | Three cost modes, shared temporal observation, vector monitor lifecycle, and OmniSafe registration |
| `tests/` | Signal, monitor/oracle, visualization, wrapper, vector lifecycle, and stable-fixture tests |

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
- bulk OmniSafe run directories and checkpoints below `results/integration_smoke/`;
- main matched-seed training outputs, which do not exist yet.

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

The wrapper milestone tracks `results/integration_smoke/summary.json` and its
README. Bulk OmniSafe `progress.csv`, copied config, and checkpoint files remain
ignored; the summary records the relevant values and progress hash.

## Future additions

The OmniSafe wrapper/integration gate has passed. The next bounded additions are
the pre-main-study declaration, explicit condition-specific cost limits, one
positive-cost on-policy sanity run, and the small representation-comparison
artifact described in `docs/minimum_research_delivery_8.10.md`. Large matched
training must wait for those recorded decisions.
