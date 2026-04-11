import os, shutil
from db import query, execute
from config import UPLOAD_PRODUCTOS

# ── Catálogo ──────────────────────────────────────────────────────────────────

def get_catalogo(activo=None, destacado=None, busqueda="", categoria="") -> list:
    filtros = []
    params  = []
    if activo is not None:
        filtros.append("activo = %s"); params.append(activo)
    if destacado:
        filtros.append("destacado = TRUE")
    if busqueda:
        filtros.append("(nombre ILIKE %s OR codigo ILIKE %s OR descripcion_web ILIKE %s)")
        params += [f"%{busqueda}%"] * 3
    if categoria:
        filtros.append("categoria ILIKE %s"); params.append(f"%{categoria}%")
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    return query(f"SELECT * FROM catalogo_productos {where} ORDER BY orden, nombre", params)


def get_producto(prod_id: int) -> dict:
    p = query("SELECT * FROM catalogo_productos WHERE id=%s", (prod_id,), many=False)
    if not p:
        return None
    p["imagenes"] = get_imagenes(prod_id)
    p["specs"]    = get_specs(prod_id)
    return p


def crear_producto(codigo, nombre, descripcion_syma="", descripcion_web="",
                   categoria="", precio_ref=None) -> dict:
    return execute("""
        INSERT INTO catalogo_productos
            (codigo, nombre, descripcion_syma, descripcion_web, categoria, precio_ref)
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING id, codigo, nombre
    """, (codigo, nombre, descripcion_syma or "", descripcion_web or "",
          categoria or "", precio_ref), returning=True)


def actualizar_producto(prod_id: int, data: dict):
    campos = ["nombre=%s","descripcion_web=%s","categoria=%s",
              "activo=%s","destacado=%s","en_hero=%s","orden=%s","precio_ref=%s",
              "actualizado_en=NOW()"]
    params = [data.get("nombre"), data.get("descripcion_web",""),
              data.get("categoria",""), data.get("activo", True),
              data.get("destacado", False), data.get("en_hero", False),
              data.get("orden", 0), data.get("precio_ref"), prod_id]
    execute(f"UPDATE catalogo_productos SET {','.join(campos)} WHERE id=%s", params)


def eliminar_producto(prod_id: int):
    execute("DELETE FROM catalogo_productos WHERE id=%s", (prod_id,))


def actualizar_ficha(prod_id: int, ficha_path: str):
    execute("UPDATE catalogo_productos SET ficha_path=%s, actualizado_en=NOW() WHERE id=%s",
            (ficha_path, prod_id))


# ── Imágenes ─────────────────────────────────────────────────────────────────

def get_imagenes(prod_id: int) -> list:
    return query("SELECT * FROM catalogo_imagenes WHERE producto_id=%s ORDER BY orden, es_principal DESC",
                 (prod_id,))


def agregar_imagen(prod_id: int, url_path: str, es_principal=False, orden=0) -> dict:
    if es_principal:
        execute("UPDATE catalogo_imagenes SET es_principal=FALSE WHERE producto_id=%s", (prod_id,))
    return execute("""
        INSERT INTO catalogo_imagenes (producto_id, url_path, es_principal, orden)
        VALUES (%s,%s,%s,%s) RETURNING id, url_path
    """, (prod_id, url_path, es_principal, orden), returning=True)


def eliminar_imagen(img_id: int):
    row = query("SELECT url_path FROM catalogo_imagenes WHERE id=%s", (img_id,), many=False)
    if row:
        rel  = row["url_path"].lstrip("/")
        ruta = os.path.join(os.path.dirname(__file__), '..', rel)
        try: os.remove(os.path.normpath(ruta))
        except FileNotFoundError: pass
    execute("DELETE FROM catalogo_imagenes WHERE id=%s", (img_id,))


def set_imagen_principal(img_id: int, prod_id: int):
    execute("UPDATE catalogo_imagenes SET es_principal=FALSE WHERE producto_id=%s", (prod_id,))
    execute("UPDATE catalogo_imagenes SET es_principal=TRUE  WHERE id=%s",          (img_id,))


# ── Especificaciones técnicas ─────────────────────────────────────────────────

def get_specs(prod_id: int) -> list:
    return query("SELECT * FROM catalogo_specs WHERE producto_id=%s ORDER BY orden",
                 (prod_id,))


def agregar_spec(prod_id: int, etiqueta: str, valor: str, orden=0) -> dict:
    return execute("""
        INSERT INTO catalogo_specs (producto_id, etiqueta, valor, orden)
        VALUES (%s,%s,%s,%s) RETURNING id
    """, (prod_id, etiqueta, valor, orden), returning=True)


def eliminar_spec(spec_id: int):
    execute("DELETE FROM catalogo_specs WHERE id=%s", (spec_id,))


def reemplazar_specs(prod_id: int, specs: list):
    """Reemplaza todas las specs de un producto. specs = [{"etiqueta":"X","valor":"Y"}]"""
    execute("DELETE FROM catalogo_specs WHERE producto_id=%s", (prod_id,))
    for i, s in enumerate(specs):
        agregar_spec(prod_id, s["etiqueta"], s["valor"], i)


# ── Categorías ────────────────────────────────────────────────────────────────

def get_categorias() -> list:
    rows = query("SELECT DISTINCT categoria FROM catalogo_productos "
                 "WHERE categoria IS NOT NULL AND categoria <> '' ORDER BY categoria")
    return [r["categoria"] for r in rows]


# ── Importar desde SYMA ───────────────────────────────────────────────────────

def buscar_en_syma(busqueda="", limit=200) -> list:
    """
    Conecta a SQL Server Syma y devuelve los productos con ID_PASILLO='02'
    (productos seleccionados para publicar en el catálogo web).
    Filtro adicional opcional por búsqueda de código o descripción.
    """
    try:
        import pyodbc
        from config import SYMA_DSN
        conn = pyodbc.connect(SYMA_DSN)
        cur  = conn.cursor()

        filtros = ["p.ESTADO='A'", "RTRIM(ISNULL(p.ID_PASILLO,''))='02'"]
        params  = []
        if busqueda:
            filtros.append("(RTRIM(p.ID_PRODUCTO) LIKE ? OR p.DESCRIPCION LIKE ?)")
            params += [f"%{busqueda}%", f"%{busqueda}%"]

        where = "WHERE " + " AND ".join(filtros)
        cur.execute(f"""
            SELECT TOP {limit}
                RTRIM(p.ID_PRODUCTO)             AS codigo,
                RTRIM(p.DESCRIPCION)             AS nombre,
                RTRIM(ISNULL(p.ID_CATEGORIA,'')) AS categoria,
                ISNULL(p.PRECIO, 0)              AS precio_ref,
                ISNULL(p.CANTIDAD, 0)            AS stock,
                RTRIM(ISNULL(p.NO_PARTE,''))     AS no_parte
            FROM PRODUCTOS p {where}
            ORDER BY p.DESCRIPCION
        """, params)
        cols = [d[0].lower() for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()

        # Marcar los que ya están en catálogo
        en_catalogo = {r["codigo"] for r in query("SELECT codigo FROM catalogo_productos")}
        for r in rows:
            r["en_catalogo"] = r["codigo"] in en_catalogo
        return rows
    except Exception as e:
        return [{"error": str(e)}]
