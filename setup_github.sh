#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_github.sh — Deploy completo del Bot Quorum a GitHub
# Ejecutar UNA SOLA VEZ después de: gh auth login
# ─────────────────────────────────────────────────────────────────────────────
set -e

GH_BIN="${GH_BIN:-/tmp/gh_dir/gh_2.62.0_macOS_arm64/bin/gh}"
REPO_NAME="bot-quorum"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Setup del Bot Quorum en GitHub         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Verificar gh instalado ────────────────────────────────────────────────
if ! command -v gh &>/dev/null && ! "$GH_BIN" --version &>/dev/null; then
  echo "❌ gh CLI no encontrado. Instalalo desde https://cli.github.com"
  exit 1
fi
GH=$(command -v gh || echo "$GH_BIN")

# ── 2. Verificar autenticación ───────────────────────────────────────────────
if ! $GH auth status &>/dev/null; then
  echo "⚠ No estás autenticado en GitHub. Ejecutá:"
  echo "  $GH auth login"
  echo ""
  echo "Luego volvé a correr este script."
  exit 1
fi

GH_USER=$($GH api user --jq '.login')
echo "✓ Autenticado como: $GH_USER"
echo ""

# ── 3. Crear repositorio privado ─────────────────────────────────────────────
echo "→ Creando repositorio privado '$REPO_NAME'..."
$GH repo create "$REPO_NAME" \
  --private \
  --description "Poroteo legislativo — Intención de voto de diputados HCDN" \
  || echo "  (El repo puede ya existir, continuando...)"

# ── 4. Push inicial ──────────────────────────────────────────────────────────
echo "→ Subiendo código a GitHub..."
git remote add origin "https://github.com/$GH_USER/$REPO_NAME.git" 2>/dev/null || \
  git remote set-url origin "https://github.com/$GH_USER/$REPO_NAME.git"
git push -u origin main

echo ""
echo "✓ Código subido. Repo: https://github.com/$GH_USER/$REPO_NAME"
echo ""

# ── 5. Configurar Secrets ────────────────────────────────────────────────────
echo "═══════════════════════════════════════════"
echo " Configuración de Secrets (tecleá los valores)"
echo "═══════════════════════════════════════════"
echo ""

read -p "GEMINI_API_KEY (de aistudio.google.com): " GEMINI_KEY
$GH secret set GEMINI_API_KEY --body "$GEMINI_KEY" --repo "$GH_USER/$REPO_NAME"
echo "  ✓ GEMINI_API_KEY configurado"

read -p "TELEGRAM_BOT_TOKEN (lo dio @BotFather): " TG_TOKEN
$GH secret set TELEGRAM_BOT_TOKEN --body "$TG_TOKEN" --repo "$GH_USER/$REPO_NAME"
echo "  ✓ TELEGRAM_BOT_TOKEN configurado"

read -p "TELEGRAM_CHAT_ID (tu chat id de Telegram): " TG_CHAT
$GH secret set TELEGRAM_CHAT_ID --body "$TG_CHAT" --repo "$GH_USER/$REPO_NAME"
echo "  ✓ TELEGRAM_CHAT_ID configurado"

# ── 6. Habilitar GitHub Pages ────────────────────────────────────────────────
echo ""
echo "→ Habilitando GitHub Pages desde /dashboard..."
$GH api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  "/repos/$GH_USER/$REPO_NAME/pages" \
  -f source='{"branch":"main","path":"/dashboard"}' 2>/dev/null || \
  echo "  (Pages puede requerir activación manual en Settings → Pages)"

# ── 7. Resumen final ─────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   ¡Todo listo!                                          ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  Repo:      https://github.com/$GH_USER/$REPO_NAME"
printf  "║  Dashboard: https://%s.github.io/%s/\n" "$GH_USER" "$REPO_NAME"
echo "║                                                          ║"
echo "║  Para agregar un proyecto de ley:                       ║"
echo "║  → GitHub → Actions → 'Monitor de intención de voto'   ║"
echo "║  → Run workflow → ingresá el nombre del proyecto        ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
