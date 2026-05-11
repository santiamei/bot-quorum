"""
Alertas por WhatsApp via CallMeBot (gratis).
Setup: enviá un WhatsApp a +34 644 97 46 14 con el texto:
  "I allow callmebot to send me messages"
Recibirás tu API key por WhatsApp.
"""

import os
import requests
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"

INTENTION_LABELS = {
    "favor": "A FAVOR ✅",
    "contra": "EN CONTRA ❌",
    "abstencion": "ABSTENCIÓN ⚠️",
    "sin_info": "SIN INFORMACIÓN ❓",
}

CONFIDENCE_THRESHOLD = 0.65


def send_change_alerts(bill_name: str, changes: list[dict]):
    phone = os.environ.get("WHATSAPP_PHONE")
    api_key = os.environ.get("CALLMEBOT_API_KEY")

    if not phone or not api_key:
        logger.warning("WHATSAPP_PHONE o CALLMEBOT_API_KEY no configurados. Omitiendo alertas.")
        return

    # Filtrar solo cambios con confianza suficiente
    high_confidence = [c for c in changes if c.get("confidence", 0) >= CONFIDENCE_THRESHOLD]
    if not high_confidence:
        return

    for change in high_confidence:
        message = _build_message(bill_name, change)
        _send(phone, api_key, message)


def _build_message(bill_name: str, change: dict) -> str:
    prev_label = INTENTION_LABELS.get(change["intention_prev"], change["intention_prev"])
    new_label = INTENTION_LABELS.get(change["intention_new"], change["intention_new"])
    confidence_pct = int(change["confidence"] * 100)

    lines = [
        f"🔔 CAMBIO DE POSICIÓN DETECTADO",
        f"Proyecto: {bill_name}",
        f"Diputado/a: {change['nombre']} {change['apellido']}",
        f"Bloque: {change['bloque']}",
        f"Antes: {prev_label}",
        f"Ahora: {new_label}",
        f"Confianza: {confidence_pct}%",
    ]
    if change.get("source"):
        lines.append(f"Fuente: {change['source']}")

    return "\n".join(lines)


def _send(phone: str, api_key: str, message: str):
    params = {
        "phone": phone,
        "text": message,
        "apikey": api_key,
    }
    try:
        resp = requests.get(CALLMEBOT_URL, params=params, timeout=10)
        if resp.status_code == 200:
            logger.info(f"WhatsApp enviado OK")
        else:
            logger.warning(f"CallMeBot respondió {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"Error enviando WhatsApp: {e}")


def send_daily_summary(bill_name: str, summary: dict, bill_slug: str):
    """Envía resumen diario opcional (solo si hay cambios significativos)."""
    phone = os.environ.get("WHATSAPP_PHONE")
    api_key = os.environ.get("CALLMEBOT_API_KEY")
    if not phone or not api_key:
        return

    total = sum(summary.values())
    favor = summary.get("favor", 0)
    contra = summary.get("contra", 0)
    abstencion = summary.get("abstencion", 0)
    sin_info = summary.get("sin_info", 0)

    message = (
        f"📊 RESUMEN DIARIO - {bill_name}\n"
        f"✅ A favor: {favor}\n"
        f"❌ En contra: {contra}\n"
        f"⚠️ Abstención: {abstencion}\n"
        f"❓ Sin info: {sin_info}\n"
        f"Total monitoreados: {total}"
    )
    _send(phone, api_key, message)
