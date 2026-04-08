import os

# ── PostgreSQL ────────────────────────────────────────────────────────────────
PG_HOST     = os.getenv("PG_HOST",     "localhost")
PG_PORT     = int(os.getenv("PG_PORT", "5432"))
PG_DB       = os.getenv("PG_DB",       "mundotec_web")
PG_USER     = os.getenv("PG_USER",     "mw_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "Mw@Web2026!")

# ── Conexión SQL Server Syma (solo para importar productos) ────────────────────
SYMA_DSN = (
    r"DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=192.168.10.15\SQLEXPRESS;"
    r"DATABASE=Syma;"
    r"UID=sa;"
    r"PWD=sqladmin;"
    r"TrustServerCertificate=yes"
)

# ── App ───────────────────────────────────────────────────────────────────────
APP_HOST   = "0.0.0.0"
APP_PORT   = 8001
SECRET_KEY = "mw-web-secret-2026-change-in-prod"

# ── Rutas de archivos ─────────────────────────────────────────────────────────
BASE_DIR          = os.path.dirname(__file__)
UPLOAD_PRODUCTOS  = os.path.join(BASE_DIR, "static", "uploads", "productos")
UPLOAD_PROYECTOS  = os.path.join(BASE_DIR, "static", "uploads", "proyectos")
