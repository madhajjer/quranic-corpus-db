---
name: dependency-graph-project
description: Active effort to recreate corpus.quran.com dependency graphs locally from EQTB data; state lives in repo HANDOFF.md
metadata:
  type: project
---

As of 2026-07-19: reconstructing corpus.quran.com dependency graphs locally in the
quranic-corpus-morphology-0.4 repo. Full state, established research facts (morphology
0.4 has no syntax; qurancorpus.app API dead; EQTB dataset chosen and downloaded to
`eqtb/`), and next steps are in the repo's **HANDOFF.md** — read it first, don't
re-research those points. Next task: inspect `eqtb/Quranic.csv` (43-col, likely UTF-16
TSV), then build `build_treebank.py` loader + SVG renderer. Work continues in
[[wsl-python-environment]].
