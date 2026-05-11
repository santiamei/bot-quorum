"""
Gestión de datos JSON en disco.
Estructura:
  data/bills.yaml               → proyectos activos
  data/bills/{slug}/latest.json → snapshot actual
  data/bills/{slug}/{fecha}.json → historial diario
"""

import json
import os
import re
import yaml
import shutil
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
BILLS_DIR = DATA_DIR / "bills"
BILLS_CONFIG = DATA_DIR / "bills.yaml"


# ── Bills ────────────────────────────────────────────────────────────────────

def load_bills() -> list[dict]:
    if not BILLS_CONFIG.exists():
        return []
    with open(BILLS_CONFIG, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return [b for b in data.get("bills", []) if b.get("active", True)]


def save_bill(name: str, vote_date: str | None = None):
    slug = slugify(name)
    bills = _load_all_bills()

    existing = next((b for b in bills if b["slug"] == slug), None)
    if existing:
        return slug  # Ya existe

    bills.append({
        "name": name,
        "slug": slug,
        "vote_date": vote_date,
        "active": True,
        "added": date.today().isoformat(),
    })

    BILLS_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(BILLS_CONFIG, "w", encoding="utf-8") as f:
        yaml.dump({"bills": bills}, f, allow_unicode=True, default_flow_style=False)

    bill_dir = BILLS_DIR / slug
    bill_dir.mkdir(parents=True, exist_ok=True)
    return slug


def deactivate_bill(slug: str):
    bills = _load_all_bills()
    for b in bills:
        if b["slug"] == slug:
            b["active"] = False
    with open(BILLS_CONFIG, "w", encoding="utf-8") as f:
        yaml.dump({"bills": bills}, f, allow_unicode=True, default_flow_style=False)


def _load_all_bills() -> list[dict]:
    if not BILLS_CONFIG.exists():
        return []
    with open(BILLS_CONFIG, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("bills", [])


# ── Snapshots ────────────────────────────────────────────────────────────────

def load_latest(slug: str) -> dict | None:
    path = BILLS_DIR / slug / "latest.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_snapshot(slug: str, snapshot: dict):
    bill_dir = BILLS_DIR / slug
    bill_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    snapshot["last_updated"] = datetime.now().isoformat()

    # Guardar historial diario
    history_path = bill_dir / f"{today}.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    # Actualizar latest
    latest_path = bill_dir / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def build_snapshot(bill: dict, deputies_results: list[dict]) -> dict:
    counts = {"favor": 0, "contra": 0, "abstencion": 0, "sin_info": 0}
    for d in deputies_results:
        counts[d.get("intention", "sin_info")] += 1

    return {
        "bill_name": bill["name"],
        "bill_slug": bill["slug"],
        "vote_date": bill.get("vote_date"),
        "deputies": deputies_results,
        "summary": counts,
    }


def detect_changes(old: dict | None, new: dict) -> list[dict]:
    if not old:
        return []

    changes = []
    old_map = {d["apellido"]: d for d in old.get("deputies", [])}

    for deputy in new.get("deputies", []):
        ap = deputy["apellido"]
        prev = old_map.get(ap)
        if not prev:
            continue
        if prev["intention"] != deputy["intention"] and deputy["intention"] != "sin_info":
            changes.append({
                "apellido": ap,
                "nombre": deputy["nombre"],
                "bloque": deputy["bloque"],
                "intention_prev": prev["intention"],
                "intention_new": deputy["intention"],
                "confidence": deputy["confidence"],
                "source": deputy.get("source"),
            })
    return changes


# ── Helpers ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[áàä]", "a", text)
    text = re.sub(r"[éèë]", "e", text)
    text = re.sub(r"[íìï]", "i", text)
    text = re.sub(r"[óòö]", "o", text)
    text = re.sub(r"[úùü]", "u", text)
    text = re.sub(r"ñ", "n", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:60]


def list_bill_dirs() -> list[Path]:
    if not BILLS_DIR.exists():
        return []
    return [p for p in BILLS_DIR.iterdir() if p.is_dir()]
