#!/usr/bin/env bash
# Lancia Chromium in modalità kiosk verso la pagina specchio di ClosetAI.
# Pensato per essere eseguito da systemd o autostart su Raspberry Pi 5.
# Vedi docs/raspberry-pi.md per il setup completo.
set -euo pipefail

# Personalizzabile: se il backend gira su un'altra macchina, sostituisci
# con `http://<IP_BACKEND>:5173/mirror`.
MIRROR_URL="${MIRROR_URL:-http://localhost:5173/mirror}"

# Nasconde il cursore dopo 0.5s di inattività.
if command -v unclutter >/dev/null 2>&1; then
  unclutter -idle 0.5 -root &
fi

# Disabilita screensaver / DPMS.
if command -v xset >/dev/null 2>&1; then
  xset s off || true
  xset -dpms || true
  xset s noblank || true
fi

# Scegli il binary disponibile (Chromium-browser su Bookworm, chromium su
# alcune distro recenti).
CHROMIUM_BIN=""
for candidate in chromium-browser chromium google-chrome; do
  if command -v "$candidate" >/dev/null 2>&1; then
    CHROMIUM_BIN="$candidate"
    break
  fi
done

if [[ -z "$CHROMIUM_BIN" ]]; then
  echo "!! Nessun browser Chromium-compatibile trovato (chromium-browser, chromium, google-chrome)." >&2
  exit 1
fi

exec "$CHROMIUM_BIN" \
  --kiosk \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --disable-infobars \
  --disable-translate \
  --no-first-run \
  --start-fullscreen \
  --autoplay-policy=no-user-gesture-required \
  --disk-cache-dir=/tmp/closetai-mirror-cache \
  "$MIRROR_URL"
