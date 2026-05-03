# Privacy policy + data-flow

Nova is a personal assistant. Your audio, transcripts, and memory live
on your devices unless **you** turn on a cloud feature.

## What stays local (always)

- Wake word detection
- Default STT (Moonshine) and TTS (Kokoro)
- Short-term context, vector memory, episodic log
- Audit log (`~/.local/share/nova/audit.jsonl`) — never transmitted

## What can leave your device (opt-in)

- Cloud LLM call: Claude / OpenAI / Gemini, only when:
  - The user enables the cloud route in settings, **and**
  - `nova.brain.cost_tracker` is under the daily cap, **and**
  - The query is not flagged "private" by the router
- Cloud STT (Deepgram / AssemblyAI): same opt-in flag, with offline
  fallback wired into `nova.voice.cloud_stt`.
- Synced session state with paired phone (always end-to-end via your
  Tailscale / WireGuard tunnel).

## Data-flow diagram

```
                         user speaks
                              |
               +--------------v---------------+
               | wake word (local)            |
               | STT (local default)          |
               | redaction (regex + ML)       |  ← nova.safety.redaction
               +--------------+---------------+
                              |
                  +-----------v----------+
                  | Hybrid router        |
                  | difficulty / privacy |
                  +-----+--------+-------+
                        |        |
            local LLM   |        | cloud LLM (only if user opted in
              (Ollama)  |        |  AND cost cap not hit AND not flagged)
                        |        |
                  +-----v--------v-------+
                  | response             |
                  | TTS (local default)  |
                  +-----------+----------+
                              |
                       +------v-------+
                       | audit log    | ← stays on device, redacted
                       +--------------+
```

## Your controls

| Setting | Default | Effect |
|---|---|---|
| Cloud LLM | off | Allows / disallows any outbound LLM call |
| Cloud STT | off | Allows / disallows outbound STT |
| Cost cap (USD/day) | 1.00 | Hard stop on cloud spend |
| Egress allow-list | empty | Domains tools may reach (`nova.safety.egress`) |
| Speaker verification | off | Sensitive tools require enrolled voice |
| Audit redaction | on | Strip secrets before writing audit |
| Memory export | on demand | JSON + Markdown via `nova.memory.export` |
| Memory delete | on demand | Wipe via Settings → Memory → Forget |

## What we never do

- Send your data to Anthropic / Nova maintainers (we have no server).
- Phone home for telemetry.
- Persist audio chunks beyond the wake / turn window unless you explicitly
  enable the false-trigger logger for retraining.
