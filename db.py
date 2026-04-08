import psycopg2
import psycopg2.extras
from config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD

DDL = """
CREATE TABLE IF NOT EXISTS site_config (
    clave  VARCHAR(100) PRIMARY KEY,
    valor  TEXT
);

CREATE TABLE IF NOT EXISTS proyectos (
    id           SERIAL PRIMARY KEY,
    titulo       VARCHAR(200)  NOT NULL,
    descripcion  TEXT,
    imagen_path  VARCHAR(500),
    categoria    VARCHAR(100),
    activo       BOOLEAN       DEFAULT TRUE,
    destacado    BOOLEAN       DEFAULT FALSE,
    orden        INT           DEFAULT 0,
    fecha        DATE
);

CREATE TABLE IF NOT EXISTS catalogo_productos (
    id               SERIAL PRIMARY KEY,
    codigo           VARCHAR(50)  NOT NULL UNIQUE,
    nombre           VARCHAR(300) NOT NULL,
    descripcion_syma TEXT,
    descripcion_web  TEXT,
    categoria        VARCHAR(150),
    activo           BOOLEAN      DEFAULT TRUE,
    destacado        BOOLEAN      DEFAULT FALSE,
    orden            INT          DEFAULT 0,
    ficha_path       VARCHAR(500),
    precio_ref       NUMERIC(15,2),
    creado_en        TIMESTAMP    DEFAULT NOW(),
    actualizado_en   TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS catalogo_imagenes (
    id           SERIAL PRIMARY KEY,
    producto_id  INT          REFERENCES catalogo_productos(id) ON DELETE CASCADE,
    url_path     VARCHAR(500) NOT NULL,
    es_principal BOOLEAN      DEFAULT FALSE,
    orden        INT          DEFAULT 0
);

CREATE TABLE IF NOT EXISTS catalogo_specs (
    id          SERIAL PRIMARY KEY,
    producto_id INT          REFERENCES catalogo_productos(id) ON DELETE CASCADE,
    etiqueta    VARCHAR(100) NOT NULL,
    valor       VARCHAR(500) NOT NULL,
    orden       INT          DEFAULT 0
);

CREATE TABLE IF NOT EXISTS contacto (
    id        SERIAL PRIMARY KEY,
    nombre    VARCHAR(150) NOT NULL,
    email     VARCHAR(200),
    telefono  VARCHAR(30),
    empresa   VARCHAR(150),
    mensaje   TEXT         NOT NULL,
    creado_en TIMESTAMP    DEFAULT NOW(),
    leido     BOOLEAN      DEFAULT FALSE
);

-- Datos iniciales de configuración
INSERT INTO site_config (clave, valor) VALUES
    ('empresa_nombre',         'MUNDOTEC'),
    ('empresa_slogan',         'Soluciones tecnológicas para su negocio'),
    ('empresa_descripcion',    'Empresa especializada en tecnología, soporte técnico y soluciones integrales para su negocio.'),
    ('empresa_telefono',       ''),
    ('empresa_email',          ''),
    ('empresa_whatsapp',       ''),
    ('empresa_direccion',      ''),
    ('empresa_anio_fundacion', '2010'),
    ('hero_titulo',            'Tecnología que impulsa su negocio'),
    ('hero_subtitulo',         'Productos, soporte técnico y soluciones a medida'),
    ('color_primario',         '#1E4E8C'),
    ('color_acento',           '#E67E22'),
    ('smtp_host',              ''),
    ('smtp_port',              '587'),
    ('smtp_user',              ''),
    ('smtp_password',          ''),
    ('smtp_from',              ''),
    ('notif_to',               '')
ON CONFLICT (clave) DO NOTHING;
"""


def get_connection():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB,
        user=PG_USER, password=PG_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def query(sql: str, params=(), many=True):
    """Ejecuta SELECT y devuelve lista de dicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if many else cur.fetchone()
            return [dict(r) for r in rows] if many else (dict(rows) if rows else None)
    finally:
        conn.close()


def execute(sql: str, params=(), returning=False):
    """Ejecuta INSERT/UPDATE/DELETE, opcionalmente retorna fila."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            result = dict(cur.fetchone()) if returning and cur.description else None
            conn.commit()
            return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
        print("[DB] PostgreSQL mundotec_web inicializada correctamente.")
    finally:
        conn.close()
