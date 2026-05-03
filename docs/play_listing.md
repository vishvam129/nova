# Play Store listing + accessibility declared-use

## Listing copy (≤80 chars title, ≤80 short, 4000 long)

**Title:** Nova — your offline-first AI assistant

**Short description:**
Local-first voice + chat AI that bridges your phone and laptop.

**Long description:**

Nova is a personal AI assistant built around a single principle: your
data is yours. Everything from wake-word to spoken reply runs on your
own hardware by default — Moonshine STT, Kokoro TTS, and a local LLM
of your choice. Cloud models stay opt-in and never run when you're not
explicitly paying for them.

Pair Nova with the laptop companion to share one brain across both
devices. Mid-sentence handoff lets you start a thought on the phone and
finish it on the laptop, with a CRDT-backed session that reconciles
offline edits when the link returns.

Highlights:

- Local wake word ("hey nova"), STT, TTS — works on the plane.
- Optional Claude / GPT / Gemini fallback with a hard daily cost cap.
- Cross-device session handoff over your own Tailscale / WireGuard mesh.
- Tool ecosystem: any MCP server you install plus 20+ built-ins
  (calendar, contacts, email, web search, screen capture, system
  control, file search, computer-use).
- Speaker verification gates sensitive actions to enrolled voices.
- One-tap memory export (GDPR-grade JSON + Markdown).

## Declared use of AccessibilityService (Jan 2026 policy)

**Permission requested:** `BIND_ACCESSIBILITY_SERVICE`

**App functionality this enables:**
Nova uses Android's AccessibilityService to (a) capture on-screen text
and the active app name so the assistant can answer questions about
what you're looking at ("what does this error mean?"), and (b) perform
the user-requested UI actions Nova was asked to do (tap a button,
type a string, scroll). Without AccessibilityService, Nova cannot
read screen context or carry out cross-app automation.

**Pre-permission disclosure shown to the user (verbatim):**

> Nova reads on-screen text and the active app name so it can answer
> questions about what you're looking at. No screen data is stored or
> shared with third parties. You can revoke this permission at any
> time in Settings → Accessibility → Nova.

(see `nova.mobile.accessibility.POLICY_DISCLOSURE_TEXT` — kept in sync
with this listing on every release.)

**Alternative if user denies:** Nova falls back to Shizuku or
wireless ADB (`nova.mobile.shizuku_fallback`) for shell-driven
automation — voice/STT/TTS/notifications continue to work without
the AccessibilityService.

## Sensitive permissions matrix

| Permission | Why | Optional? |
|---|---|---|
| `RECORD_AUDIO` | wake word + STT | required for voice |
| `FOREGROUND_SERVICE` | keep mic open with screen off | required |
| `POST_NOTIFICATIONS` | nova replies + reminders | yes |
| `READ_CONTACTS` | "call mom" intent | yes |
| `SEND_SMS` | "text alice I'm late" | yes |
| `BIND_ACCESSIBILITY_SERVICE` | screen context + automation | yes (fallback above) |
| `READ_NOTIFICATIONS` | summarise pending notifications | yes |
| `BLUETOOTH_CONNECT` | route audio to headset | yes |

## Content rating

Everyone — no user-generated public content, no ads, no in-app purchases.
