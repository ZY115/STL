# Package Manifest

## Purpose

This handoff package contains the durable research context required to continue the project on another computer or Codex account.

It intentionally excludes LaTeX temporary files and bulk raw trajectories. The
environment-inspection, rule-and-monitor, visualization, and OmniSafe-wrapper
integration milestones are complete. Tested monitor/wrapper code, runnable
visualization, frozen pilot configs, the completed full pilot's compact
analysis/figures, and stable sanity evidence are tracked; bulk checkpoints and
raw job logs remain local and ignored.

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
| `docs/CURRENT_EXECUTION_DIRECTIVE.md` | Short current directive for the D37/D38 continuous Stage II package |
| `docs/STAGE2_CONTINUOUS_WORK_ORDER.md` | Normative spatial replay, frozen O7, Stage II-A, Gold-cost diagnostic, online-interface and Stage II-B work order |
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
| `docs/stage1_pre_main_study_proposal.md` | D31 pilot-only criteria, seeds, uncertainty, budgets, and training scale |
| `docs/pre_main_engineering_gate_report.md` | On-policy positive-cost and common checkpoint-evaluator evidence |
| `docs/stage1_pilot_sanity_report.md` | Frozen pilot protocol and three-condition engineering-sanity evidence |
| `docs/cuda_enablement_report.md` | RTX 4090/PyTorch CUDA enablement, deterministic launch requirement, and PPOLag evidence |
| `docs/stage1_pilot_launch_readiness.md` | Completed runner/analysis/tests/preflight gate, exact launch/resume commands, resource projection, risks, and compute decision request |
| `docs/stage1_pilot_result_report.md` | Completed 15-job pilot result, frozen confidence intervals, learning-curve interpretation, figures and limitations |
| `docs/stage1_code_failure_analysis_and_repair_recommendations.md` | Post-pilot code-level diagnosis, evidence grading, OmniSafe runtime risks, and prioritized non-compute/diagnostic/confirmatory repair plan |
| `docs/stage1_o8_main_study_decision_proposal.md` | Post-pilot close/longer/bounded-diagnostic decision package; no compute authorization |
| `docs/stage2_o7_benchmark_design_proposal.md` | Candidate controlled-language schema, semantic pairs, splits, human review and offline gate |
| `docs/stage1_trajectory_diagnosis_report.md` | Existing-checkpoint trajectory mechanism analysis and installed OmniSafe runtime contract |
| `docs/stage2_v0_benchmark_report.md` | Machine-validated Stage II v0 single-family benchmark foundation and remaining review gates |
| `docs/stage2_v0_baseline_review_package.md` | Formal/current-observation/history-aware baseline contracts, fairness table and consolidated decisions |
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
| `docs/slides/research_timeline_revised_direction_slides.pptx` | Editable research-timeline deck showing the novelty correction and revised comparison |
| `docs/slides/research_direction_formal_vs_direct_slides.pptx` | Condensed editable deck for the formal-path versus direct-cost research question and current pilot role |

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
| `configs/on_policy_positive_cost_sanity.yaml` | Full-horizon actor-sampled positive STL-cost sanity |
| `configs/stage1_pre_main_proposal.yaml` | Machine-readable D31 pilot summary; not a final main-study standard |
| `configs/stage1_pilot/protocol.yaml` | Frozen shared Stage I pilot protocol and exact OmniSafe settings |
| `configs/stage1_pilot/*.yaml` | Frozen task-only, native-cost, and gold-STL condition overlays |
| `configs/stage1_pilot_sanity.yaml` | Engineering-only three-condition sanity overrides and acceptance gate |
| `configs/cuda_validation.yaml` | Fixed CUDA device/runtime/wrapper/full-horizon validation contract |
| `configs/stage1_pilot_preflight.yaml` | Excluded 100k exact-vector/epoch-scale throughput preflight contract |
| `scripts/collect_rule_calibration.py` | Formal controlled/random data collection and parameter selection |
| `scripts/generate_monitor_fixtures.py` | Stable environment fixture generation |
| `scripts/run_monitor_agreement.py` | Machine-readable agreement evaluation and report generation |
| `scripts/run_stage1_demo.py` | Python environment/monitor visualization entry point |
| `scripts/visualize_stage1.sh` | One-command Conda-aware launcher |
| `scripts/run_omnisafe_integration_smoke.py` | Positive-cost routing probe and minimal PPO-Lagrangian rollout/update runner |
| `scripts/run_omnisafe_smoke.sh` | Conda-aware one-command integration-smoke launcher |
| `scripts/run_on_policy_positive_cost_sanity.py` | Explicit-budget full-horizon PPOLag event-cost gate |
| `scripts/run_on_policy_sanity.sh` | Conda-aware on-policy sanity launcher |
| `scripts/evaluate_stage1_checkpoint.py` | Common checkpoint evaluation CLI |
| `scripts/evaluate_stage1_checkpoint.sh` | Conda-aware checkpoint evaluation launcher |
| `scripts/run_stage1_pilot_sanity.py` | Frozen-config composition, three-condition training, and paired evaluator gate |
| `scripts/run_stage1_pilot_sanity.sh` | Conda-aware three-condition sanity launcher |
| `scripts/validate_cuda_stage1.py` | CUDA device, wrapper tensor, dependency, and positive-cost PPOLag validation |
| `scripts/validate_cuda_stage1.sh` | Deterministic cuBLAS CUDA validation launcher |
| `scripts/run_stage1_pilot.py` | 15-job dry-run/selection/resume/train/evaluate orchestration and compute gate |
| `scripts/run_stage1_pilot.sh` | Deterministic CUDA launcher for pilot runner and preflight |
| `scripts/analyze_stage1_pilot.py` | Complete-matrix frozen analysis CLI |
| `scripts/plot_stage1_pilot.py` | Reproducible PNG/SVG evaluation, primary-comparison, learning-curve and constraint figures |
| `scripts/diagnose_stage1_trajectories.py` | CPU-only deterministic replay and per-step mechanism diagnosis of existing final checkpoints |
| `scripts/inspect_omnisafe_runtime.py` | Installed-source hashes and executable regression evidence for effective on-policy behavior |
| `scripts/build_stage2_v0_benchmark.py` | Synthetic/real Stage II trajectory construction and three-way Gold validation |
| `scripts/evaluate_stage2_predictions.py` | Common held-out trace-label, event-time, boundary and consistency evaluator |
| `src/safety_stl/signals.py` | Public hazard-lidar distance extraction |
| `src/safety_stl/monitor.py` | Causal online bounded-recovery monitor |
| `src/safety_stl/oracle.py` | Independent direct enumerator and RTAMT window check |
| `src/safety_stl/visualization.py` | Live viewer, annotated video, controller, and independent logs |
| `src/safety_stl/omnisafe_env.py` | Three cost modes, shared temporal observation, vector monitor lifecycle, and OmniSafe registration |
| `src/safety_stl/evaluation.py` | Checkpoint loading, gold oracle/RTAMT verification, and policy metrics |
| `src/safety_stl/pilot_protocol.py` | D31 validation and OmniSafe config composition |
| `src/safety_stl/pilot_runner.py` | Immutable attempts, hash verification, fixed checkpoint selection, training/evaluation execution |
| `src/safety_stl/pilot_analysis.py` | Pooled metrics, paired hierarchical bootstrap, non-inferiority and curve review |
| `src/safety_stl/runtime_contract.py` | Effective OmniSafe episode-window, discount, advantage and timeout-bootstrap audit |
| `src/safety_stl/trajectory_diagnosis.py` | Existing-checkpoint replay, mechanism decomposition, exports and plots |
| `src/safety_stl/stage2_benchmark.py` | Versioned Stage II contract validation, trace generation/import and Gold labeling |
| `src/safety_stl/offline_metrics.py` | Common Stage II prediction validation and offline metric computation |
| `benchmarks/stage2_v0/` | Draft single-family schemas, five examples, generated traces, labels, coverage and hashes |
| `configs/stage2_v0/baselines.yaml` | Reviewable three-method access/supervision/compute contract; not yet finally frozen |
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
- bulk OmniSafe run directories and checkpoints below `results/integration_smoke/`
  `results/on_policy_sanity/`, and `results/pilot_sanity/`;
