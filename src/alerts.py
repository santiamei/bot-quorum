"""
Alertas por Telegram (gratis, instantáneo).
Requiere: TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en variables de entorno.
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

INTENTION_LABELS = {
    "favor":      "A FAVOR ✅",
    "contra":     "EN CONTRA ❌",
    "abstencion": "ABSTENCIÓN ⚠️",
    "sin_info":   "SIN INFORMACIÓN ❓",
}

CONFIDENCE_THRESHOLD = 0.65


def send_change_alerts(bill_name: str, changes: list[dict]):
    token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados. Omitiendo alertas.")
        return

    high_confidence = [c for c in changes if c.get("confidence", 0) >= CONFIDENCE_THRESHOLD]
    if not high_confidence:
        return

    for change in high_confidence:
        message = _build_message(bill_name, change)
        _send(token, chat_id, message)


def send_daily_summary(bill_name: str, summary: dict, bill_slug: str):
    token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    total      = sum(summary.values())
    favor      = summary.get("favor", 0)
    contra     = summary.get("contra", 0)
    abstencion = summary.get("abstencion", 0)
    sin_info   = summary.get("sin_info", 0)

    message = (
        f"📊 *RESUMEN DIARIO*\n"
        f"_{bill_name}_\n\n"
        f"✅ A favor: {favor}\n"
        f"❌ En contra: {contra}\n"
        f"⚠️ Abstención: {abstencion}\n"
        f"❓ Sin info: {sin_info}\n"
        f"Total monitoreados: {total}"
    )
    _send(token, chat_id, message)


def _build_message(bill_name: str, change: dict) -> str:
    prev_label = INTENTION_LABELS.get(change["intention_prev"], change["intention_prev"])
    new_label  = INTENTION_LABELS.get(change["intention_new"], change["intention_new"])
    confidence_pct = int(change["confidence"] * 100)

    lines = [
        f"🔔 *CAMBIO DE POSICIÓN DETECTADO*",
        f"📋 Proyecto: _{bill_name}_",
        f"👤 Diputado/a: {change['nombre']} {change['apellido']}",
        f"🏛 Bloque: {change['bloque']}",
        f"Antes: {prev_label}",
        f"Ahora: {new_label}",
        f"Confianza: {confidence_pct}%",
    ]
    if change.get("source"):
        lines.append(f"📰 Fuente: {change['source']}")

    return "\n".join(lines)


def _send(token: str, chat_id: str, message: str):
    url = TELEGRAM_API.format(token=token)
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10)
        if resp.status_code == 200:
            logger.info("Telegram enviado OK")
        else:
            logger.warning(f"Telegram respondió {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"Error enviando Telegram: {e}")
