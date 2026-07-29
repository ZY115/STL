# Package Manifest

## Purpose

This handoff package contains the durable research context required to continue the project on another computer or Codex account.

It intentionally excludes LaTeX temporary files and does not yet contain experiment implementation directories.

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

## Project documents

| File | Purpose |
|---|---|
| `docs/PROJECT_INTRODUCTION.md` | Short Chinese and English introduction for group sharing |
| `docs/stage1_plan.md` | Detailed Stage I engineering plan and resource list |
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
- any untested experiment implementation.

## Future additions

After the Ubuntu environment inspection, the project may add:

- a tested setup guide;
- an environment lock file;
- source code;
- unit tests;
- experiment configurations;
- trajectory fixtures;
- results and analysis.

Their directory structure should be chosen after the actual Safety-Gymnasium and OmniSafe interfaces have been inspected.
