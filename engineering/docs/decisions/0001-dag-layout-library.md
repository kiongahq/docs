---
description: Lay out pipeline dependency graphs in the console with vendored Dagre and Kionga's own accessible SVG renderer.
status: "superseded"
date: 2026-10-09
---

# 0001 Lay out pipeline graphs with Dagre and a Kionga SVG renderer

## Current status

The React frontend supersedes the browser-script implementation described below.
`platform/frontend/components/ui/GraphCanvas.tsx` now provides React Flow
interaction, while `platform/frontend/features/operations/ExecutionGraph.tsx`
derives execution layout from the recorded dependencies. The earlier decision
remains here as design history; its vendored assets and tests have been removed.

## Context and problem statement

The console shows each pipeline definition and run as a dependency graph with live
step status. Graphs range from a few nodes to about 200. The console is plain
JavaScript embedded in the gateway binary with no build step. Which library should
compute the layout, and who should own rendering and interaction?

## Decision drivers

- Readable automatic layout for small and large DAGs.
- Zoom, pan, fit-to-view and a legend.
- Status shown without relying on color alone.
- Keyboard selection of nodes.
- Drawn edges that match the persisted dependencies exactly.
- Works offline.
- No bundler: the library must load as a classic script.

## Considered options

- Dagre
- ELK.js
- Cytoscape.js
- React Flow (`xyflow`)
- Mermaid

## Decision outcome

Chosen option: **Dagre**, because it is the only option that gives layered DAG layout as
a small dependency-free classic script while leaving rendering, accessibility and
interaction under Kionga's control.

`@dagrejs/dagre` 2.0.0 (MIT) was vendored with an integrity hash. A gateway browser script supplied Kionga's SVG renderer.

### Consequences

- Good, because edges are generated only from each node's `depends_on`. A property
  test renders random DAGs with and without Dagre and asserts that the drawn edges
  equal the dependency set.
- Good, because layout is presentation only. The gateway validates the graph and owns
  execution order; Dagre cannot reorder or schedule jobs.
- Good, because the graph still renders without Dagre, or for a cyclic draft, using a
  dependency-layer fallback layout, so the graph and its warnings remain visible.
- Neutral, because interaction (zoom, pan, fit, roving-tabindex keyboard navigation)
  is Kionga code in `KiongaPipelineGraph.enhance()` and must be maintained here.

### Confirmation

The former graph test suite ran random-DAG edge property tests and interaction tests in `jsdom`. The former vendor-integrity gate checked pinned asset hashes. Current graph tests live in `platform/frontend/tests/graph.test.ts`.

## Pros and cons of the options

### Dagre

Layered layout for directed graphs, about 42 KB, no dependencies.

- Good, because it works as a classic script with no bundler.
- Good, because it computes layout only, so Kionga controls rendering and
  accessibility.
- Bad, because zoom, pan and keyboard navigation have to be written by hand.

### ELK.js

- Good, because its layered layouts are excellent for large graphs.
- Bad, because it is about 1.5 MB and needs an asynchronous worker setup, which is
  heavier than graphs of up to 200 nodes need.

### Cytoscape.js

A full graph toolkit with its own renderer.

- Bad, because its canvas renderer makes accessible, keyboard-navigable nodes harder.
- Bad, because it is larger.

### React Flow (`xyflow`)

A polished node editor.

- Bad, because it requires React and a bundler, which the console deliberately
  avoids.

### Mermaid

Text-to-diagram rendering.

- Bad, because its output is static: no node selection and no live status.

## More information

The library was vendored with the versioned pipeline DAG work in the `platform`
repository (commit `6847578`, 2026-10-09). See
[execution and serving](../components/execution.md#pipeline-runner) for how the
validated graph reaches the runner.
