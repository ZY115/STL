# References and Existing Resources

## 1. Core Stage I software

### Safety-Gymnasium

- Repository: https://github.com/PKU-Alignment/safety-gymnasium
- Documentation: https://safety-gymnasium.readthedocs.io/en/latest/
- Goal environment: https://safety-gymnasium.readthedocs.io/en/latest/environments/safe_navigation/goal.html

Role:

- provides `SafetyPointGoal1-v0`;
- provides the native task reward;
- provides the native hazard cost;
- provides the simulation and trajectory signals.

### OmniSafe

- Repository: https://github.com/PKU-Alignment/omnisafe
- Documentation: https://omnisafe.readthedocs.io/en/latest/
- Environment customization: https://omnisafe.readthedocs.io/en/latest/start/env.html

Role:

- provides PPO-Lagrangian and other Safe RL algorithms;
- provides training and logging infrastructure;
- supports Safety-Gymnasium;
- avoids implementing constrained policy optimization from scratch.

### RTAMT

- Repository: https://github.com/nickovic/rtamt
- PyPI: https://pypi.org/project/rtamt/
- Paper: https://arxiv.org/abs/2005.11827

Role:

- reference offline STL evaluation;
- discrete-time bounded-future monitoring;
- quantitative robustness calculation.

## 2. Core Stage I papers

### Safety-Gymnasium: A Unified Safe Reinforcement Learning Benchmark

- NeurIPS 2023 paper:
  https://proceedings.neurips.cc/paper_files/paper/2023/file/3c557a3d6a48cc99444f85e924c66753-Paper-Datasets_and_Benchmarks.pdf
- arXiv:
  https://arxiv.org/abs/2310.12567

Use: benchmark definition, environment API, and Safe RL evaluation context.

### OmniSafe: An Infrastructure for Accelerating Safe Reinforcement Learning Research

- JMLR:
  https://jmlr.org/papers/v25/23-0681.html

Use: constrained RL implementation and experiment infrastructure.

### RTAMT: Online Robustness Monitors from STL

- arXiv:
  https://arxiv.org/abs/2005.11827

Use: reference monitor semantics and implementation.

### Tractable Reinforcement Learning of Signal Temporal Logic Objectives

- PMLR:
  https://proceedings.mlr.press/v120/venkataraman20a.html
- Local copy:
  `papers/related/2020_Tractable_RL_of_STL_Objectives_8.10.pdf`

Use: temporal history, STL objectives, and RL-state considerations.

## 3. Closest Prior Work and Updated Novelty Boundary

The 2026-08-10 review changed the research positioning. The project must not
claim novelty for STL state augmentation, STL-constrained Lagrangian learning,
or monitor-to-cost integration by themselves.

### Deep Reinforcement Learning under Signal Temporal Logic Constraints Using Lagrangian Relaxation

- arXiv: https://arxiv.org/abs/2201.08504
- IEEE Access DOI: https://doi.org/10.1109/ACCESS.2022.3218216
- Local copy: `papers/related/2022_STL_Constraints_Lagrangian_DRL_8.10.pdf`

Overlap:

- formulates an STL-constrained control problem as an extended `tau-CMDP`;
- uses Lagrangian DRL;
- preprocesses temporal history into compact flag state.

Boundary:

- assumes the STL constraint is already available;
- does not compare NL-to-STL with direct NL-to-cost construction.

### STL-Based Synthesis of Feedback Controllers Using Reinforcement Learning

- arXiv: https://arxiv.org/abs/2212.01022
- AAAI paper: https://ojs.aaai.org/index.php/AAAI/article/view/26764
- Local copy: `papers/related/2023_STL_Feedback_Controllers_RL_8.10.pdf`

Overlap:

- generates online RL rewards from STL quantitative semantics;
- directly studies how aggregation semantics affect learning.

Boundary:

- treats STL as the controller-synthesis objective;
- does not study language-derived safety costs or the representation comparison.

### Temporal Logic Specification-Conditioned Decision Transformer for Offline Safe Reinforcement Learning

