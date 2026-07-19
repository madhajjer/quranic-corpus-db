---
name: use-explore-subagents
description: User wants exploration subagents used for research in Fable sessions
metadata:
  type: feedback
---

The user asked to "use exploration subagents for fable session" when I was doing web
research inline.

**Why:** keeps the main (Fable) context lean; parallel Explore agents handle broad
fan-out research faster and cheaper.

**How to apply:** in this project, when a task needs multi-source web/code research,
spawn Explore subagents (parallel where independent) instead of fetching page-by-page
in the main session.
