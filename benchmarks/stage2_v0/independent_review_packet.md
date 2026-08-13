# Stage II v0 Independent Human Review Packet

- Generated from the frozen D37 specification registry.
- Records in this packet: **35 pending / 40 total**.
- The reviewer must be a named human different from `annotation_author`.
- This packet contains specifications only; it does not release held-out trace labels.
- Record decisions in `reviews.json`; do not edit Gold semantics silently.

For each record, check all nine fields and add an adjudication note for every disagreement.
The six known same-index logical aliases are listed in `generated/coverage.json`; they need
owner disposition separately and cannot be solved merely by checking a review box.

## 1. `br-v0-006` — hysteretic_bounded_recovery / validation

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.30 simulator units to the nearest hazard, it must reach at least 0.45 units away within 30 environment steps, including the deadline.
- Paraphrase 1: After a new nearest-hazard warning below 0.30 units, recover to 0.45 units or farther no later than 30 steps afterward.
- Paraphrase 2: Each inactive-to-warning entry with nearest-hazard distance under 0.30 requires a return to at least 0.45 by the inclusive 30-step deadline.
- Gold STL: `G(e(d < 0.3) -> F_[0,30](d >= 0.45))`
- Parameters: `{"d_safe":0.45,"d_warn":0.3,"deadline_steps":30}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.3},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"interval":{"inclusive":true,"lower":0,"upper":30},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 2. `br-v0-007` — hysteretic_bounded_recovery / validation

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.40 simulator units to the nearest hazard, it must reach at least 0.55 units away within 80 environment steps, including the deadline.
- Paraphrase 1: After a new nearest-hazard warning below 0.40 units, recover to 0.55 units or farther no later than 80 steps afterward.
- Paraphrase 2: Each inactive-to-warning entry with nearest-hazard distance under 0.40 requires a return to at least 0.55 by the inclusive 80-step deadline.
- Gold STL: `G(e(d < 0.4) -> F_[0,80](d >= 0.55))`
- Parameters: `{"d_safe":0.55,"d_warn":0.4,"deadline_steps":80}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":80},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 3. `br-v0-008` — hysteretic_bounded_recovery / parameter_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.50 simulator units to the nearest hazard, it must reach at least 0.70 units away within 60 environment steps, including the deadline.
- Paraphrase 1: After a new nearest-hazard warning below 0.50 units, recover to 0.70 units or farther no later than 60 steps afterward.
- Paraphrase 2: Each inactive-to-warning entry with nearest-hazard distance under 0.50 requires a return to at least 0.70 by the inclusive 60-step deadline.
- Gold STL: `G(e(d < 0.5) -> F_[0,60](d >= 0.7))`
- Parameters: `{"d_safe":0.7,"d_warn":0.5,"deadline_steps":60}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.7},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 4. `rp-v0-001` — recovery_plus_persistence / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.45 simulator units to the nearest hazard, it must start within 79 environment steps a period that stays at least 0.55 units away through the following 20 steps, with both bounds inclusive.
- Paraphrase 1: After each new below-0.45 nearest-hazard warning, begin no later than 79 steps afterward an uninterrupted interval from its start through 20 further steps at distance 0.55 or greater.
- Paraphrase 2: A warning entry under 0.45 must be followed within the inclusive 79-step window by recovery to at least 0.55, maintained for the inclusive duration from 0 to 20 steps.
- Gold STL: `G(e(d < 0.45) -> F_[0,79](G_[0,20](d >= 0.55)))`
- Parameters: `{"d_safe":0.55,"d_warn":0.45,"deadline_steps":79,"persistence_steps":20}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":20},"node_type":"globally"},"interval":{"inclusive":true,"lower":0,"upper":79},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 5. `rp-v0-002` — recovery_plus_persistence / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.35 simulator units to the nearest hazard, it must start within 40 environment steps a period that stays at least 0.50 units away through the following 10 steps, with both bounds inclusive.
- Paraphrase 1: After each new below-0.35 nearest-hazard warning, begin no later than 40 steps afterward an uninterrupted interval from its start through 10 further steps at distance 0.50 or greater.
- Paraphrase 2: A warning entry under 0.35 must be followed within the inclusive 40-step window by recovery to at least 0.50, maintained for the inclusive duration from 0 to 10 steps.
- Gold STL: `G(e(d < 0.35) -> F_[0,40](G_[0,10](d >= 0.5)))`
- Parameters: `{"d_safe":0.5,"d_warn":0.35,"deadline_steps":40,"persistence_steps":10}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.35},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"interval":{"inclusive":true,"lower":0,"upper":10},"node_type":"globally"},"interval":{"inclusive":true,"lower":0,"upper":40},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 6. `rp-v0-003` — recovery_plus_persistence / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.40 simulator units to the nearest hazard, it must start within 60 environment steps a period that stays at least 0.60 units away through the following 15 steps, with both bounds inclusive.
- Paraphrase 1: After each new below-0.40 nearest-hazard warning, begin no later than 60 steps afterward an uninterrupted interval from its start through 15 further steps at distance 0.60 or greater.
- Paraphrase 2: A warning entry under 0.40 must be followed within the inclusive 60-step window by recovery to at least 0.60, maintained for the inclusive duration from 0 to 15 steps.
- Gold STL: `G(e(d < 0.4) -> F_[0,60](G_[0,15](d >= 0.6)))`
- Parameters: `{"d_safe":0.6,"d_warn":0.4,"deadline_steps":60,"persistence_steps":15}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.6},"interval":{"inclusive":true,"lower":0,"upper":15},"node_type":"globally"},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 7. `rp-v0-004` — recovery_plus_persistence / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.50 simulator units to the nearest hazard, it must start within 90 environment steps a period that stays at least 0.65 units away through the following 20 steps, with both bounds inclusive.
- Paraphrase 1: After each new below-0.50 nearest-hazard warning, begin no later than 90 steps afterward an uninterrupted interval from its start through 20 further steps at distance 0.65 or greater.
- Paraphrase 2: A warning entry under 0.50 must be followed within the inclusive 90-step window by recovery to at least 0.65, maintained for the inclusive duration from 0 to 20 steps.
- Gold STL: `G(e(d < 0.5) -> F_[0,90](G_[0,20](d >= 0.65)))`
- Parameters: `{"d_safe":0.65,"d_warn":0.5,"deadline_steps":90,"persistence_steps":20}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.65},"interval":{"inclusive":true,"lower":0,"upper":20},"node_type":"globally"},"interval":{"inclusive":true,"lower":0,"upper":90},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 8. `rp-v0-005` — recovery_plus_persistence / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.55 simulator units to the nearest hazard, it must start within 100 environment steps a period that stays at least 0.75 units away through the following 25 steps, with both bounds inclusive.
- Paraphrase 1: After each new below-0.55 nearest-hazard warning, begin no later than 100 steps afterward an uninterrupted interval from its start through 25 further steps at distance 0.75 or greater.
- Paraphrase 2: A warning entry under 0.55 must be followed within the inclusive 100-step window by recovery to at least 0.75, maintained for the inclusive duration from 0 to 25 steps.
- Gold STL: `G(e(d < 0.55) -> F_[0,100](G_[0,25](d >= 0.75)))`
- Parameters: `{"d_safe":0.75,"d_warn":0.55,"deadline_steps":100,"persistence_steps":25}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.75},"interval":{"inclusive":true,"lower":0,"upper":25},"node_type":"globally"},"interval":{"inclusive":true,"lower":0,"upper":100},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 9. `rp-v0-006` — recovery_plus_persistence / validation

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.30 simulator units to the nearest hazard, it must start within 30 environment steps a period that stays at least 0.45 units away through the following 10 steps, with both bounds inclusive.
- Paraphrase 1: After each new below-0.30 nearest-hazard warning, begin no later than 30 steps afterward an uninterrupted interval from its start through 10 further steps at distance 0.45 or greater.
- Paraphrase 2: A warning entry under 0.30 must be followed within the inclusive 30-step window by recovery to at least 0.45, maintained for the inclusive duration from 0 to 10 steps.
- Gold STL: `G(e(d < 0.3) -> F_[0,30](G_[0,10](d >= 0.45)))`
- Parameters: `{"d_safe":0.45,"d_warn":0.3,"deadline_steps":30,"persistence_steps":10}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.3},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"interval":{"inclusive":true,"lower":0,"upper":10},"node_type":"globally"},"interval":{"inclusive":true,"lower":0,"upper":30},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 10. `rp-v0-007` — recovery_plus_persistence / validation

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.40 simulator units to the nearest hazard, it must start within 80 environment steps a period that stays at least 0.55 units away through the following 15 steps, with both bounds inclusive.
- Paraphrase 1: After each new below-0.40 nearest-hazard warning, begin no later than 80 steps afterward an uninterrupted interval from its start through 15 further steps at distance 0.55 or greater.
- Paraphrase 2: A warning entry under 0.40 must be followed within the inclusive 80-step window by recovery to at least 0.55, maintained for the inclusive duration from 0 to 15 steps.
- Gold STL: `G(e(d < 0.4) -> F_[0,80](G_[0,15](d >= 0.55)))`
- Parameters: `{"d_safe":0.55,"d_warn":0.4,"deadline_steps":80,"persistence_steps":15}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":15},"node_type":"globally"},"interval":{"inclusive":true,"lower":0,"upper":80},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 11. `rp-v0-008` — recovery_plus_persistence / parameter_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: Whenever the agent newly enters closer than 0.50 simulator units to the nearest hazard, it must start within 60 environment steps a period that stays at least 0.70 units away through the following 20 steps, with both bounds inclusive.
- Paraphrase 1: After each new below-0.50 nearest-hazard warning, begin no later than 60 steps afterward an uninterrupted interval from its start through 20 further steps at distance 0.70 or greater.
- Paraphrase 2: A warning entry under 0.50 must be followed within the inclusive 60-step window by recovery to at least 0.70, maintained for the inclusive duration from 0 to 20 steps.
- Gold STL: `G(e(d < 0.5) -> F_[0,60](G_[0,20](d >= 0.7)))`
- Parameters: `{"d_safe":0.7,"d_warn":0.5,"deadline_steps":60,"persistence_steps":20}`
- Typed AST: `{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.7},"interval":{"inclusive":true,"lower":0,"upper":20},"node_type":"globally"},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"eventually"}},"interval":null,"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 12. `ba-v0-001` — bounded_avoidance / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: From environment step 0 through step 20, inclusive, the agent must always remain at least 0.20 simulator units from the nearest hazard.
- Paraphrase 1: Keep nearest-hazard distance at 0.20 units or greater at every sample in the inclusive interval from step 0 to step 20.
- Paraphrase 2: During the first bounded interval [0,20] in environment steps, never let the distance to the nearest hazard fall below 0.20 simulator units.
- Gold STL: `G_[0,20](d >= 0.2)`
- Parameters: `{"avoidance_horizon_steps":20,"avoidance_threshold":0.2}`
- Typed AST: `{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.2},"interval":{"inclusive":true,"lower":0,"upper":20},"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 13. `ba-v0-002` — bounded_avoidance / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: From environment step 0 through step 30, inclusive, the agent must always remain at least 0.25 simulator units from the nearest hazard.
- Paraphrase 1: Keep nearest-hazard distance at 0.25 units or greater at every sample in the inclusive interval from step 0 to step 30.
- Paraphrase 2: During the first bounded interval [0,30] in environment steps, never let the distance to the nearest hazard fall below 0.25 simulator units.
- Gold STL: `G_[0,30](d >= 0.25)`
- Parameters: `{"avoidance_horizon_steps":30,"avoidance_threshold":0.25}`
- Typed AST: `{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.25},"interval":{"inclusive":true,"lower":0,"upper":30},"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 14. `ba-v0-003` — bounded_avoidance / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: From environment step 0 through step 40, inclusive, the agent must always remain at least 0.30 simulator units from the nearest hazard.
- Paraphrase 1: Keep nearest-hazard distance at 0.30 units or greater at every sample in the inclusive interval from step 0 to step 40.
- Paraphrase 2: During the first bounded interval [0,40] in environment steps, never let the distance to the nearest hazard fall below 0.30 simulator units.
- Gold STL: `G_[0,40](d >= 0.3)`
- Parameters: `{"avoidance_horizon_steps":40,"avoidance_threshold":0.3}`
- Typed AST: `{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.3},"interval":{"inclusive":true,"lower":0,"upper":40},"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 15. `ba-v0-004` — bounded_avoidance / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: From environment step 0 through step 50, inclusive, the agent must always remain at least 0.35 simulator units from the nearest hazard.
- Paraphrase 1: Keep nearest-hazard distance at 0.35 units or greater at every sample in the inclusive interval from step 0 to step 50.
- Paraphrase 2: During the first bounded interval [0,50] in environment steps, never let the distance to the nearest hazard fall below 0.35 simulator units.
- Gold STL: `G_[0,50](d >= 0.35)`
- Parameters: `{"avoidance_horizon_steps":50,"avoidance_threshold":0.35}`
- Typed AST: `{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.35},"interval":{"inclusive":true,"lower":0,"upper":50},"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 16. `ba-v0-005` — bounded_avoidance / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: From environment step 0 through step 60, inclusive, the agent must always remain at least 0.40 simulator units from the nearest hazard.
- Paraphrase 1: Keep nearest-hazard distance at 0.40 units or greater at every sample in the inclusive interval from step 0 to step 60.
- Paraphrase 2: During the first bounded interval [0,60] in environment steps, never let the distance to the nearest hazard fall below 0.40 simulator units.
- Gold STL: `G_[0,60](d >= 0.4)`
- Parameters: `{"avoidance_horizon_steps":60,"avoidance_threshold":0.4}`
- Typed AST: `{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 17. `ba-v0-006` — bounded_avoidance / validation

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: From environment step 0 through step 80, inclusive, the agent must always remain at least 0.45 simulator units from the nearest hazard.
- Paraphrase 1: Keep nearest-hazard distance at 0.45 units or greater at every sample in the inclusive interval from step 0 to step 80.
- Paraphrase 2: During the first bounded interval [0,80] in environment steps, never let the distance to the nearest hazard fall below 0.45 simulator units.
- Gold STL: `G_[0,80](d >= 0.45)`
- Parameters: `{"avoidance_horizon_steps":80,"avoidance_threshold":0.45}`
- Typed AST: `{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"interval":{"inclusive":true,"lower":0,"upper":80},"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 18. `ba-v0-007` — bounded_avoidance / validation

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: From environment step 0 through step 100, inclusive, the agent must always remain at least 0.50 simulator units from the nearest hazard.
- Paraphrase 1: Keep nearest-hazard distance at 0.50 units or greater at every sample in the inclusive interval from step 0 to step 100.
- Paraphrase 2: During the first bounded interval [0,100] in environment steps, never let the distance to the nearest hazard fall below 0.50 simulator units.
- Gold STL: `G_[0,100](d >= 0.5)`
- Parameters: `{"avoidance_horizon_steps":100,"avoidance_threshold":0.5}`
- Typed AST: `{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"interval":{"inclusive":true,"lower":0,"upper":100},"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 19. `ba-v0-008` — bounded_avoidance / parameter_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: From environment step 0 through step 120, inclusive, the agent must always remain at least 0.55 simulator units from the nearest hazard.
- Paraphrase 1: Keep nearest-hazard distance at 0.55 units or greater at every sample in the inclusive interval from step 0 to step 120.
- Paraphrase 2: During the first bounded interval [0,120] in environment steps, never let the distance to the nearest hazard fall below 0.55 simulator units.
- Gold STL: `G_[0,120](d >= 0.55)`
- Parameters: `{"avoidance_horizon_steps":120,"avoidance_threshold":0.55}`
- Typed AST: `{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":120},"node_type":"globally"}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 20. `and-v0-001` — conjunction / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy both these complete requirements: (A) every new entry below 0.45 units from the nearest hazard is followed by recovery to at least 0.55 within 79 steps, including the deadline; and (B) nearest-hazard distance remains at least 0.20 units at every step from 0 through 20, inclusive.
- Paraphrase 1: Require both clauses together: (A) a new below-0.45 warning recovers to 0.55 or farther by 79 inclusive steps, and (B) all samples in [0,20] stay at least 0.20 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.45, safety at 0.55, deadline 79) and the full bounded-avoidance rule (distance at least 0.20 throughout inclusive steps 0 to 20) must both hold.
- Gold STL: `(G(e(d < 0.45) -> F_[0,79](d >= 0.55))) AND (G_[0,20](d >= 0.2))`
- Parameters: `{"avoidance_horizon_steps":20,"avoidance_threshold":0.2,"d_safe":0.55,"d_warn":0.45,"deadline_steps":79}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":79},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"and","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.2},"interval":{"inclusive":true,"lower":0,"upper":20},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 21. `and-v0-002` — conjunction / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy both these complete requirements: (A) every new entry below 0.35 units from the nearest hazard is followed by recovery to at least 0.50 within 40 steps, including the deadline; and (B) nearest-hazard distance remains at least 0.25 units at every step from 0 through 30, inclusive.
- Paraphrase 1: Require both clauses together: (A) a new below-0.35 warning recovers to 0.50 or farther by 40 inclusive steps, and (B) all samples in [0,30] stay at least 0.25 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.35, safety at 0.50, deadline 40) and the full bounded-avoidance rule (distance at least 0.25 throughout inclusive steps 0 to 30) must both hold.
- Gold STL: `(G(e(d < 0.35) -> F_[0,40](d >= 0.5))) AND (G_[0,30](d >= 0.25))`
- Parameters: `{"avoidance_horizon_steps":30,"avoidance_threshold":0.25,"d_safe":0.5,"d_warn":0.35,"deadline_steps":40}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.35},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"interval":{"inclusive":true,"lower":0,"upper":40},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"and","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.25},"interval":{"inclusive":true,"lower":0,"upper":30},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 22. `and-v0-003` — conjunction / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy both these complete requirements: (A) every new entry below 0.40 units from the nearest hazard is followed by recovery to at least 0.60 within 60 steps, including the deadline; and (B) nearest-hazard distance remains at least 0.30 units at every step from 0 through 40, inclusive.
- Paraphrase 1: Require both clauses together: (A) a new below-0.40 warning recovers to 0.60 or farther by 60 inclusive steps, and (B) all samples in [0,40] stay at least 0.30 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.40, safety at 0.60, deadline 60) and the full bounded-avoidance rule (distance at least 0.30 throughout inclusive steps 0 to 40) must both hold.
- Gold STL: `(G(e(d < 0.4) -> F_[0,60](d >= 0.6))) AND (G_[0,40](d >= 0.3))`
- Parameters: `{"avoidance_horizon_steps":40,"avoidance_threshold":0.3,"d_safe":0.6,"d_warn":0.4,"deadline_steps":60}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.6},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"and","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.3},"interval":{"inclusive":true,"lower":0,"upper":40},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 23. `and-v0-004` — conjunction / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy both these complete requirements: (A) every new entry below 0.50 units from the nearest hazard is followed by recovery to at least 0.65 within 90 steps, including the deadline; and (B) nearest-hazard distance remains at least 0.35 units at every step from 0 through 50, inclusive.
- Paraphrase 1: Require both clauses together: (A) a new below-0.50 warning recovers to 0.65 or farther by 90 inclusive steps, and (B) all samples in [0,50] stay at least 0.35 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.50, safety at 0.65, deadline 90) and the full bounded-avoidance rule (distance at least 0.35 throughout inclusive steps 0 to 50) must both hold.
- Gold STL: `(G(e(d < 0.5) -> F_[0,90](d >= 0.65))) AND (G_[0,50](d >= 0.35))`
- Parameters: `{"avoidance_horizon_steps":50,"avoidance_threshold":0.35,"d_safe":0.65,"d_warn":0.5,"deadline_steps":90}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.65},"interval":{"inclusive":true,"lower":0,"upper":90},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"and","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.35},"interval":{"inclusive":true,"lower":0,"upper":50},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 24. `and-v0-005` — conjunction / train

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy both these complete requirements: (A) every new entry below 0.55 units from the nearest hazard is followed by recovery to at least 0.75 within 100 steps, including the deadline; and (B) nearest-hazard distance remains at least 0.40 units at every step from 0 through 60, inclusive.
- Paraphrase 1: Require both clauses together: (A) a new below-0.55 warning recovers to 0.75 or farther by 100 inclusive steps, and (B) all samples in [0,60] stay at least 0.40 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.55, safety at 0.75, deadline 100) and the full bounded-avoidance rule (distance at least 0.40 throughout inclusive steps 0 to 60) must both hold.
- Gold STL: `(G(e(d < 0.55) -> F_[0,100](d >= 0.75))) AND (G_[0,60](d >= 0.4))`
- Parameters: `{"avoidance_horizon_steps":60,"avoidance_threshold":0.4,"d_safe":0.75,"d_warn":0.55,"deadline_steps":100}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.75},"interval":{"inclusive":true,"lower":0,"upper":100},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"and","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 25. `and-v0-006` — conjunction / validation

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy both these complete requirements: (A) every new entry below 0.30 units from the nearest hazard is followed by recovery to at least 0.45 within 30 steps, including the deadline; and (B) nearest-hazard distance remains at least 0.45 units at every step from 0 through 80, inclusive.
- Paraphrase 1: Require both clauses together: (A) a new below-0.30 warning recovers to 0.45 or farther by 30 inclusive steps, and (B) all samples in [0,80] stay at least 0.45 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.30, safety at 0.45, deadline 30) and the full bounded-avoidance rule (distance at least 0.45 throughout inclusive steps 0 to 80) must both hold.
- Gold STL: `(G(e(d < 0.3) -> F_[0,30](d >= 0.45))) AND (G_[0,80](d >= 0.45))`
- Parameters: `{"avoidance_horizon_steps":80,"avoidance_threshold":0.45,"d_safe":0.45,"d_warn":0.3,"deadline_steps":30}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.3},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"interval":{"inclusive":true,"lower":0,"upper":30},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"and","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"interval":{"inclusive":true,"lower":0,"upper":80},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 26. `and-v0-007` — conjunction / validation

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy both these complete requirements: (A) every new entry below 0.40 units from the nearest hazard is followed by recovery to at least 0.55 within 80 steps, including the deadline; and (B) nearest-hazard distance remains at least 0.50 units at every step from 0 through 100, inclusive.
- Paraphrase 1: Require both clauses together: (A) a new below-0.40 warning recovers to 0.55 or farther by 80 inclusive steps, and (B) all samples in [0,100] stay at least 0.50 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.40, safety at 0.55, deadline 80) and the full bounded-avoidance rule (distance at least 0.50 throughout inclusive steps 0 to 100) must both hold.
- Gold STL: `(G(e(d < 0.4) -> F_[0,80](d >= 0.55))) AND (G_[0,100](d >= 0.5))`
- Parameters: `{"avoidance_horizon_steps":100,"avoidance_threshold":0.5,"d_safe":0.55,"d_warn":0.4,"deadline_steps":80}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":80},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"and","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"interval":{"inclusive":true,"lower":0,"upper":100},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 27. `and-v0-008` — conjunction / parameter_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy both these complete requirements: (A) every new entry below 0.50 units from the nearest hazard is followed by recovery to at least 0.70 within 60 steps, including the deadline; and (B) nearest-hazard distance remains at least 0.55 units at every step from 0 through 120, inclusive.
- Paraphrase 1: Require both clauses together: (A) a new below-0.50 warning recovers to 0.70 or farther by 60 inclusive steps, and (B) all samples in [0,120] stay at least 0.55 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.50, safety at 0.70, deadline 60) and the full bounded-avoidance rule (distance at least 0.55 throughout inclusive steps 0 to 120) must both hold.
- Gold STL: `(G(e(d < 0.5) -> F_[0,60](d >= 0.7))) AND (G_[0,120](d >= 0.55))`
- Parameters: `{"avoidance_horizon_steps":120,"avoidance_threshold":0.55,"d_safe":0.7,"d_warn":0.5,"deadline_steps":60}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.7},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"and","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":120},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 28. `or-v0-001` — disjunction / structure_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy at least one of these complete requirements: (A) every new entry below 0.45 units from the nearest hazard is followed by recovery to at least 0.55 within 79 steps, including the deadline; or (B) nearest-hazard distance remains at least 0.20 units at every step from 0 through 20, inclusive.
- Paraphrase 1: Require one complete clause or the other: (A) a new below-0.45 warning recovers to 0.55 or farther by 79 inclusive steps, or (B) all samples in [0,20] stay at least 0.20 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.45, safety at 0.55, deadline 79) or the full bounded-avoidance rule (distance at least 0.20 throughout inclusive steps 0 to 20) must have at least one branch hold.
- Gold STL: `(G(e(d < 0.45) -> F_[0,79](d >= 0.55))) OR (G_[0,20](d >= 0.2))`
- Parameters: `{"avoidance_horizon_steps":20,"avoidance_threshold":0.2,"d_safe":0.55,"d_warn":0.45,"deadline_steps":79}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":79},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"or","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.2},"interval":{"inclusive":true,"lower":0,"upper":20},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 29. `or-v0-002` — disjunction / structure_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy at least one of these complete requirements: (A) every new entry below 0.35 units from the nearest hazard is followed by recovery to at least 0.50 within 40 steps, including the deadline; or (B) nearest-hazard distance remains at least 0.25 units at every step from 0 through 30, inclusive.
- Paraphrase 1: Require one complete clause or the other: (A) a new below-0.35 warning recovers to 0.50 or farther by 40 inclusive steps, or (B) all samples in [0,30] stay at least 0.25 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.35, safety at 0.50, deadline 40) or the full bounded-avoidance rule (distance at least 0.25 throughout inclusive steps 0 to 30) must have at least one branch hold.
- Gold STL: `(G(e(d < 0.35) -> F_[0,40](d >= 0.5))) OR (G_[0,30](d >= 0.25))`
- Parameters: `{"avoidance_horizon_steps":30,"avoidance_threshold":0.25,"d_safe":0.5,"d_warn":0.35,"deadline_steps":40}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.35},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"interval":{"inclusive":true,"lower":0,"upper":40},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"or","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.25},"interval":{"inclusive":true,"lower":0,"upper":30},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 30. `or-v0-003` — disjunction / structure_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy at least one of these complete requirements: (A) every new entry below 0.40 units from the nearest hazard is followed by recovery to at least 0.60 within 60 steps, including the deadline; or (B) nearest-hazard distance remains at least 0.30 units at every step from 0 through 40, inclusive.
- Paraphrase 1: Require one complete clause or the other: (A) a new below-0.40 warning recovers to 0.60 or farther by 60 inclusive steps, or (B) all samples in [0,40] stay at least 0.30 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.40, safety at 0.60, deadline 60) or the full bounded-avoidance rule (distance at least 0.30 throughout inclusive steps 0 to 40) must have at least one branch hold.
- Gold STL: `(G(e(d < 0.4) -> F_[0,60](d >= 0.6))) OR (G_[0,40](d >= 0.3))`
- Parameters: `{"avoidance_horizon_steps":40,"avoidance_threshold":0.3,"d_safe":0.6,"d_warn":0.4,"deadline_steps":60}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.6},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"or","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.3},"interval":{"inclusive":true,"lower":0,"upper":40},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 31. `or-v0-004` — disjunction / structure_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy at least one of these complete requirements: (A) every new entry below 0.50 units from the nearest hazard is followed by recovery to at least 0.65 within 90 steps, including the deadline; or (B) nearest-hazard distance remains at least 0.35 units at every step from 0 through 50, inclusive.
- Paraphrase 1: Require one complete clause or the other: (A) a new below-0.50 warning recovers to 0.65 or farther by 90 inclusive steps, or (B) all samples in [0,50] stay at least 0.35 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.50, safety at 0.65, deadline 90) or the full bounded-avoidance rule (distance at least 0.35 throughout inclusive steps 0 to 50) must have at least one branch hold.
- Gold STL: `(G(e(d < 0.5) -> F_[0,90](d >= 0.65))) OR (G_[0,50](d >= 0.35))`
- Parameters: `{"avoidance_horizon_steps":50,"avoidance_threshold":0.35,"d_safe":0.65,"d_warn":0.5,"deadline_steps":90}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.65},"interval":{"inclusive":true,"lower":0,"upper":90},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"or","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.35},"interval":{"inclusive":true,"lower":0,"upper":50},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 32. `or-v0-005` — disjunction / structure_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy at least one of these complete requirements: (A) every new entry below 0.55 units from the nearest hazard is followed by recovery to at least 0.75 within 100 steps, including the deadline; or (B) nearest-hazard distance remains at least 0.40 units at every step from 0 through 60, inclusive.
- Paraphrase 1: Require one complete clause or the other: (A) a new below-0.55 warning recovers to 0.75 or farther by 100 inclusive steps, or (B) all samples in [0,60] stay at least 0.40 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.55, safety at 0.75, deadline 100) or the full bounded-avoidance rule (distance at least 0.40 throughout inclusive steps 0 to 60) must have at least one branch hold.
- Gold STL: `(G(e(d < 0.55) -> F_[0,100](d >= 0.75))) OR (G_[0,60](d >= 0.4))`
- Parameters: `{"avoidance_horizon_steps":60,"avoidance_threshold":0.4,"d_safe":0.75,"d_warn":0.55,"deadline_steps":100}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.75},"interval":{"inclusive":true,"lower":0,"upper":100},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"or","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 33. `or-v0-006` — disjunction / structure_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy at least one of these complete requirements: (A) every new entry below 0.30 units from the nearest hazard is followed by recovery to at least 0.45 within 30 steps, including the deadline; or (B) nearest-hazard distance remains at least 0.45 units at every step from 0 through 80, inclusive.
- Paraphrase 1: Require one complete clause or the other: (A) a new below-0.30 warning recovers to 0.45 or farther by 30 inclusive steps, or (B) all samples in [0,80] stay at least 0.45 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.30, safety at 0.45, deadline 30) or the full bounded-avoidance rule (distance at least 0.45 throughout inclusive steps 0 to 80) must have at least one branch hold.
- Gold STL: `(G(e(d < 0.3) -> F_[0,30](d >= 0.45))) OR (G_[0,80](d >= 0.45))`
- Parameters: `{"avoidance_horizon_steps":80,"avoidance_threshold":0.45,"d_safe":0.45,"d_warn":0.3,"deadline_steps":30}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.3},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"interval":{"inclusive":true,"lower":0,"upper":30},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"or","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.45},"interval":{"inclusive":true,"lower":0,"upper":80},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 34. `or-v0-007` — disjunction / structure_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy at least one of these complete requirements: (A) every new entry below 0.40 units from the nearest hazard is followed by recovery to at least 0.55 within 80 steps, including the deadline; or (B) nearest-hazard distance remains at least 0.50 units at every step from 0 through 100, inclusive.
- Paraphrase 1: Require one complete clause or the other: (A) a new below-0.40 warning recovers to 0.55 or farther by 80 inclusive steps, or (B) all samples in [0,100] stay at least 0.50 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.40, safety at 0.55, deadline 80) or the full bounded-avoidance rule (distance at least 0.50 throughout inclusive steps 0 to 100) must have at least one branch hold.
- Gold STL: `(G(e(d < 0.4) -> F_[0,80](d >= 0.55))) OR (G_[0,100](d >= 0.5))`
- Parameters: `{"avoidance_horizon_steps":100,"avoidance_threshold":0.5,"d_safe":0.55,"d_warn":0.4,"deadline_steps":80}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.4},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":80},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"or","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"interval":{"inclusive":true,"lower":0,"upper":100},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________