- PMLR: https://proceedings.mlr.press/v235/guo24j.html
- arXiv: https://arxiv.org/abs/2402.17217
- Local copy: `papers/related/2024_STL_Conditioned_Offline_Safe_RL_8.10.pdf`

Overlap:

- uses STL to represent non-Markovian safety constraints;
- evaluates Safe RL policies under temporal specifications.

Boundary:

- offline Decision Transformer setting rather than matched online PPO-Lagrangian;
- no NL-to-STL versus direct NL-to-cost comparison.

### RLRom: Monitoring and Training Reinforcement Learning Agents using Signal Temporal Logic

- Paper: https://ceur-ws.org/Vol-4142/paper18.pdf
- Local copy: `papers/related/2026_RLRom_STL_Monitoring_Training_RL_8.10.pdf`

Overlap:

- integrates STL monitoring with common RL frameworks;
- exposes robustness as observations or reward components.

Boundary:

- a monitor/training tool demonstration;
- no natural-language representation comparison.

### Integrating LTL Constraints into PPO for Safe Reinforcement Learning

- arXiv: https://arxiv.org/abs/2603.01292
- Code: https://github.com/EVIEHub/PPO-LTL
- Local copy: `papers/related/2026_PPO_LTL_8.10.pdf`

Overlap:

- compiles temporal logic into runtime monitors;
- translates violations into costs;
- integrates the costs with PPO-Lagrangian;
- augments the product state with automaton state.

Boundary:

- uses LTL rather than bounded real-valued STL;
- does not start from natural-language safety requirements;
- confirms that monitor-to-cost-to-PPO cannot be our novelty claim.

### Multi-Constrained Learning Robots under Full Signal Temporal Logic Specifications

- OpenReview: https://openreview.net/pdf?id=MIcZ9q09Q4
- Venue: AAMAS 2026
- Local download: pending because OpenReview currently requires browser
  verification; see `papers/related/CLOSEST_PRIOR_WORK_8.10.md`.

Overlap:

- constrained RL under multiple simultaneous STL constraints;
- extends Markov formulations to full STL, including `until`;
- compares against STL constraint aggregation.

Boundary:

- assumes formal specifications are supplied;
- targets full-STL multi-constraint optimization, not language representation
  fidelity or error attribution.

### From Language to Logic: A Theoretical Architecture for VLM-Grounded Safe Navigation

- arXiv: https://arxiv.org/abs/2605.04327
- Local copy:
  `papers/related/2026_From_Language_to_Logic_Safe_Navigation_8.10.pdf`

Overlap:

- translates human safety rules into STL;
- uses STL during navigation and runtime monitoring.

Boundary:

- presents a theoretical navigation architecture rather than a matched online
  Safe RL comparison;
- does not compare explicit formal intermediates against direct learned costs.

### Safe Reinforcement Learning with Natural Language Constraints

- arXiv: https://arxiv.org/abs/2010.05150
- OpenReview: https://openreview.net/forum?id=Ua5yGJhfgAg
- Local copy:
  `papers/related/2021_Safe_RL_Natural_Language_Constraints_8.10.pdf`

Overlap:

- maps textual constraints into learned spatial and temporal representations;
- trains a policy to reduce language-specified constraint violations.

Boundary:

- the intermediate representation is learned rather than executable STL;
- it does not compare formal monitoring with direct learned cost prediction
  under one matched backend.

### Safe Reinforcement Learning with Free-form Natural Language Constraints and Pre-Trained Language Models

- arXiv: https://arxiv.org/abs/2401.07553
- AAMAS paper: https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2024/pdfs/p1274.pdf
- DOI: https://doi.org/10.5555/3635637.3662985
- Local copy:
  `papers/related/2024_Freeform_NL_Constraints_Safe_RL_8.10.pdf`

Overlap:

- maps free-form language and observations to predicted binary costs;
- trains PPO with a Lagrangian multiplier using the predicted costs;
- supplies the most important direct-cost baseline for the revised question.

Boundary:

