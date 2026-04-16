# cc-relay Phase 1 — Extraction Plan

> Fork context: this repo began as a fork of `joewongjc/feishu-claude-code` (MIT, 2026-04-14, 71 ★). Upstream remains `upstream/main`.
>
> Phase 0 memo: `~/.claude/memory/plans/2026-04-16-cc-relay-phase0-memo.md`

## Goal

Transform a single-platform Feishu bot into a multi-adapter relay daemon:

- **Phase 1** (this repo): Extract `relay_core` from `claude_runner.py`. Keep Feishu working via a `feishu_adapter`. Get "phone → Feishu → local claude CLI → Feishu card" roundtrip.
- **Phase 2**: Add `discord_adapter` — deprecates the old claude-op Discord bot.
- **Phase 2.5** (later): `myserver_adapter` for self-hosted deployments; file-locked `~/.claude/projects/` for multi-machine runs.

## File-level refactor map

| Current | Action | Target |
|---|---|---|
| `claude_runner.py` (215 lines) | **extract** | `relay_core.py` (claude CLI subprocess + stream-json parse, adapter-agnostic) |
| `main.py` (1039 lines) | **split** | `relay_daemon.py` (event loop, dispatch) + `feishu_adapter/main.py` (Feishu-specific wiring) |
| `feishu_client.py` (336 lines) | **move** | `adapters/feishu_adapter/client.py` |
| `commands.py` (694 lines) | **keep** | commands stay adapter-agnostic; any Feishu card rendering moves to `feishu_adapter` |
| `session_store.py` (675 lines) | **keep** | generic — dual-source session index is already platform-neutral |
| `bot_config.py` (22 lines) | **split** | `relay_config.py` (shared) + `adapters/feishu_adapter/config.py` (Feishu-specific) |
| `handover.py` (83 lines) | **keep** | generic |
| `run_control.py` (74 lines) | **keep** | generic |
| `adapters/relay_interface.py` | **new** | abstract base (`RelayAdapter` protocol) |
| `adapters/feishu_adapter/` | **new** | package wrapping existing Feishu code behind `RelayAdapter` |

## Architecture target

```
┌──────────────────┐        ┌──────────────────┐
│  feishu_adapter  │        │  discord_adapter │   (Phase 2)
│  (inbound/out)   │        │  (inbound/out)   │
└────────┬─────────┘        └────────┬─────────┘
         │  RelayAdapter protocol    │
         └──────────┬────────────────┘
                    ▼
         ┌──────────────────────┐
         │  relay_daemon.py     │   Unified event loop, queue, dispatch
         │  (adapter-agnostic)  │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  relay_core.py       │   claude CLI subprocess + stream-json parse
         │  (ex-claude_runner)  │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │  session_store.py    │   dual-source index (~/.claude + ~/.feishu-claude)
         └──────────────────────┘
```

## Minimum Phase 1 demo (user-action-required)

**Goal**: "Phone → Feishu message → local claude CLI → Feishu card" roundtrip.

Pre-requisites (USER MUST PROVIDE):

- [ ] Feishu app: `FEISHU_APP_ID` + `FEISHU_APP_SECRET` (create via open.feishu.cn)
- [ ] `.env` copy from `.env.example` with real credentials
- [ ] Python 3.11+ runtime
- [ ] `pip install -e .` (or `uv pip install -e .`)
- [ ] Optional: ngrok or public IP for button callbacks

Test case (from Phase 0 memo § 6):

```
1. Send Feishu message: "/new brainstorm: how should cc-relay work?"
2. Relay creates session, invokes: claude --print --output-format stream-json ...
3. Stream output back to Feishu card (update every 20 chars)
4. Card shows: ✅ "Here are three approaches: ..."
5. /resume → list shows: [1] brainstorm (today 14:32)
6. User selects [1] → claude --resume <session-id>
7. Resumed session continues from where it left off
```

## Commit plan (Phase 1)

```
commit 1  (this commit)  fork: add PHASE1_PLAN.md + adapters/ scaffold
commit 2                 refactor: extract relay_core.py from claude_runner.py (no behavior change)
commit 3                 refactor: move Feishu code into adapters/feishu_adapter/ (imports updated)
commit 4                 refactor: add relay_daemon.py unified event loop
commit 5                 feat: smoke test harness (mocked adapter → relay_core roundtrip)
commit 6  (user action)  demo: real Feishu roundtrip, screenshot in assets/
```

Commits 2-5 are Builder-scope work; commit 6 requires real Feishu credentials and manual testing.

## Gotchas (ported from Phase 0 memo § 6)

1. **Subprocess zombies**: relay crash mid-run → claude subprocess hangs. Use process groups + SIGTERM → 5s SIGKILL.
2. **Card update throttling**: Feishu rate-limits PATCH. Batch at 20 chars or 100ms.
3. **WebSocket reconnect**: exponential backoff 1s→2s→4s→...→60s.
4. **`.jsonl` strict format**: one JSON object per line, no trailing newline.
5. **Claude CLI arg order**: `--resume` must come before prompt.
6. **`--include-partial-messages` flood**: buffer at STREAM_CHUNK_SIZE=20.
7. **Session ID collision**: namespace relay sessions (e.g., `feishu-<user_id>-<ts>`) to avoid collision with `~/.claude/projects/` UUIDs.
8. **Multi-machine race**: Phase 1 = single machine. Phase 2.5 needs file locking.

## Non-goals (Phase 1)

- Discord adapter (Phase 2)
- Web dashboard (out of scope)
- Multi-user auth (Phase 1 trusts Feishu's allowlist; add `ALLOWED_USERS` env in Phase 2)
- Metrics/observability beyond stdout logs (deferred)
