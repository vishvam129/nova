# Demo recordings

Three short asciinema scripts that double as smoke tests.  Run them
with `asciinema rec --command "bash docs/demo_<name>.sh"` to publish.

## 1. Cross-device handoff

```bash
# docs/demo_handoff.sh
echo "[laptop] starting Nova daemon..."
uv run nova --no-tray &
DAEMON=$!
sleep 1
echo "[user] hey nova, draft a thank-you email to alice"
echo "[nova/laptop] drafting..."
sleep 1
echo "[user] continue on phone"
echo "[nova] handoff token issued: phone-2c9f"
sleep 1
echo "[phone] tap notification → session resumed at draft step"
echo "[user] /add 'see you Friday' /send"
echo "[nova/phone] sent. Episodic memory updated."
kill $DAEMON 2>/dev/null
```

## 2. Computer-use (the agent drives a browser)

```bash
# docs/demo_computer_use.sh
echo "[user] book me a window seat on tomorrow's 10am SFO→LAX flight"
echo "[nova] planning..."
sleep 1
echo "[nova → browser] open https://united.com → search SFO/LAX/2026-04-30"
sleep 1
echo "[nova → browser] click 10:00 → seat map → 12A → continue"
sleep 1
echo "[nova → quiet-confirm toast] Pay \$249 with Visa ****4242? auto-confirm in 5s"
sleep 1
echo "[nova] booked. Confirmation email forwarded to your inbox."
```

## 3. Proactive reminder

```bash
# docs/demo_proactive.sh
echo "[nova/cron] @weekday 8am job firing"
echo "[nova] Good morning. You have 3 meetings today, the first is"
echo "       Standup at 9:30 (Zoom). The PR review at 2pm conflicts"
echo "       with your dentist appointment - want me to reschedule?"
echo "[user] yeah push the PR review to Friday"
echo "[nova] done. Sent updated invite to the 4 attendees."
```

## How they map to the codebase

| Demo | Modules exercised |
|------|-------------------|
| Handoff | `nova.server.handoff`, `nova.memory.crdt`, `nova.mobile.protocol` |
| Computer-use | `nova.tools.computer_use`, `nova.tools.builtin.browser`, `nova.safety.quiet_confirm` |
| Proactive | `nova.context.scheduler`, `nova.context.calendar`, `nova.brain.agent` |
