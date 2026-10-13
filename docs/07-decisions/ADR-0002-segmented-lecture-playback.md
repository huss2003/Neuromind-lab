# ADR-0002: Data-driven segmented lecture player
Status: Accepted | Date: 2026-10-13

## Context
Each lecture must sequence theory, MCQs/results, practical video, exercise and grading. Timestamp-only control of long video is brittle and media APIs vary.

## Decision
Represent lesson as ordered segment/action data. Use separate media segments at major transitions. Use HTML5-compatible playback where `ended` drives transitions. Persist segment/checkpoint state server-side. Test Drive embedded playback but do not rely on undocumented iframe events. Provide accessible fallback controls.

## Alternatives
One long timestamped video: harder to maintain after edits.
Bespoke page per lecture: 104 separate implementations.
Segmented data-driven player: selected.

## Consequences
More assets/configuration, but easier to test, replace and scale.
