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

Use: temporal history, STL objectives, and RL-state considerations.

## 3. Papers that motivated the broader project

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
  `papers/2026_UAV_NL_STL_MILP_Repair.pdf`

Use: NL-to-STL translation, numerical repair, UAV application, and comparison with our cost-based Safe RL question.

## 4. Additional literature review materials

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

The `extracted-text/` directory contains text extractions used for focused search and comparison. These are reference aids, not authoritative replacements for the PDFs.

## 5. Selected code references

The `code-notes/` directory contains selected files from related open-source projects that were inspected during planning:

- Safety-Gymnasium environment construction and hazard implementation;
- PPO-LTL wrapper and PPO-Lagrangian-related files.

These files are literature and implementation references. They are not the Stage I experiment code and should not be edited as if they were the project implementation.
