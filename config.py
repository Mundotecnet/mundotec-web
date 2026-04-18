import os

# Cargar .env local si existe (no requiere dependencias externas)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

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

# ── Correo SMTP (notificaciones de contacto) ──────────────────────────────────
# Dejar vacío para deshabilitar notificaciones por correo
SMTP_HOST     = os.getenv("SMTP_HOST",     "")          # ej: smtp.gmail.com
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))      # 587=TLS, 465=SSL
SMTP_USER     = os.getenv("SMTP_USER",     "")          # tu correo
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")          # contraseña / app password
SMTP_FROM     = os.getenv("SMTP_FROM",     "")          # remitente (puede ser = SMTP_USER)
NOTIF_TO      = os.getenv("NOTIF_TO",      "")          # correo destino del admin

# ── Claude AI (generación de descripciones) ───────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Rutas de archivos ─────────────────────────────────────────────────────────
BASE_DIR          = os.path.dirname(__file__)
UPLOAD_PRODUCTOS  = os.path.join(BASE_DIR, "static", "uploads", "productos")
UPLOAD_PROYECTOS  = os.path.join(BASE_DIR, "static", "uploads", "proyectos")

# ── Google OAuth ──────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID",     "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
