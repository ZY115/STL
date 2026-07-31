# Package Manifest

## Purpose

This handoff package contains the durable research context required to continue the project on another computer or Codex account.

It intentionally excludes LaTeX temporary files. The environment-inspection
milestone is complete; generated outputs live under an ignored `results/`
directory, while monitor and training implementation directories do not yet
exist.

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

## Project documents

| File | Purpose |
|---|---|
| `docs/PROJECT_INTRODUCTION.md` | Short Chinese and English introduction for group sharing |
| `docs/stage1_plan.md` | Detailed Stage I engineering plan and resource list |
| `docs/environment_setup.md` | Tested setup commands, versions, and isolation notes |
| `docs/environment_inspection.md` | Public API, distance definition, and smoke-test results |
| `docs/stage1_rule_monitor_spec.md` | Normative rule semantics, monitor contract, calibration protocol, tests, and Ubuntu work order |
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
- any untested monitor or training implementation.

## Generated outputs

`results/.gitignore` keeps raw generated CSV trajectories out of the
research-document history. The local environment inspection produced CSV and
MP4 files under `results/environment_inspection/`. Git retains the two compact
MP4 renderings, the directory README, and the JSON summary. The summary includes
statistics and SHA-256 hashes for both tracked videos and ignored raw CSV
artifacts.

## Future additions

The temporal semantics are now frozen. During the next rule-and-monitor
milestone, the project may add only the implementation surface declared in
`docs/stage1_rule_monitor_spec.md`:

- calibration and fixture-generation scripts;
- signal, monitor, and offline-oracle source code;
- the fixed rule configuration;
- semantic unit tests and stable fixtures;
- calibration and monitor-agreement reports.

Wrapper, training, and language-layer code remain deferred until that
document's completion gate passes.
