# Specchio smart ClosetAI — guida Raspberry Pi 5

> Estensione hardware *opzionale* del progetto. Trasforma un Raspberry Pi 5 con
> monitor verticale in uno "specchio smart" che mostra orologio, meteo, e
> l'outfit suggerito da ClosetAI per la giornata. La pagina `/mirror` del
> frontend è pensata per girare a fullscreen in modalità kiosk.

## Materiale consigliato

- **Raspberry Pi 5** (4 GB o 8 GB di RAM) con alimentatore ufficiale
- microSD ≥ 32 GB (Raspberry Pi OS 64-bit, Bookworm)
- Monitor con ingresso HDMI/DisplayPort (uno portrait 1080×1920 è ideale)
- Cavo micro-HDMI → HDMI
- Vetro semi-riflettente (acrylic one-way) o specchio spia se si vuole
  l'effetto "Mirror" vero — opzionale, la demo funziona anche su monitor
  diretto
- Webcam USB (futuro: capture outfit indossati per wear log automatico)
- Tastiera USB per il setup iniziale (poi rimovibile)

## Schema di rete

```
┌─────────────┐      Wi-Fi / LAN     ┌──────────────────┐
│ Raspberry   │  ─────────────────► │ Backend ClosetAI │
│ Pi (kiosk)  │                      │ (uvicorn :8000)  │
│ Chromium    │ ◄─── /mirror ───── │ FastAPI          │
└─────────────┘                      └──────────────────┘
```

Il backend può girare:
- **sullo stesso Pi**: comodo per la demo single-device, ma più lento
  perché Fashion-CLIP è esoso di CPU (cf. benchmark in `architecture.md`)
- **su un server di rete locale**: PC desktop / NAS / mini-PC che il Pi
  raggiunge via Wi-Fi → preferibile

## Setup software (sul Raspberry Pi)

### 1. OS

```bash
# Da `rpi-imager` (https://www.raspberrypi.com/software/) installa
# "Raspberry Pi OS (64-bit)". Abilita SSH, imposta hostname `closet-mirror`.
```

### 2. Installa Chromium kiosk launcher

Lo script [`scripts/start-mirror.sh`](../scripts/start-mirror.sh) avvia
Chromium in fullscreen verso la pagina `/mirror` del frontend.

```bash
sudo apt update
sudo apt install -y chromium-browser unclutter xdotool

# Copia lo script dal repo:
mkdir -p ~/closetai && cp /path/to/scripts/start-mirror.sh ~/closetai/
chmod +x ~/closetai/start-mirror.sh
```

Per personalizzare l'URL: modifica la variabile `MIRROR_URL` in cima allo
script. Default: `http://localhost:5173/mirror` (se anche frontend gira sul
Pi); per puntare a un server remoto:
`MIRROR_URL=http://192.168.1.20:5173/mirror`.

### 3. Autostart all'avvio (Wayland)

Crea `~/.config/wayfire.ini` (o `~/.config/lxsession/LXDE-pi/autostart`
su X11 legacy) e aggiungi:

```ini
[autostart]
mirror = bash /home/pi/closetai/start-mirror.sh
```

In alternativa, una unit systemd:

```bash
sudo tee /etc/systemd/system/closet-mirror.service <<'EOF'
[Unit]
Description=ClosetAI mirror (Chromium kiosk)
After=graphical.target network-online.target

[Service]
User=pi
Environment=DISPLAY=:0
ExecStart=/home/pi/closetai/start-mirror.sh
Restart=on-failure

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable closet-mirror
```

### 4. Rotazione schermo (portrait)

Per un monitor portrait, in `/boot/firmware/config.txt`:

```ini
display_rotate=1   # 90°; usa 3 per ruotare nell'altro senso
```

(Su Wayland/labwc, usa `wlr-randr --output HDMI-A-1 --transform 90`.)

### 5. Webcam (estensione futura)

Test webcam:

```bash
sudo apt install -y fswebcam
fswebcam -r 640x480 --no-banner /tmp/test.jpg
```

Il modulo "outfit detection automatico" è elencato come estensione futura
in `docs/architecture.md` (M4 / M5). L'idea: pulsante "ti ho visto: era
questo l'outfit?" su `/mirror` quando si rileva una presenza tramite PIR
o motion detection sul frame catturato.

## Troubleshooting

### "Black screen" al boot

- Verifica che il monitor accetti il segnale HDMI rilevato dal Pi:
  `vcgencmd hdmi_status`.
- In `config.txt` prova `hdmi_force_hotplug=1`.

### "Chromium si riapre in loop"

Lo script usa `--noerrdialogs --disable-session-crashed-bubble` per
sopprimere il dialog "Chrome non si è chiuso correttamente". Se non basta,
cancella la profile dir: `rm -rf ~/.config/chromium`.

### "Outfit vuoto"

`/mirror` chiama `GET /outfits/suggest?count=1`. Se il guardaroba è vuoto
risponde `outfits: []`. Carica almeno un top + bottom + scarpe dal
frontend per ottenere una proposta.

### CPU al 100% durante l'inferenza

Atteso: Fashion-CLIP ~7s al primo caricamento e ~60ms per call su Pi 5.
Per il refresh ogni 5 minuti basta tranquillamente. Se l'inferenza è
percepibile, sposta il backend su una macchina più potente (vedi sezione
"Schema di rete").

## Variazioni demo-ready

- **Demo da scrivania**: monitor 24" landscape su un cavalletto, niente
  vetro semi-riflettente. La UI funziona identica.
- **Demo "vera"**: cornice in legno + acrilico spia 30%. L'illuminazione
  della stanza deve essere bassa e i pixel del monitor devono passare
  attraverso il vetro.
