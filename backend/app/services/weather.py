"""Servizio meteo basato su Open-Meteo (https://open-meteo.com/).

Open-Meteo è gratuito, non richiede autenticazione, e supporta forecast
giornalieri e orari. Lo utilizziamo per condizionare le proposte di outfit.

Il modulo espone un'unica funzione pubblica `fetch_weather()`: i test la
patchano via `monkeypatch` invece di colpire la rete.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import httpx

from app.config import DEFAULT_LAT, DEFAULT_LON

log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(frozen=True, slots=True)
class WeatherInfo:
    target_date: date
    temperature_c: float
    precipitation_mm: float
    wind_kmh: float
    weather_code: int
    source: str  # "open-meteo" | "fallback"

    def is_cold(self) -> bool:
        return self.temperature_c < 12.0

    def is_warm(self) -> bool:
        return self.temperature_c >= 22.0

    def is_rainy(self) -> bool:
        return self.precipitation_mm >= 1.0


def _fallback(target_date: date) -> WeatherInfo:
    """Meteo di fallback: usato se la chiamata HTTP fallisce."""
    return WeatherInfo(
        target_date=target_date,
        temperature_c=18.0,
        precipitation_mm=0.0,
        wind_kmh=10.0,
        weather_code=0,
        source="fallback",
    )


def fetch_weather(
    target_date: date,
    *,
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LON,
    timeout: float = 4.0,
) -> WeatherInfo:
    """Recupera il meteo per `target_date` alle coordinate date.

    Restituisce dati daily aggregati. Se l'API risponde con errore o timeout,
    ritorna un fallback "templato" che permette comunque al recommender di
    funzionare (il chiamante può ispezionare `source == "fallback"`).
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_mean,precipitation_sum,wind_speed_10m_max,weather_code",
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "timezone": "auto",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(OPEN_METEO_URL, params=params)
            r.raise_for_status()
            body = r.json()
        daily = body.get("daily") or {}
        return WeatherInfo(
            target_date=target_date,
            temperature_c=float((daily.get("temperature_2m_mean") or [18.0])[0]),
            precipitation_mm=float((daily.get("precipitation_sum") or [0.0])[0]),
            wind_kmh=float((daily.get("wind_speed_10m_max") or [10.0])[0]),
            weather_code=int((daily.get("weather_code") or [0])[0]),
            source="open-meteo",
        )
    except Exception:
        log.warning("Open-Meteo non raggiungibile, uso fallback", exc_info=True)
        return _fallback(target_date)
