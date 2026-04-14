import psycopg2
import psycopg2.extras
import datetime
from config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD


def _normalize(row: dict) -> dict:
    """Convierte tipos no-JSON-serializables (date, datetime, Decimal) a tipos básicos."""
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime.datetime):
            out[k] = v.isoformat()
        elif isinstance(v, datetime.date):
            out[k] = v.isoformat()          # "2026-04-11"
        else:
            out[k] = v
    return out

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
    en_hero          BOOLEAN      DEFAULT FALSE,
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
    id           SERIAL PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL,
    email        VARCHAR(200),
    telefono     VARCHAR(30),
    empresa      VARCHAR(150),
    mensaje      TEXT         NOT NULL,
    producto_ref VARCHAR(300),
    creado_en    TIMESTAMP    DEFAULT NOW(),
    leido        BOOLEAN      DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS cotizaciones (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(150) NOT NULL,
    email         VARCHAR(200),
    telefono      VARCHAR(30),
    empresa       VARCHAR(150),
    nota          TEXT,
    items         TEXT         NOT NULL,
    total_sin_iva NUMERIC(15,2),
    total_con_iva NUMERIC(15,2),
    iva_pct       INT          DEFAULT 13,
    leido         BOOLEAN      DEFAULT FALSE,
    creado_en     TIMESTAMP    DEFAULT NOW()
);

ALTER TABLE contacto ADD COLUMN IF NOT EXISTS producto_ref VARCHAR(300);
ALTER TABLE catalogo_productos ADD COLUMN IF NOT EXISTS stock INT DEFAULT 0;
ALTER TABLE catalogo_productos ADD COLUMN IF NOT EXISTS subcategoria VARCHAR(150);

CREATE TABLE IF NOT EXISTS pedidos (
    id              SERIAL PRIMARY KEY,
    num_pedido      VARCHAR(20) UNIQUE,
    tipo_factura    VARCHAR(20)  NOT NULL DEFAULT 'ticket',  -- 'ticket' | 'factura'
    nombre          VARCHAR(200) NOT NULL,
    email           VARCHAR(200),
    telefono        VARCHAR(30),
    cedula          VARCHAR(30),
    direccion       TEXT,
    cod_actividad   VARCHAR(20),
    items           TEXT         NOT NULL,
    total_sin_iva   NUMERIC(15,2),
    total_con_iva   NUMERIC(15,2),
    iva_pct         INT          DEFAULT 13,
    nota_cliente    TEXT,
    estado          VARCHAR(30)  DEFAULT 'pendiente',
    link_pago       TEXT,
    nota_vendedor   TEXT,
    leido           BOOLEAN      DEFAULT FALSE,
    creado_en       TIMESTAMP    DEFAULT NOW(),
    actualizado_en  TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ofertas (
    id             SERIAL PRIMARY KEY,
    producto_id    INT           NOT NULL REFERENCES catalogo_productos(id) ON DELETE CASCADE,
    precio_oferta  NUMERIC(15,2) NOT NULL,
    descuento_pct  NUMERIC(5,2),
    etiqueta       VARCHAR(80)   DEFAULT 'OFERTA',
    fecha_inicio   TIMESTAMP     NOT NULL DEFAULT NOW(),
    fecha_fin      TIMESTAMP     NOT NULL,
    activa         BOOLEAN       DEFAULT TRUE,
    creado_en      TIMESTAMP     DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ofertas_unica ON ofertas(producto_id)
    WHERE activa = TRUE;

CREATE TABLE IF NOT EXISTS descuentos_volumen (
    id             SERIAL PRIMARY KEY,
    producto_id    INT           NOT NULL REFERENCES catalogo_productos(id) ON DELETE CASCADE,
    cantidad_min   INT           NOT NULL,  -- desde esta cantidad aplica
    descuento_pct  NUMERIC(5,2)  NOT NULL,  -- % de descuento sobre precio_ref
    activo         BOOLEAN       DEFAULT TRUE,
    creado_en      TIMESTAMP     DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dv_producto ON descuentos_volumen(producto_id)
    WHERE activo = TRUE;

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
    ('iva_porcentaje',          '13'),
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
            return [_normalize(dict(r)) for r in rows] if many else (_normalize(dict(rows)) if rows else None)
    finally:
        conn.close()


def execute(sql: str, params=(), returning=False):
    """Ejecuta INSERT/UPDATE/DELETE, opcionalmente retorna fila."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            result = _normalize(dict(cur.fetchone())) if returning and cur.description else None
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

# ── Migraciones adicionales (corren en init_db via ALTER IF NOT EXISTS) ───────
DDL_CLIENTES = '''
CREATE TABLE IF NOT EXISTS clientes (
    id           SERIAL PRIMARY KEY,
    google_id    VARCHAR(100) UNIQUE NOT NULL,
    email        VARCHAR(200) NOT NULL,
    nombre       VARCHAR(200),
    foto_url     VARCHAR(500),
    creado_en    TIMESTAMP DEFAULT NOW(),
    ultimo_login TIMESTAMP DEFAULT NOW()
);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS cliente_id INT REFERENCES clientes(id);
'''
