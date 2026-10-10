# ADR-0003: chat-small answers every question; no routing to chat-strong yet

## Status

Accepted. Priya and Kwame.

## Context

Model routing sends a question to the small model first and to the strong model when a rule fires. We measured three designs on the same 67 questions with the same search results (measured, 2 passes each): chat-small only 86.6% correct, US$0.00017 a question, p95 3.8 s; chat-strong only 85.8%, US$0.0032, p95 6.6 s; routed (escalate when chat-small declines or a citation check fails) 86.6%, US$0.0008, p95 4.0 s. The misses that remained were search misses (the right passage was not in the top 5) and two contradiction questions: a stronger model cannot fix a missing passage.

## Options

1. chat-small only.
2. chat-strong only: 19 times the cost per question, slower, not better on this set.
3. Routed: 4.8 times the cost per question of chat-small, the same quality on this set.

## Decision

Option 1. Keep the routing code path, switched off, with the escalation rule written down.

## Consequences

- The answer cost stays about US$7 a month in the base scenario.
- Quality work goes to search first (the misses are there).

## Revisit when

- A new question set (a new tenant, harder questions) shows chat-strong at least 5 points better than chat-small, or
- the misses move from search to reasoning (the passage is there and the answer is still wrong).
