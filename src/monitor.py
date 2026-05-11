"""
Orquestador principal del bot de poroteo.
Uso:
  python -m src.monitor                    → corre todos los proyectos activos
  python -m src.monitor --bill "Presupuesto 2027" --date "2026-06-15"  → agrega y corre uno nuevo
  python -m src.monitor --bill "Presupuesto 2027"                       → solo agrega
  python -m src.monitor --summary                                        → envía resumen diario
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper import fetch_articles
from src.analyzer import analyze_deputy_intent
from src.storage import (
    load_bills,
    save_bill,
    load_latest,
    save_snapshot,
    build_snapshot,
    detect_changes,
)
from src.alerts import send_change_alerts, send_daily_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

DEPUTIES_CONFIG = Path(__file__).parent.parent / "config" / "deputies.yaml"
DELAY_BETWEEN_DEPUTIES = 2  # segundos entre llamadas Gemini


def load_deputies() -> list[dict]:
    with open(DEPUTIES_CONFIG, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("deputies", [])


def run_bill(bill: dict, deputies: list[dict], send_summary: bool = False):
    bill_name = bill["name"]
    slug = bill["slug"]

    logger.info(f"━━━ Procesando: {bill_name} ━━━")
    prev_snapshot = load_latest(slug)
    deputies_results = []

    for deputy in deputies:
        apellido = deputy["apellido"]
        nombre = deputy["nombre"]
        bloque = deputy["bloque"]

        articles = fetch_articles(apellido, nombre, bill_name)
        analysis = analyze_deputy_intent(apellido, nombre, bloque, bill_name, articles)

        result = {
            "apellido": apellido,
            "nombre": nombre,
            "bloque": bloque,
            "intention": analysis["intention"],
            "confidence": analysis["confidence"],
            "quote": analysis.get("quote"),
            "source": analysis.get("source"),
            "reasoning": analysis.get("reasoning"),
        }
        deputies_results.append(result)

        intention_str = analysis["intention"].upper()
        conf_str = f"{int(analysis['confidence']*100)}%"
        logger.info(f"  {apellido}, {nombre[:12]} → {intention_str} ({conf_str})")

        time.sleep(DELAY_BETWEEN_DEPUTIES)

    snapshot = build_snapshot(bill, deputies_results)
    save_snapshot(slug, snapshot)
    logger.info(f"  Snapshot guardado. Resumen: {snapshot['summary']}")

    # Detectar cambios y alertar
    changes = detect_changes(prev_snapshot, snapshot)
    if changes:
        logger.info(f"  {len(changes)} cambio(s) detectado(s). Enviando alertas...")
        send_change_alerts(bill_name, changes)
    else:
        logger.info("  Sin cambios de posición.")

    if send_summary:
        send_daily_summary(bill_name, snapshot["summary"], slug)

    return snapshot


def main():
    parser = argparse.ArgumentParser(description="Bot de poroteo legislativo")
    parser.add_argument("--bill", help="Nombre del nuevo proyecto de ley a agregar")
    parser.add_argument("--date", help="Fecha de votación (YYYY-MM-DD)")
    parser.add_argument("--run", action="store_true", help="Correr solo el proyecto especificado en --bill")
    parser.add_argument("--summary", action="store_true", help="Enviar resumen diario por WhatsApp")
    args = parser.parse_args()

    deputies = load_deputies()
    logger.info(f"Diputados cargados: {len(deputies)}")

    # Agregar nuevo proyecto si se especificó
    if args.bill:
        slug = save_bill(args.bill, args.date)
        logger.info(f"Proyecto '{args.bill}' registrado (slug: {slug})")

        if args.run:
            bill = {"name": args.bill, "slug": slug, "vote_date": args.date, "active": True}
            run_bill(bill, deputies, send_summary=args.summary)
            return

    # Correr todos los proyectos activos
    bills = load_bills()
    if not bills:
        logger.warning("No hay proyectos activos. Agregá uno con --bill 'Nombre del proyecto'")
        return

    logger.info(f"Proyectos activos: {len(bills)}")
    for bill in bills:
        run_bill(bill, deputies, send_summary=args.summary)

    logger.info("✓ Ciclo completo.")


if __name__ == "__main__":
    main()
