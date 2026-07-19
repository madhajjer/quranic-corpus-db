---
name: dependency-graph-project
description: Active effort to recreate corpus.quran.com dependency graphs locally from EQTB data; state lives in repo HANDOFF.md
metadata:
  type: project
---

As of 2026-07-19: reconstructing corpus.quran.com dependency graphs locally in the
quranic-corpus-morphology-0.4 repo. Full state, established research facts (morphology
0.4 has no syntax; qurancorpus.app API dead; EQTB dataset chosen and downloaded to
`eqtb/`), and progress are in the repo's **HANDOFF.md** — read it first, don't
re-research those points. DONE: `build_treebank.py` (→ `quran_treebank.db`, validated
100% join vs morphology db) and first-pass `render_graph.py` (SVG). NEXT: visual
validation vs corpus.quran.com PNGs + layout polish + README updates (see HANDOFF
"Progress" section). Work continues in [[wsl-python-environment]].
