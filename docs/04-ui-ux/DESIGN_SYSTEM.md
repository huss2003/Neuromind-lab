# Design System
Version 0.1.0. Goal: calm, legible, beginner-friendly interface. Validate contrast before production.

## Principles
One obvious primary action; video and coding are main surfaces; minimal decoration; text plus colour for status; errors must include recovery; no success state before server confirmation.

## Tokens
Background `#F7F8FA`; surface `#FFFFFF`; muted surface `#EEF2F6`; text `#17212B`; muted text `#526171`; border `#D5DDE5`; primary `#2357D9`; primary hover `#1946B8`; success `#16794B`; warning `#8A5700`; danger `#B42318`; focus `#7C3AED`; code background `#111827`.
Typography: system UI stack; monospace code stack; body 16px/1.5; supporting text generally >=14px; headings 28–32px desktop, 24px compact.
Spacing: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64 px. Radius: controls 6px, cards 10px, dialogs 12px. Prefer borders over heavy shadows.

## Components
- App shell: header, side nav, content area.
- Buttons: primary, secondary, tertiary, destructive.
- Status badges: Draft, Published, In progress, Completed, Queued, Running, Passed, Needs retry, Unavailable.
- Video player: 16:9, segment title, progress, checkpoint state, keyboard fallback.
- MCQ: labelled radio options, disabled submit until selection, explanation after server result.
- Coding lab: instructions, Monaco, Run practice, Submit for grading, output, feedback, retry.
- Dialogs: focus management; essential errors remain visible rather than toast-only.

## Layout/responsiveness
Max content width 1440px; side nav 240px on wide screens; editor/output split on desktop and stacked on narrow screens. No ordinary screen horizontal overflow at 360px. Desktop-first coding experience.
Motion 120–180ms; respect reduced-motion.
Accessibility target WCAG 2.2 AA: keyboard operation, focus, labels, contrast, semantic headings, accessible errors, dialog focus, captions/transcripts where feasible.
