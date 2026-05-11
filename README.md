# Bot Quorum — Poroteo Legislativo HCDN

Monitoreo automático de la **intención de voto** de diputados nacionales argentinos, con alertas por WhatsApp y dashboard web.

---

## Qué hace

- Busca noticias en medios argentinos (Google News RSS) sobre cada diputado y el proyecto a votar
- Usa Gemini Flash para clasificar la posición: **A favor / En contra / Abstención / Sin info**
- Guarda un historial diario en JSON
- Detecta cambios de posición y te avisa por **WhatsApp** (gratis via CallMeBot)
- Muestra todo en un **dashboard web** en GitHub Pages
- Corre automáticamente **3 veces por día** (8am, 14:00 y 20:00 hora Argentina)
- Se actualiza la nómina de diputados automáticamente el primer día de cada mes

**Diputados monitoreados:** ~57 diputados de 17 bloques opositores/provinciales (Provincias Unidas, UCR, Encuentro Federal, Coalición Cívica, Innovación Federal, y más).

---

## Setup inicial (una sola vez)

### 1. Crear el repositorio en GitHub

```bash
cd "Bot Quorum"
git remote add origin https://github.com/TU_USUARIO/bot-quorum.git
git add .
git commit -m "feat: setup inicial del bot de poroteo"
git push -u origin main
```

### 2. Configurar los Secrets en GitHub

Ir a tu repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Valor |
|--------|-------|
| `GEMINI_API_KEY` | Tu API key de [aistudio.google.com](https://aistudio.google.com) (gratis) |
| `WHATSAPP_PHONE` | Tu número con código de país, ej: `+5491122334455` |
| `CALLMEBOT_API_KEY` | Tu API key de CallMeBot (ver paso 3) |

### 3. Activar CallMeBot (WhatsApp gratis)

Enviá un WhatsApp al número **+34 644 97 46 14** con el texto exacto:

```
I allow callmebot to send me messages
```

En pocos minutos recibirás tu API key por WhatsApp. Guardala como secret `CALLMEBOT_API_KEY`.

### 4. Activar GitHub Pages

1. Ir a tu repo → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / folder: `/dashboard`
4. Guardar

Tu dashboard quedará disponible en: `https://TU_USUARIO.github.io/bot-quorum/`

---

## Agregar un nuevo proyecto de ley

1. Ir a tu repo en GitHub → **Actions → Monitor de intención de voto → Run workflow**
2. Completar:
   - **Nombre del proyecto de ley:** ej. `Ley de Presupuesto 2027`
   - **Fecha de votación:** ej. `2026-06-15` (opcional)
3. Hacer clic en **Run workflow**

El bot arranca el monitoreo inmediatamente y lo sigue corriendo 3 veces por día.

---

## Uso local (opcional)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Crear archivo de variables de entorno
cp .env.example .env
# Editar .env con tus claves

# Agregar un proyecto y correrlo
python -m src.monitor --bill "Ley de Presupuesto 2027" --date "2026-06-15" --run

# Correr todos los proyectos activos
python -m src.monitor

# Enviar resumen diario por WhatsApp
python -m src.monitor --summary
```

---

## Estructura del proyecto

```
Bot Quorum/
├── .github/workflows/
│   ├── monitor.yml          # Cron 3x/día + trigger manual
│   └── update_deputies.yml  # Actualización mensual de nómina
├── config/
│   └── deputies.yaml        # Nómina actualizada de diputados
├── data/
│   ├── bills.yaml           # Proyectos activos
│   └── bills/
│       └── {slug}/
│           ├── latest.json  # Snapshot actual
│           └── YYYY-MM-DD.json  # Historial
├── dashboard/               # Publicado en GitHub Pages
│   ├── index.html
│   ├── style.css
│   └── app.js
├── src/
│   ├── scraper.py           # Google News RSS
│   ├── analyzer.py          # Gemini Flash
│   ├── storage.py           # Gestión de datos
│   ├── alerts.py            # WhatsApp via CallMeBot
│   └── monitor.py           # Orquestador
└── scripts/
    └── fetch_deputies.py    # Actualización mensual de nómina
```

---

## Costo

**$0** — Todo gratuito:
- GitHub Actions (2000 min/mes gratis)
- GitHub Pages (hosting gratis)
- Google News RSS (sin API key)
- Gemini Flash (free tier: 15 req/min, 1M tokens/día)
- CallMeBot WhatsApp (gratis)
