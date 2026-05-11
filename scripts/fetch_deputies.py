"""
Actualiza config/deputies.yaml scrapeando la nómina oficial de la HCDN.
Mantiene solo los bloques configurados en TARGET_BLOQUES.
Ejecutar: python scripts/fetch_deputies.py
"""

import sys
import re
from pathlib import Path
from datetime import date

import requests
from bs4 import BeautifulSoup
import yaml

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "config" / "deputies.yaml"
HCDN_URL = "https://www.hcdn.gob.ar/diputados/diputados-por-bloque.html"

TARGET_BLOQUES = {
    "PROVINCIAS UNIDAS",
    "INNOVACIÓN FEDERAL",
    "UCR - UNIÓN CÍVICA RADICAL",
    "ELIJO CATAMARCA",
    "INDEPENDENCIA",
    "COALICIÓN CÍVICA",
    "ENCUENTRO FEDERAL",
    "MID - MOVIMIENTO DE INTEGRACIÓN Y DESARROLLO",
    "PARTIDO OBRERO EN EL FRENTE DE IZQUIERDA Y DE TRABAJADORES-UNIDAD",
    "PRODUCCIÓN Y TRABAJO",
    "PTS-FRENTE DE IZQUIERDA Y DE TRABAJADORES UNIDAD",
    "ADELANTE BUENOS AIRES",
    "COHERENCIA",
    "DEFENDAMOS CÓRDOBA",
    "LA NEUQUINIDAD",
    "POR SANTA CRUZ",
    "PRIMERO SAN LUIS",
}

BLOQUE_ALIASES = {
    "MID - MOVIMIENTO DE INTEGRACIÓN Y DESARROLLO": "MID",
    "PARTIDO OBRERO EN EL FRENTE DE IZQUIERDA Y DE TRABAJADORES-UNIDAD": "PARTIDO OBRERO - FIT UNIDAD",
    "PTS-FRENTE DE IZQUIERDA Y DE TRABAJADORES UNIDAD": "PTS - FIT UNIDAD",
}


def fetch_page():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; QuorumBot/1.0)"}
    resp = requests.get(HCDN_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_deputies(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    deputies = []

    # La página tiene secciones por bloque con h2/h3 y listas de diputados
    # Buscamos cualquier heading que contenga el nombre del bloque
    current_bloque = None
    for element in soup.find_all(["h2", "h3", "h4", "li", "a", "p"]):
        text = element.get_text(strip=True).upper()

        # Detectar bloque
        for target in TARGET_BLOQUES:
            if target in text and len(text) < len(target) + 30:
                current_bloque = BLOQUE_ALIASES.get(target, target)
                break

        # Detectar diputado (formato "Apellido, Nombre")
        if current_bloque and element.name in ["li", "a"]:
            raw = element.get_text(strip=True)
            if "," in raw and 5 < len(raw) < 80:
                parts = raw.split(",", 1)
                apellido = parts[0].strip().title()
                nombre = parts[1].strip().title() if len(parts) > 1 else ""
                if apellido and nombre:
                    deputies.append({
                        "apellido": apellido,
                        "nombre": nombre,
                        "bloque": current_bloque,
                    })

    return deputies


def save(deputies: list[dict]):
    content = (
        f"# Diputados a monitorear - Fuente: HCDN (hcdn.gob.ar)\n"
        f"# Última actualización: {date.today().isoformat()}\n\n"
        f"deputies:\n"
    )
    current_bloque = None
    for d in sorted(deputies, key=lambda x: (x["bloque"], x["apellido"])):
        if d["bloque"] != current_bloque:
            current_bloque = d["bloque"]
            content += f"\n  # ── {current_bloque} ──\n"
        content += (
            f"  - apellido: {d['apellido']}\n"
            f"    nombre: {d['nombre']}\n"
            f"    bloque: {d['bloque']}\n"
        )
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"✓ {len(deputies)} diputados guardados en {OUTPUT}")


def main():
    print(f"Descargando nómina desde {HCDN_URL}...")
    html = fetch_page()
    deputies = parse_deputies(html)

    if len(deputies) < 10:
        print(f"⚠ Solo se encontraron {len(deputies)} diputados. Puede que la estructura de la página haya cambiado.")
        print("  Revisá el scraper en scripts/fetch_deputies.py")
        # Conservar el archivo actual
        sys.exit(1)

    save(deputies)


if __name__ == "__main__":
    main()
