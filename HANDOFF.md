# HANDOFF — Recreate corpus.quran.com dependency graphs locally

**Date:** 2026-07-19. **Status:** research done, data acquired. Next step: build the SQLite loader + renderer.
**This repo was recloned into WSL at `~/hajir`** (Windows Python was a WindowsApps stub
with no permission — do Python work in WSL from now on). See `.agent-memory/` in this repo
for full session memory (also readable by Claude Code automatically); it was moved here
from the Windows-side memory store since that store won't follow the reclone.

## Goal
Reconstruct the syntactic dependency graphs from
<https://corpus.quran.com/documentation/dependencygraph.jsp> locally — data in SQLite next to the
existing `quran_morphology.db`, plus a local renderer producing the same style of graph
(Arabic tokens right-to-left, colored POS, curved labeled arcs like فاعل / مفعول به, phrase
nodes, hidden/elided words).

## Established facts (do not re-research)

1. **`quranic-corpus-morphology-0.4.txt` contains NO syntax.** Only per-token morphology.
   The dependency graphs come from the separate Quranic Treebank (QADT), which was **never
   bulk-released** — corpus.quran.com only serves server-rendered PNGs
   (`https://corpus.quran.com/graphimage?id=N` works, returns image/png; no JSON API there).

2. **The modern API is dead.** The open-source frontend
   [github.com/kaisdukes/quranic-corpus](https://github.com/kaisdukes/quranic-corpus) called
   `https://qurancorpus.app/api` (endpoints `/syntax?location=1:1&graph=0`, `/morphology`,
   `/morphology/word`, `/metadata`, `/irab`) — that domain is now a parked "for sale" page.
   Kais Dukes' repos deliberately don't ship treebank data.

3. **Chosen data source: Extended Quranic Treebank (EQTB), 2025** — re-derives and completes
   the treebank to **100% Quran coverage**, machine-readable. Downloaded into `eqtb/` here.
   - GitHub mirror (MIT): <https://github.com/NoorBayan/Quranic> (`corpus/Quranic.rar`,
     `corpus/RelLabels.csv`, `corpus/pos.csv`)
   - Canonical (CC BY 4.0, citable): Mendeley DOI `10.17632/rk96pn66m4.1`
     <https://data.mendeley.com/datasets/rk96pn66m4/1>
   - Paper: "A complete, multi-layered quranic treebank dataset with hybrid syntactic
     annotations" (Data in Brief 2025, DOI `10.1016/j.dib.2025.111940`, PMC12361616).
   - Caveat: syntax layer is parser-generated + expert-validated, not fully gold-standard.

## Local data (`eqtb/`)

| File | What | Notes |
|---|---|---|
| `Quranic.csv` | Full 43-column table, ~132,736 tokens, whole Quran | 57 MB, extracted from the rar, **gitignored** — re-extract from `Quranic.rar` if missing (`unrar x Quranic.rar` or WinRAR at `C:\Program Files\WinRAR\UnRAR.exe`) |
| `Quranic.rar` | Compressed original (tracked in git) | 4 MB |
| `RelLabels.csv` | Dependency relation lexicon: `rel_en`/`rel_ar` + display colors | e.g. gen/مجرور, Pred/خبر |
| `pos.csv` | POS tag set | |

**Not yet inspected** (blocked when Windows Python failed): column layout of `Quranic.csv`
and file encodings. Sources report: possibly **UTF-16**, tab-separated, 43 columns =
9 orthographic + 21 morphological + 7 syntactic (+ aux): dependency edges via
`rel_label` + `ref_token_id`, constituency via `is_constituent`/`constituent_position`/
`constituent_label`, and resolved elided words (TAQDIR). **First task in WSL: check BOM,
dump header + a few rows, and verify against verse 1:1.**

## Reference: original graph wire format (for renderer fidelity)

From the open-source frontend (types in `src/corpus/syntax/`):

```ts
Graph { graphNumber, graphCount, legacyCorpusGraphNumber, prev?, next?,
        words: Word[], edges: Edge[], phraseNodes?: PhraseNode[] }
Word  { type: 'token'|'reference'|'elided', token?, elidedText?, elidedPosTag?,
        startNode, endNode }            // token.segments[] are the sub-word nodes
Edge  { startNode, endNode, dependencyTag }   // 46 tags: subj, obj, gen, poss, conj, …
PhraseNode { startNode, endNode, phraseTag }  // 'S'|'NS'|'VS'|'CS'|'PP'|'SC'
```

Node numbering: flat integer index over all word segments; `node >= segmentNodeCount`
means phrase node `phraseNodes[node - segmentNodeCount]`. `subjx`/`predx` get special
Arabic subject/predicate labels.

**Layout algorithm to port** (framework-agnostic geometry) lives in that repo:
`src/layout/syntax-graph-visualizer.ts`, `graph-layout.ts`, `height-map.ts`,
`geometry.ts`; SVG rendering in `src/treebank/syntax-graph-view.tsx`, `arc-arrow.tsx`,
`svg-arabic-token.tsx`. Arabic relation-name map (46 tags → Arabic) is in
`src/corpus/syntax/syntax-service.ts`.

## Plan (next session)

1. Inspect `eqtb/Quranic.csv` (encoding, delimiter, header, 43 columns); map columns to the
   Graph model above.
2. `build_treebank.py` (pure stdlib, same style as `convert_corpus.py`): parse EQTB →
   new tables in a `quran_treebank.db` (or added to `quran_morphology.db`):
   `graph_words(sura, verse, word, token, type, arabic, pos, elided_text, node_id)`,
   `graph_edges(dependent_node, head_node, rel_en, rel_ar)`,
   `graph_phrases(node_id, start_node, end_node, tag)`, plus `rel_labels` from
   `RelLabels.csv`. Key on `(sura, verse, word, token)` to join the existing morphology
   tables.
3. `render_graph.py`: given `sura:verse`, emit standalone SVG/HTML dependency graph
   (RTL baseline of Arabic tokens w/ POS colors from `RelLabels.csv`/`pos.csv`, arcs
   below with Arabic labels, elided words in grey, phrase brackets). Port layout ideas
   from the frontend's `src/layout/`; a simpler arc-height stacking (HeightMap-style) is fine.
4. Validate a few graphs against corpus.quran.com PNGs (`/graphimage?id=N`) for e.g. 1:1–1:7.
5. Follow repo conventions: pure stdlib, idempotent DROP/CREATE builds, paths relative to
   script (`WORKSPACE_DIR`), update README.md + README.en.md together, keep Colab
   notebooks in sync if touched.
