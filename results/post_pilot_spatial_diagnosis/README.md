# Post-pilot spatial diagnosis artifacts

This directory contains the compact, reproducible outputs from deterministic
replay of all 15 frozen Stage I final checkpoints over the same 100 evaluation
seeds. No training or checkpoint selection occurred.

- `summary.json`: matrix validation, provenance, layout and aggregate spatial metrics;
- `replay_manifest.json`: source/checkpoint/output hashes and the ignored full-table hash;
- `geometry_schema.json`: row fields and privileged-geometry boundary;
- `representative_geometry.csv`: three preselected cases across all conditions;
- `spatial_density_counts.npz`: compact aggregate grid counts;
- `layout_feasibility.csv`: 100 fixed-layout grid estimates;
- `goal_context_metrics.json`: goal-window exposure versus missed-event proximity;
- three PNG figures plus `figures_manifest.json`.

The 1,501,500-row `full_geometry.csv.gz` is intentionally local and ignored by
Git. Its exact SHA-256, byte count, command and schema are retained in the
manifest. Privileged coordinates are diagnostic only and never enter a policy,
learner cost or language-model input.
