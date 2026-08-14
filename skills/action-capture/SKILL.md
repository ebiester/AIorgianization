---
name: action-capture
description: Capture substantive follow-up work in AIorgianization with an actionable title and enough Markdown context to resume it later. Use whenever a conversation, coding session, review, meeting, or investigation creates a commitment, unresolved decision, blocker, handoff, or next action that should persist in the Obsidian vault.
---

# Action Capture

Persist work that would otherwise disappear into the chat. Prefer doing the capture over merely suggesting that the user create a note.

## Capture workflow

1. Detect a capture trigger: an agreed follow-up, pending decision, blocker, handoff, or a clear next action left after work stops.
2. Write a specific, verb-led title describing the next observable action. Use `Send revised rollout wording to Sam`, not `Rollout` or `Follow up`.
3. Write concise Markdown notes that allow a fresh person to resume. Include only relevant items:
   - **Why:** outcome or reason the task exists.
   - **Current state:** what is done and what remains.
   - **Decision/constraint:** settled choices, boundaries, or risks.
   - **Next action:** the first concrete step.
   - **References:** paths, URLs, PRs, issue IDs, or people when known.
4. Call `aio_add_task` with `title`, `notes`, and any known `due`, `project`, `status`, or `assign` values. If working without MCP, run `aio add "<title>" --notes "<notes>"`.
5. Confirm the saved title and ID in one short sentence. Do not duplicate the full note in chat.

## Rules

- Capture automatically for substantive work; do not wait for the user to explicitly ask for a task.
- Keep trivial, self-evident tasks short. Add notes whenever future context, a decision, a reference, or a handoff matters.
- Preserve facts from the conversation. Clearly label uncertainty rather than inventing missing details.
- Do not create a task for work already completed unless a distinct follow-up remains.
- When several independent actions exist, create separate tasks with their own next actions.

## Example

```text
title: Send security approval options to Sam
notes: |
  - Why: Security approval is blocking the September rollout.
  - Current state: The phased rollout remains the plan; legal wording is open.
  - Next action: Send the two wording options and request approval by Thursday.
  - References: docs/rollout.md, PR #482, Slack thread with Sam (14 Aug).
```
