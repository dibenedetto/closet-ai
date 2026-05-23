"""Popola il database con dati realistici per la demo.

Crea ~10 capi con immagini placeholder (rettangoli colorati generati con PIL),
una storia di wear log distribuita su 90 giorni, e un paio di azioni circolari.

Uso:
    uv run python scripts/seed_demo.py                # popola
    uv run python scripts/seed_demo.py --reset        # azzera prima di popolare

Si appoggia direttamente all'API REST tramite httpx, così il side-effect su
ChromaDB e classifier resta lo stesso del flusso normale.
"""

from __future__ import annotations

import argparse
import io
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8000/api/v1"

# (name, category, color, rgb, price, days_owned)
SEED_ITEMS: list[tuple[str, str, str, tuple[int, int, int], float, int]] = [
    ("T-shirt bordeaux", "t-shirt", "rosso", (160, 30, 50), 19.90, 280),
    ("Camicia bianca classica", "camicia", "bianco", (240, 240, 240), 49.00, 720),
    ("Maglione verde foresta", "maglione", "verde", (50, 110, 70), 79.00, 410),
    ("Felpa grigio melange", "felpa", "grigio", (130, 130, 130), 39.90, 90),
    ("Jeans slim blu indaco", "jeans", "blu", (35, 55, 100), 89.00, 600),
    ("Pantaloni chino beige", "pantaloni", "beige", (210, 195, 165), 59.00, 350),
    ("Gonna a pieghe nera", "gonna", "nero", (25, 25, 30), 49.00, 540),
    ("Giacca denim", "giacca", "blu", (60, 95, 150), 119.00, 800),
    ("Cappotto lana cammello", "cappotto", "marrone", (160, 120, 80), 220.00, 1200),
    ("Scarpe sneakers bianche", "scarpe", "bianco", (240, 240, 240), 99.00, 200),
    ("Sciarpa lana rossa", "sciarpa", "rosso", (180, 40, 40), 24.90, 1500),
    ("Vestito floreale estivo", "vestito", "rosa", (220, 130, 160), 89.00, 95),
]


def make_image(name: str, rgb: tuple[int, int, int]) -> bytes:
    """Crea un'immagine 256x256 con un rettangolo colorato e il nome del capo."""
    img = Image.new("RGB", (256, 256), (250, 250, 250))
    draw = ImageDraw.Draw(img)
    # Rettangolo centrale come "capo"
    draw.rectangle((40, 40, 216, 216), fill=rgb)
    # Etichetta in basso
    try:
        font = ImageFont.load_default(size=14)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((10, 226), name[:36], fill=(40, 40, 50), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def reset_all(client: httpx.Client) -> None:
    """Cancella tutti gli item esistenti (cascade ai wear/action)."""
    items = client.get("/items?limit=200").json()
    for it in items:
        client.delete(f"/items/{it['id']}")
    if items:
        print(f"  reset: cancellati {len(items)} capi")


def seed(reset: bool) -> None:
    rng = random.Random(42)
    today = date.today()

    with httpx.Client(base_url=BASE, timeout=30) as client:
        # Verifica connessione
        try:
            client.get("/health").raise_for_status()
        except Exception as e:
            print(f"!! Backend non raggiungibile su {BASE}: {e}")
            print("   Avvia prima `scripts/run-backend.{sh,ps1,bat}`.")
            sys.exit(1)

        if reset:
            reset_all(client)

        created: list[dict] = []
        print("==> Carico capi…")
        for name, category, color, rgb, price, days_owned in SEED_ITEMS:
            purchase_date = (today - timedelta(days=days_owned)).isoformat()
            data = {
                "name": name,
                "category": category,
                "color": color,
                "price": str(price),
                "purchase_date": purchase_date,
            }
            r = client.post(
                "/items",
                data=data,
                files={"image": (f"{name}.png", make_image(name, rgb), "image/png")},
            )
            r.raise_for_status()
            item = r.json()
            created.append(item)
            print(f"  + #{item['id']:>2} {name}")
            time.sleep(0.02)  # respiro per non spammare il classifier

        print("\n==> Registro storico wear log (90 giorni)…")
        # Distribuzione realistica: alcuni capi indossati molto, altri quasi mai
        wear_distribution = {
            0: 30,  # T-shirt bordeaux: indossato 30 volte
            1: 12,  # Camicia bianca: 12 volte
            2: 8,   # Maglione: 8 volte
            3: 15,  # Felpa: 15 volte
            4: 25,  # Jeans: 25 volte
            5: 18,  # Chino: 18 volte
            6: 6,   # Gonna: 6 volte
            7: 4,   # Giacca denim: 4 volte
            8: 2,   # Cappotto: 2 volte (capo invernale, non in stagione)
            9: 28,  # Sneakers: 28 volte
            10: 0,  # Sciarpa rossa: mai indossata → FANTASMA
            11: 0,  # Vestito floreale: mai indossato → FANTASMA
        }
        total_wears = 0
        for idx, count in wear_distribution.items():
            item = created[idx]
            for _ in range(count):
                days_back = rng.randint(0, 89)
                worn = (today - timedelta(days=days_back)).isoformat()
                client.post(
                    f"/items/{item['id']}/wear",
                    json={"worn_on": worn},
                )
                total_wears += 1
        print(f"  registrati {total_wears} eventi di utilizzo")

        print("\n==> Registro un paio di azioni circolari di esempio…")
        # Riparazione su giacca denim (4 wears su 800gg → usurato)
        giacca = created[7]
        client.put(f"/items/{giacca['id']}/condition", json={"condition": "usurato"})
        client.post(
            f"/items/{giacca['id']}/actions",
            json={"action_type": "riparazione", "notes": "ricucita cucitura interna"},
        )
        print(f"  + riparazione su #{giacca['id']} {giacca['name']}")

        # Donazione del cappotto (out-of-season, raro uso)
        cappotto = created[8]
        client.post(
            f"/items/{cappotto['id']}/actions",
            json={"action_type": "donazione", "notes": "donato a centro Caritas"},
        )
        print(f"  + donazione di #{cappotto['id']} {cappotto['name']}")

        # Diagnose la sciarpa fantasma per popolare condition
        sciarpa = created[10]
        client.post(f"/items/{sciarpa['id']}/diagnose")
        print(f"  + diagnosi su #{sciarpa['id']} {sciarpa['name']} (capo fantasma)")

        print("\n==> Seed completato.")
        impact = client.get("/stats/impact").json()
        wardrobe = client.get("/stats/wardrobe").json()
        print("\nStato del guardaroba:")
        print(f"  • Capi attivi:       {wardrobe['total_items']}")
        print(f"  • Capi fantasma:     {wardrobe['ghost_count']}")
        print(f"  • Utilizzi totali:   {wardrobe['total_wears']}")
        print(f"  • Cost-per-wear:     € {wardrobe['avg_cost_per_wear']}")
        print(f"  • CO₂ evitata:       {impact['total_co2_saved_kg']} kg")
        print(f"  • Capi riparati:     {impact['repaired_items_count']}")
        print(f"  • Capi ritirati:     {impact['retired_items_count']}")
        print("\nApri http://localhost:5173/ (o /test/) per esplorare la demo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Azzera il guardaroba prima di seedare",
    )
    args = parser.parse_args()
    seed(reset=args.reset)
