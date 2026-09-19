from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

START = date(2025, 3, 1)
WAR_START = date(2026, 2, 28)
END = date.today()
DATA_RAW = ROOT / "data" / "raw"
DATA_REF = ROOT / "data" / "reference"

STATIONS = {
    "tehran": {"usaf_wban": "407540-99999", "name": "Mehrabad Intl", "lat": 35.689, "lon": 51.313},
    "dubai": {"usaf_wban": "411940-99999", "name": "Dubai Intl", "lat": 25.255, "lon": 55.364},
    "doha": {"usaf_wban": "411703-99999", "name": "Doha / Hamad Intl", "lat": 25.267, "lon": 51.600},
    "abu_dhabi": {"usaf_wban": "412170-99999", "name": "Abu Dhabi Intl / Zayed Intl", "lat": 24.433, "lon": 54.651},
    "riyadh": {"usaf_wban": "404370-99999", "name": "King Khaled Intl", "lat": 24.958, "lon": 46.699},
    "kuwait": {"usaf_wban": "405820-99999", "name": "Kuwait Intl", "lat": 29.227, "lon": 47.969},
    "bahrain": {"usaf_wban": "411500-99999", "name": "Bahrain Intl", "lat": 26.271, "lon": 50.634},
    "tel_aviv": {"usaf_wban": "401800-99999", "name": "Ben Gurion", "lat": 32.011, "lon": 34.887},
    "baghdad": {"usaf_wban": "406500-99999", "name": "Baghdad Intl Airport", "lat": 33.267, "lon": 44.233},
    "bandar_abbas": {"usaf_wban": "408750-99999", "name": "Bandar Abbas Intl", "lat": 27.218, "lon": 56.378},
    "muscat": {"usaf_wban": "412560-99999", "name": "Seeb Intl / Muscat Intl", "lat": 23.593, "lon": 58.284},
    "basrah": {"usaf_wban": "406890-99999", "name": "Basrah Intl", "lat": 30.550, "lon": 47.662},
    "london": {"usaf_wban": "037720-99999", "name": "London Heathrow", "lat": 51.478, "lon": -0.461},
    "nyc_jfk": {"usaf_wban": "744860-94789", "name": "John F Kennedy International Airport", "lat": 40.639, "lon": -73.764},
    "houston": {"usaf_wban": "722430-12960", "name": "G Bush Intercontinental AP/Houston AP", "lat": 29.984, "lon": -95.361},
    "oklahoma_city": {"usaf_wban": "723530-13967", "name": "Will Rogers World Airport", "lat": 35.388, "lon": -97.600},
    "rotterdam": {"usaf_wban": "063440-99999", "name": "Rotterdam", "lat": 51.957, "lon": 4.437},
    "singapore": {"usaf_wban": "486980-99999", "name": "Singapore Changi Intl", "lat": 1.350, "lon": 103.994},
    "tokyo": {"usaf_wban": "476710-99999", "name": "Tokyo Intl", "lat": 35.552, "lon": 139.780},
}
CITIES = {key: {"lat": value["lat"], "lon": value["lon"]} for key, value in STATIONS.items()}

OPENALEX_QUERIES = {
    "iran": "iran", "strait_of_hormuz": "strait of hormuz", "oil_price": "oil price",
    "lng": "liquefied natural gas", "helium": "helium", "tungsten": "tungsten",
    "sulfur": "sulfur", "aluminium": "aluminium OR aluminum", "fertilizer": "fertilizer",
    "desalination": "desalination", "drone": "drone", "missile_defense": "missile defense",
    "energy_security": "energy security", "battery": "lithium battery", "solar": "photovoltaic",
    "nuclear": "uranium enrichment", "cyberattack": "cyberattack water", "sanctions": "sanctions",
    "air_pollution": "air pollution", "materials_science": "materials science",
}

def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)