- bulk full-pilot job attempts, checkpoints and raw progress logs under
  `results/stage1_pilot/jobs/`; they exist locally and are hash-addressed by
  successful manifests but are intentionally not packaged.

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

The pre-main engineering gate tracks `results/on_policy_sanity/summary.json`
and the compact `results/evaluation_smoke/summary.json`/`episodes.csv`. Raw
on-policy checkpoints and future large evaluation trajectory files remain
ignored.

The pilot sanity gate tracks `results/pilot_sanity/summary.json` and compact
paired evaluation summaries/episode CSVs. Bulk OmniSafe logs and checkpoints
remain ignored; the top-level summary records their paths and SHA-256 hashes.

The CUDA gate tracks `results/cuda_validation/summary.json` and README. Bulk
validation checkpoints/logs remain ignored. The environment lock now includes
PyTorch 2.4.1+cu124 and its exact CUDA 12.4 runtime dependencies.

The launch-preparation gate tracks `results/pilot_preflight/README.md`, compact
`summary.json`, and the 15-job dry-run manifest. Raw attempts, checkpoints,
progress logs and excluded evaluation CSV remain local and ignored.

The completed full pilot tracks `results/stage1_pilot/README.md` and the compact
`analysis/` package: frozen JSON/CSV outputs, 10,000 bootstrap primary rows,
1,500 episode records, learning-curve summaries, PNG/SVG figures and a figure
hash manifest. The 15 raw job/checkpoint trees remain ignored.

The post-pilot diagnosis tracks `results/post_pilot_diagnosis/`: effective
runtime evidence, replay/checkpoint summaries, representative per-step public
signals, exact checkpoint/seed provenance and two PNG mechanism plots. It
reuses fixed final checkpoints and performs no training or checkpoint
selection. Stage II generated JSONL files and their local hash manifest are
tracked under `benchmarks/stage2_v0/generated/` because they are compact,
versioned benchmark evidence rather than raw training output.

## Future additions

The D31 protocol, three-condition sanity, resumable matrix runner, frozen
analysis, excluded 100k preflight and full five-seed/three-condition pilot have
passed their engineering gates. The pilot did not meet the 30% safety target
and is not converged. The post-pilot runtime/trajectory diagnosis and Stage II
machine foundation are now implemented without retraining; the full suite has
68 passing tests. O8 remains open for
the final-main-study standard; independent semantic review and the final O7
formula/split/model/gate decisions remain open.