- does not use STL as an explicit, executable intermediate representation;
- does not evaluate polarity, temporal-scope, persistence, and deadline minimal
  pairs against a gold formal monitor.

### From Text to Trajectory: Exploring Complex Constraint Representation and Decomposition in Safe Reinforcement Learning

- OpenReview: https://openreview.net/forum?id=MDpIQ9hQ7H
- arXiv: https://arxiv.org/abs/2412.08920
- Local copy: `papers/related/2024_Text_to_Trajectory_Safe_RL_8.10.pdf`

Overlap:

- translates textual constraints and trajectory information into a learned
  safety signal;
- evaluates downstream Safe RL without a manually designed cost for every
  constraint.

Boundary:

- does not generate or execute STL;
- does not compare its learned cost labels against an explicit formal path on
  semantic minimal pairs.

### RESTL and ReasonSTL

- RESTL DOI: https://doi.org/10.1609/aaai.v40i36.40324
- RESTL local copy: `papers/related/2026_RESTL_8.10.pdf`
- ReasonSTL arXiv: https://arxiv.org/abs/2605.06483
- ReasonSTL local copy: `papers/related/2026_ReasonSTL_8.10.pdf`

Overlap:

- improve natural-language-to-STL generation and semantic fidelity;
- provide current translator designs and evaluation resources for Stage II.

Boundary:

- stop at specification generation rather than matched online Safe RL;
- do not compare STL-derived cost with a direct language-conditioned cost
  predictor at trace and policy levels.

The authoritative revised comparison and claim limits are documented in
`docs/research_direction_novelty_feasibility.md`.

## 4. Papers that motivated the broader project

### NL2TL: Transforming Natural Languages to Temporal Logics using Large Language Models

- ACL Anthology:
  https://aclanthology.org/2023.emnlp-main.985/
- Local copy:
  `papers/2023_NL2TL.pdf`

Use: lifted logical structures, natural-language-to-temporal-logic translation, T5, and GPT-assisted data or proposition processing.

### DeepLTL: Learning to Efficiently Satisfy Complex LTL Specifications for Multi-Task RL

- arXiv:
  https://arxiv.org/abs/2410.04631
- Project:
  https://deep-ltl.github.io/
- Local copy:
  `papers/2025_DeepLTL.pdf`

Use: execution of complex formal specifications, automata structure, and zero-shot formula-conditioned policy behavior.

### Safe Reinforcement Learning via Shielding

- arXiv:
  https://arxiv.org/abs/1708.08611
- Local copy:
  `papers/2018_Safe_RL_via_Shielding.pdf`

Use: alternative runtime safety enforcement based on action intervention.

### LLM-Enabled Low-Altitude UAV Natural Language Navigation via Signal Temporal Logic Specification Translation and Repair

- arXiv:
  https://arxiv.org/abs/2603.27583
- Local copy:
  `papers/2026_UAV_NL_STL_MILP_Repair_8.10.pdf`

Use: NL-to-STL translation, numerical repair, UAV application, and comparison with our cost-based Safe RL question.

## 5. Additional literature review materials

The `papers/related/` directory contains additional papers gathered during the novelty and feasibility review, including:

- natural-language constraints for Safe RL;
- DialogueSTL;
- Lang2LTL;
- free-form natural-language constraints for Safe RL;
- STL-conditioned offline Safe RL;
- LTL code generation;
- PPO with LTL;
- RESTL;
- ReasonSTL;
- SafeDec.

The closest-prior-work PDFs collected or renamed on 2026-08-10 use the
`_8.10.pdf` suffix and are indexed in
`papers/related/CLOSEST_PRIOR_WORK_8.10.md`.

The `extracted-text/` directory contains text extractions used for focused search and comparison. These are reference aids, not authoritative replacements for the PDFs.

## 6. Selected code references

The `code-notes/` directory contains selected files from related open-source projects that were inspected during planning:

- Safety-Gymnasium environment construction and hazard implementation;
- PPO-LTL wrapper and PPO-Lagrangian-related files.

These files are literature and implementation references. They are not the Stage I experiment code and should not be edited as if they were the project implementation.
