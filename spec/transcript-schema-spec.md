# Claude Code transcript JSONL — schema spec v0.1

**Spec version:** `0.1.0`  
**Status:** draft, observation-grounded  
**Source:** [`coo-memory/coo/instruments/_runs/2026-05-21_transcript-schema-extractor.md`](https://github.com/coo-labs/coo-memory/blob/main/coo/instruments/_runs/2026-05-21_transcript-schema-extractor.md) §"Draft hierarchical schema spec — v0.1", lifted into this repo per [coo-labs/coo-logs#381](https://github.com/coo-labs/coo-logs/issues/381).

This is a community-authored, observation-grounded spec for the on-disk JSONL transcript format Claude Code writes to `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`. Anthropic does not publish a per-line schema; this spec exists to document the de-facto shape that has converged across community parsers and across the VADE R2 transcript archive.

The spec is **descriptive, not prescriptive**: it tracks observed reality. When reality changes, the spec bumps (see §"Versioning convention").

---

## 1. Hierarchy

The format is hierarchical because the lines are hierarchical:

```
top-level line       (discriminator: type)
└── message          (when present, on assistant + user)
    └── content[]    (discriminator: type)
        ├── text
        ├── thinking         (assistant only)
        ├── tool_use         (assistant only)
        │   └── input        (discriminator: name; per-tool sub-schema)
        └── tool_result      (user only)
└── attachment       (discriminator: type, on attachment lines)
    └── (per-type payload — see §6)
└── usage            (on assistant turns, inside message)
```

Each named level below carries its own required/optional split. Field-level requireds are grounded in the empirical sample (the R2 8-session, 2015-line drift extraction from 2026-05-04 → 2026-05-21). Per-tool input sub-schemas are an extension point keyed on `tool_use.name`.

---

## 2. Envelope (every line)

Two fields are guaranteed present on every observed line shape:

| Field | Type | Notes |
|---|---|---|
| `type` | string | Closed enum discriminator. See §3. |
| `sessionId` | string | UUID. Stable across resume; matches the file name. |

All other fields are per-type required or optional.

---

## 3. Top-level types (closed enum, v0.1)

| Type | Empirical | Role |
|---|---|---|
| `assistant` | R2 (174/174) | Model output turn |
| `attachment` | R2 (172/174) | Side-channel content surfaced into the transcript |
| `user` | R2 (174/174) | User-side input (typed + tool result + meta) |
| `system` | R2 (44/174) | System events (compact, hook, stop summary) |
| `last-prompt` | R2 (105/174) | Pointer to the leaf prompt for resume |
| `queue-operation` | R2 (88/174) | Queued-command bookkeeping |
| `pr-link` | R2 (3/174) | Emitted by the harness after `gh pr create`; carries the new PR's number, URL, and repo. See §5.7. |
| `agent-name` | [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) | Subagent name registration |
| `custom-title` | [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) | User-set session name |
| `file-history-snapshot` | [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) + simonw spec | Checkpoint file backup |
| `permission-mode` | [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) | Permission mode change |

Validators MUST recognize all eleven as known top-level types in v0.1. The four sourced only from issue #53516 carry minimal field detail; future observation passes against broader samples fill those in.

**Contributor on-ramp.** If your parser sees a `type` value not in this enum, that's a spec gap. Open an issue with one or two example lines (redact sensitive content) or PR the type directly per [CONTRIBUTING.md](../CONTRIBUTING.md#c-adding-a-new-top-level-event-type). The four issue-#53516-only types are documented at envelope level only — PRs that fill in their per-field tables from a real observation are exactly what the spec needs.

---

## 4. Common-rich fields (present on `assistant`, `attachment`, `user`)

Twelve fields are present on every observed line of these three types:

| Field | Type | Notes |
|---|---|---|
| `type` | string | See §3 |
| `sessionId` | string | See §2 |
| `uuid` | string | Line-level UUID. Used by parsers for DAG reconstruction |
| `parentUuid` | string \| null | Parent line's uuid, or null at session root. **Known-corruptable**: [anthropics/claude-code#22526](https://github.com/anthropics/claude-code/issues/22526). Treat the parent-chain as best-effort, not invariant. |
| `timestamp` | string | ISO-8601 UTC |
| `cwd` | string | Absolute path; round-trippable to the `encoded-cwd` directory name |
| `entrypoint` | string | How the session was started (`claude --resume`, `cloud`, etc.). **Stable across resume** — not re-set on resume. |
| `gitBranch` | string | Repo branch at the moment of the event |
| `isSidechain` | boolean | True when the event belongs to a subagent transcript |
| `userType` | string | `external` (typed-in) vs other internal categories |
| `version` | string | Claude Code version (e.g. `2.1.140`) |
| `message` | object | Present on `assistant` + `user`; see §5 |

**Common-rich envelope optionals** (observed on multiple top-level types):

| Field | Type | Notes |
|---|---|---|
| `slug` | string | Session slug; the cute-name identifier (e.g. `boot-up-coo-identity-golden-bird`). Present on assistant + user + attachment + system on newer Claude Code versions; optional on older. |
| `isMeta` | boolean | True for harness-generated events (not user-typed). Also on `system`. |
| `logicalParentUuid` | string | Logical parent override for `compact_boundary` and related events; distinct from `parentUuid`. |

---

## 5. Per-type field tables

### 5.1 `assistant`

**Required:** envelope + common-rich (above) + `message`.

`message` shape:

```
message:
  id: string                  — Anthropic message ID
  type: "message"
  role: "assistant"
  model: string               — model identifier (e.g. "claude-opus-4-7-20251202")
  content: array              — see §7
  stop_reason: string|null    — "end_turn", "tool_use", "max_tokens", etc.
  stop_sequence: string|null
  usage: object               — see §8
```

**Optional envelope fields (observed):**

| Field | Type | Notes |
|---|---|---|
| `agentId` | string | Present on subagent assistant lines (correlated with `isSidechain == true`) |
| `attributionAgent` | string | Subagent type that wrote the message |
| `attributionSkill` | string | Skill that was active when the message was written |
| `requestId` | string | Anthropic request ID |
| `isApiErrorMessage` | boolean | True when the assistant line carries an API-error surrogate (rare; v2.1.x added) |
| `error` | object | Companion to `isApiErrorMessage`; the error payload from the API |

### 5.2 `user`

**Required (12 fields):** `type, sessionId, uuid, parentUuid, timestamp, cwd, entrypoint, gitBranch, isSidechain, message, userType, version`.

`message.role` is always `"user"`. `message.content[]` blocks observed: `text`, `tool_result`.

**Optional envelope fields (observed):**

| Field | Type | Notes |
|---|---|---|
| `promptId` | string | Stable prompt-side identifier; sticky across resume |
| `agentId` | string | Subagent context (correlated with `isSidechain == true`) |
| `isMeta` | boolean | True for harness-generated events (not user-typed) |
| `mcpMeta` | object | Present on user lines wrapping MCP tool results |
| `origin` | object | Provenance of the user event |
| `permissionMode` | string | Permission mode at the time of the event |
| `sourceToolAssistantUUID` | string | Correlation back to the assistant `tool_use` line |
| `sourceToolUseID` | string | Sibling correlation field (newer ID shape) |
| `toolUseResult` | object | Pre-extracted tool_result payload (sibling to `message.content[].tool_result`) |

### 5.3 `attachment`

**Required:** envelope + common-rich + `attachment`.

`attachment` shape:

```
attachment:
  type: string  — closed enum (see §6)
  ...           — per-type payload (see §6)
```

### 5.4 `last-prompt`

```
type: "last-prompt"
sessionId: string
leafUuid: string             — UUID of the leaf prompt to resume to
lastPrompt: string (optional) — the prompt text (when present)
```

### 5.5 `queue-operation`

```
type: "queue-operation"
sessionId: string
timestamp: ISO-8601
operation: string            — "enqueue" / "dequeue" / etc.
content: any (optional)      — operation payload
```

### 5.6 `system`

**Required:** envelope + common-rich + `subtype`.

```
subtype: string  — discriminator. Closed enum (see below).
level:   string  — severity bucket. Observed values: "info", "suggestion".
```

`system.subtype` known values:

| Subtype | Source | Notes |
|---|---|---|
| `away_summary` | [#53516](https://github.com/anthropics/claude-code/issues/53516) | Synthesized "while you were away" digest. |
| `bridge_status` | [#53516](https://github.com/anthropics/claude-code/issues/53516) | Web/cloud bridge connectivity status. |
| `compact_boundary` | R2 | Compaction event; payload carries `compactMetadata` (see below). |
| `local_command` | [#53516](https://github.com/anthropics/claude-code/issues/53516) | Slash-command echo / local-command marker. |
| `scheduled_task_fire` | [#53516](https://github.com/anthropics/claude-code/issues/53516) | Scheduled-task hook fire. |
| `stop_hook_summary` | R2 | Stop-hook batch summary; payload carries `hookCount`, `hookErrors`, `hasOutput`, `preventedContinuation`, `stopReason`, `toolUseID`. |
| `turn_duration` | [#53516](https://github.com/anthropics/claude-code/issues/53516) | Wall-clock turn duration metric. |
| `hook_callback` | [#53516](https://github.com/anthropics/claude-code/issues/53516) | Generic hook-callback marker. |

Observed `system` envelope optionals:

| Field | Type | Notes |
|---|---|---|
| `toolUseID` | string | Correlates a system event to its triggering tool (subtype `stop_hook_summary`, `hook_callback`). |
| `hookCount` | integer | Total hooks in the batch (subtype `stop_hook_summary`). |
| `hookErrors` | array | Per-hook error strings (subtype `stop_hook_summary`). |
| `hookInfos` | array | Per-hook info records (subtype `stop_hook_summary`). |
| `hasOutput` | boolean | True when at least one hook emitted output (subtype `stop_hook_summary`). |
| `preventedContinuation` | boolean | True when a hook blocked continuation (subtype `stop_hook_summary`). |
| `stopReason` | string | Stop-reason text (subtype `stop_hook_summary`). |
| `content` | string | Subtype payload prose (some subtypes). |
| `compactMetadata` | object | `{durationMs, preTokens, postTokens, trigger, preCompactDiscoveredTools}` (subtype `compact_boundary`). |

### 5.7 `pr-link`

```
type:         "pr-link"
sessionId:    string
prNumber:     integer
prUrl:        string  — full GitHub PR URL
prRepository: string  — "owner/repo" form
timestamp:    ISO-8601
```

Emitted by the local harness after the user runs `gh pr create`; purely cosmetic surfacing. Downstream analysis tooling that walks for tool-use density should ignore this type.

### 5.8 `agent-name`, `custom-title`, `file-history-snapshot`, `permission-mode`

v0.1 names these from the community enumeration ([anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516)); per-type field tables are filled by subsequent observation passes that exercise them. A validator under v0.1 MUST NOT flag these as unknown event types, even when the per-field detail is empty.

---

## 6. `attachment.type` (closed enum, v0.1)

Twenty-one values observed across the 174-session v0 sample:

| `attachment.type` | Payload status in v0.1 |
|---|---|
| `command_permissions` | Opaque `object`. To be filled in v1. |
| `compact_file_reference` | `{displayPath, filename}` — file referenced inside a compact prompt. |
| `date_change` | `{newDate}` — emitted when the wall-clock date crosses midnight during a session. |
| `deferred_tools_delta` | Opaque `object`. To be filled in v1. |
| `dynamic_skill` | Opaque `object`. To be filled in v1. |
| `edited_text_file` | Opaque `object`. To be filled in v1. |
| `file` | `{content, displayPath, filename}` — file content surfaced into the transcript (typically a Read-style result). |
| `hook_additional_context` | `{content, hookEvent, hookName, toolUseID}` — additional context appended by a hook's `hookSpecificOutput.additionalContext`. |
| `hook_blocking_error` | `{blockingError, hookEvent, hookName, toolUseID}` — hook returned a deny/block decision. |
| `hook_non_blocking_error` | `{command, durationMs, exitCode, hookEvent, hookName, stderr, stdout, toolUseID}` — hook errored but did not block. |
| `hook_success` | **Fully specified — see §6.1** (closes the per-payload gap [coo-labs/coo-logs#381](https://github.com/coo-labs/coo-logs/issues/381) listed as the falsifier blocker). |
| `hook_system_message` | `{content, hookEvent, hookName, toolUseID}` — system-channel hook message. |
| `nested_memory` | Opaque `object`. To be filled in v1. |
| `plan_file_reference` | `{planContent, planFilePath}` — references a plan file from plan-mode. |
| `plan_mode` | `{isSubAgent, planExists, planFilePath, reminderType}` — plan-mode reminder injection. |
| `plan_mode_exit` | `{planExists, planFilePath}` — plan-mode exit event. |
| `queued_command` | Opaque `object`. To be filled in v1. |
| `skill_listing` | Opaque `object`. To be filled in v1. |
| `task_status` | Opaque `object`. Surfaces task/todo state changes. |
| `todo_reminder` | Opaque `object`. To be filled in v1. |
| `ultrathink_effort` | `{}` (empty payload) — marker that an "ultrathink" effort tier was selected. |

**Contributor on-ramp.** Eight values above are still opaque. If you've seen a real instance of `command_permissions`, `deferred_tools_delta`, `dynamic_skill`, `edited_text_file`, `nested_memory`, `queued_command`, `skill_listing`, or `todo_reminder`, please PR the payload table — the `hook_success` pattern below (§6.1) is the template. See [CONTRIBUTING.md §A](../CONTRIBUTING.md#a-adding-a-new-attachmenttype-payload).

### 6.1 `attachment.hook_success` payload

Observed shape (all 10 fields present on every observed instance — including all 8 SessionStart hooks in the v0 reference session):

| Field | Type | Notes |
|---|---|---|
| `type` | string | Always `"hook_success"` |
| `hookName` | string | Composite name in the form `<HookEvent>:<matcher>` (e.g. `SessionStart:startup`, `PreToolUse:Bash`) |
| `toolUseID` | string | Correlates one hook batch to the triggering tool/event |
| `hookEvent` | string | Bare hook event name; one of `SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `Notification` (full set per Claude Code docs) |
| `content` | string | Processed payload that lands in the transcript surface |
| `stdout` | string | Raw hook stdout |
| `stderr` | string | Raw hook stderr |
| `exitCode` | integer | Hook exit code (0 = success in practice; hook_success implies 0 but the field is always present) |
| `command` | string | The shell command the harness ran |
| `durationMs` | integer | Wall-clock duration of the hook in ms |

**Resume-firing semantics.** When `SessionStart` fires N times across a session's lifetime (initial start + each resume), the transcript holds N distinct `toolUseID` values across the `hook_success` attachments with `hookEvent == "SessionStart"`. Multiple hooks per `toolUseID` are normal (one SessionStart event triggers every registered SessionStart hook); distinct `toolUseID`s mean distinct SessionStart events. This is the discriminator the acceptance-falsifier query uses.

---

## 7. Content blocks

`message.content[]` on `assistant` and `user` carries discriminated blocks.

### 7.1 On `assistant`

| Block `type` | Shape |
|---|---|
| `text` | `{type: "text", text: string}` |
| `thinking` | `{type: "thinking", thinking: string, signature?: string}` |
| `tool_use` | `{type: "tool_use", id: string, name: string, input: object}` |

### 7.2 On `user`

| Block `type` | Shape |
|---|---|
| `text` | `{type: "text", text: string}` |
| `tool_result` | `{type: "tool_result", tool_use_id: string, content: string \| array, is_error?: boolean}` |

---

## 8. `usage` block (on `assistant` lines, inside `message`)

```
usage:
  input_tokens:              integer
  output_tokens:             integer
  cache_creation_input_tokens: integer
  cache_read_input_tokens:   integer
  server_tool_use:           object  (optional, newer)
  service_tier:              string  (optional, newer)
```

Sometimes accompanied at the envelope level by:

```
costUSD: float (optional, NOT TRUSTED — see axis 3 ccusage hedge)
```

---

## 9. `tool_use.input` per-name sub-schemas

The spec treats `tool_use.input` as an **extension point keyed on `tool_use.name`**, not a single shape. The validator ships a *registry* of known built-in tool names and validates input shapes against the SDK's input types ([Claude Code SDK Tool Input Types](https://code.claude.com/docs/en/agent-sdk/typescript#tool-input-types)). MCP tool names (`mcp__<server>__<action>`) are valid by pattern; their input shapes are the MCP server's responsibility, not this spec's.

| Tool name pattern | Source of truth for input shape |
|---|---|
| Built-in: `Bash`, `Read`, `Edit`, `Write`, `Glob`, `Grep`, `Agent`, `Skill`, `TodoWrite`, `WebFetch`, `WebSearch`, `Monitor`, `AskUserQuestion`, `ToolSearch`, `NotebookEdit`, `MultiEdit`, `Task`, `SendUserFile`, `PushNotification`, `ExitPlanMode` | Claude Code SDK type definitions + R2-observed inputs |
| `mcp__<server>__<action>` | Generic `{any: any}`; per-server schema lives in the MCP server |

The validator reports `unknown_tool_names` when it encounters a `tool_use.name` outside the registry and outside the MCP pattern.

**Contributor on-ramp.** When Claude Code ships a new built-in tool, add it to `BUILTIN_TOOL_NAMES` in [`src/tjsonl/_spec.py`](../src/tjsonl/_spec.py) and to the table above. See [CONTRIBUTING.md §B](../CONTRIBUTING.md#b-adding-a-new-built-in-tool_usename).

---

## 10. Validation report shape

A validator that walks a jsonl against this spec MUST emit the following report keys (per [coo-labs/coo-logs#381](https://github.com/coo-labs/coo-logs/issues/381) deliverable list):

| Key | Description |
|---|---|
| `unknown_event_types` | Top-level `type` values not in §3 |
| `missing_required_fields` | Required fields per §5 absent on a line, with line numbers |
| `unknown_optional_fields` | Envelope fields seen but not enumerated in §5 (signal for spec drift) |
| `unknown_attachment_types` | `attachment.type` values not in §6 |
| `unknown_tool_names` | `tool_use.name` values not in §9's registry and not matching the MCP pattern |
| `unparseable_json` | Count of lines that failed `json.loads` |

The validator exits 0 on a clean report; exits 1 if any of the above buckets is non-empty.

---

## 11. Versioning convention

- `schema_version` at the spec-document level — bumped on every published change.
- Per-event-type semver embedded in the spec body, ratcheted by the rules:
  - Field add at *required* → major bump
  - Field add at *optional* → minor bump
  - Field rename or removal at any level → major bump
  - New top-level type → minor bump
  - New `content[]` block type → minor bump
  - New `attachment.type` value → minor bump
  - New `tool_use.name` in the built-in registry → minor bump (MCP names don't count; they're per-server)

The drift-diff tool (planned for v0.2) reports which rule was hit and proposes the version bump. A human merges the spec PR that records it.

### Deprecation policy (the promise to consumers)

Once a field name or enum value lands in the spec at minor `0.N.M`, we will not remove or rename it in any subsequent minor or patch version of `0.N.*`. Major-version bumps (`0.N` → `0.(N+1)`, or eventually `0.X` → `1.0`) follow a one-minor-version deprecation window:

- The old shape stays documented as `deprecated` for at least one minor release.
- The new shape is supported in parallel for that window.
- The validator emits a `deprecated_fields` bucket (post-v0.2) so consumers can plan migration.
- The `CHANGELOG.md` is the source of truth for what changed and when.

Peer parsers can pin to a minor version with the expectation that no required field disappears, no enum value evaporates, and no envelope key is silently renamed within that line.

---

## 12. Known bounds

1. **Five top-level types unseen in the v0 sample** (`system`, `agent-name`, `custom-title`, `file-history-snapshot`, `permission-mode`) carry no per-field detail in v0.1. Each is named so validators don't flag it as unknown; per-field tables fill in on future observation passes.
2. **`attachment.<type>.payload` per-type sub-schemas are deliberately left as `object`** in v0.1 for eight of the nine observed `attachment.type` values. `hook_success` is the exception (§6.1) because it is the acceptance-falsifier's blocker.
3. **`parentUuid` corruption is a real Claude Code bug** ([anthropics/claude-code#22526](https://github.com/anthropics/claude-code/issues/22526)). Downstream tools that reconstruct conversation DAG MUST handle the corruption case.
4. **MCP tool inputs are NOT in spec scope.** The spec acknowledges them with the `mcp__<server>__<action>` pattern but defers the input schema to the MCP server's documentation.

---

## 13. Read trail

- [coo-labs/coo-logs#381](https://github.com/coo-labs/coo-logs/issues/381) — implementation issue this spec ships with.
- [coo-labs/coo-memory#864](https://github.com/coo-labs/coo-memory/pull/864) — the merged proposal this spec lifts from.
- [anthropics/claude-code#53516](https://github.com/anthropics/claude-code/issues/53516) — community schema-stability ask; engagement point post-merge.
- [simonw/claude-code-transcripts DeepWiki "JSONL Format"](https://deepwiki.com/simonw/claude-code-transcripts/5.1-jsonl-format) — clean-room community spec aligned with this one.
