# Nova quickstart

Cross-device AI assistant. Wake word → STT → ReAct/Plan → tools → TTS,
spanning laptop and Android as one brain.

## Install

```bash
git clone git@github-personal:vishvam129/nova.git
cd nova
uv sync
uv run nova
```

## First-run flow

1. Tray app comes up; speak the wake phrase ("hey nova").
2. The CLI prints the chosen models for your hardware (see
   `nova.hardware.HardwareDetector`).
3. To pair the Android app, scan the QR code in Settings → Devices.

## Architecture (one screen)

```
+--------------------+        WebSocket        +------------------+
| Android app        | <---------------------> | Laptop daemon     |
| - wake / STT / TTS |                         | - brain (ReAct)   |
| - notifications    |                         | - tools (MCP)     |
| - accessibility    |                         | - memory (CRDT)   |
+--------------------+                         | - safety stack    |
                                              +---------+--------+
                                                         |
                                              local + cloud LLMs
                                              (Ollama / Claude / GPT)
```

Module map:

- `nova.voice/` — wake word, STT, TTS, AEC, barge-in
- `nova.brain/` — LLM clients, ReAct, Plan-and-Execute, hybrid router
- `nova.tools/` — MCP, registry, sandbox, rate limit, builtin/
- `nova.safety/` — policy, redaction, audit, kill switch, speaker verify
- `nova.memory/` — short-term, vector, CRDT sync, episodic, decay
- `nova.server/` — WS hub, pairing, sessions, handoff, remote access
- `nova.mobile/` — Android protocol, accessibility, notifications
- `nova.ui/` — tray, overlay HUD, hotkey, dictation, text chat

## Safety model

Three layers, every tool call passes through all three:

1. **Approval** (`nova.tools.approval`) — per-tool AUTO / QUIET / REQUIRE
   / DENIED, persisted across sessions.
2. **Policy** (`nova.safety.policy`) — path / domain / command /
   tool-name allow / deny lists, evaluated before approval.
3. **Audit** (`nova.safety.audit`) — every accepted call appended to a
   redacted JSONL log with fsync.

Plus: `nova.safety.kill_switch` (panic phrase stops everything),
`nova.safety.redaction` (secrets stripped before they leave the device),
`nova.safety.speaker_verify` (only enrolled voices trigger sensitive
actions), `nova.safety.egress` (network destination allow-list).

## Cost & privacy

- All defaults are local: Ollama for LLM, Moonshine for STT, Kokoro for
  TTS. No data leaves the device unless you explicitly enable cloud.
- Cloud LLM is rate-limited by `nova.brain.cost_tracker` (daily USD cap;
  router auto-falls-back to local when capped).
- Cloud STT (Deepgram / AssemblyAI) is opt-in and itself falls back to
  local on network failure (`nova.voice.cloud_stt`).
