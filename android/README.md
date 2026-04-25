# Nova Android

Kotlin + Jetpack Compose app that connects to the Nova brain over
WebSocket. Runs a foreground service so the wake word keeps listening
when the screen is off.

## Build

```bash
./gradlew :app:assembleDebug
```

## Contract

The app speaks the protocol defined in `src/nova/mobile/protocol.py`
(Python) and `app/src/main/java/com/nova/mobile/Protocol.kt` (Kotlin).

## Modules

- `app/` — Jetpack Compose UI (chat + settings)
- `app/src/main/java/com/nova/service/` — Foreground service + mic
- `app/src/main/java/com/nova/transport/` — WebSocket client (OkHttp)
- `app/src/main/java/com/nova/accessibility/` — Accessibility service