## 35. `or-v0-008` — disjunction / structure_test

- Author: `Codex_stage2_draft_2026-08-12`
- Online status: `offline_only_pending_feasibility`
- Canonical: The trajectory must satisfy at least one of these complete requirements: (A) every new entry below 0.50 units from the nearest hazard is followed by recovery to at least 0.70 within 60 steps, including the deadline; or (B) nearest-hazard distance remains at least 0.55 units at every step from 0 through 120, inclusive.
- Paraphrase 1: Require one complete clause or the other: (A) a new below-0.50 warning recovers to 0.70 or farther by 60 inclusive steps, or (B) all samples in [0,120] stay at least 0.55 units from the nearest hazard.
- Paraphrase 2: The full bounded-recovery rule (warning under 0.50, safety at 0.70, deadline 60) or the full bounded-avoidance rule (distance at least 0.55 throughout inclusive steps 0 to 120) must have at least one branch hold.
- Gold STL: `(G(e(d < 0.5) -> F_[0,60](d >= 0.7))) OR (G_[0,120](d >= 0.55))`
- Parameters: `{"avoidance_horizon_steps":120,"avoidance_threshold":0.55,"d_safe":0.7,"d_warn":0.5,"deadline_steps":60}`
- Typed AST: `{"left":{"child":{"left":{"node_type":"warning_entry","predicate":{"comparator":"lt","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.5},"trigger_mode":"hysteretic_warning_episode"},"node_type":"implies","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.7},"interval":{"inclusive":true,"lower":0,"upper":60},"node_type":"eventually"}},"interval":null,"node_type":"globally"},"node_type":"or","right":{"child":{"comparator":"ge","node_type":"predicate","signal_id":"nearest_hazard_center_distance_public","threshold":0.55},"interval":{"inclusive":true,"lower":0,"upper":120},"node_type":"globally"}}`

Checklist:

- [ ] object
- [ ] signal
- [ ] operator
- [ ] comparator
- [ ] threshold
- [ ] deadline
- [ ] equality
- [ ] terminal_semantics
- [ ] paraphrase_equivalence

Reviewer name: ____________________

Decision (`approved` / `changes_required`): ____________________

Disagreement/adjudication notes: ________________________________________________
