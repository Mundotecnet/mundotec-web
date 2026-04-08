from db import query, execute

def get_catalogo_publico(categoria="", busqueda="", destacado=False) -> list:
    filtros = ["p.activo = TRUE"]
    params  = []
    if destacado:
        filtros.append("p.destacado = TRUE")
    if categoria:
        filtros.append("p.categoria ILIKE %s"); params.append(f"%{categoria}%")
    if busqueda:
        filtros.append("(p.nombre ILIKE %s OR p.descripcion_web ILIKE %s)")
        params += [f"%{busqueda}%", f"%{busqueda}%"]
    where = "WHERE " + " AND ".join(filtros)
    prods = query(f"""
        SELECT p.*,
               i.url_path AS imagen_principal
        FROM catalogo_productos p
        LEFT JOIN catalogo_imagenes i ON i.producto_id=p.id AND i.es_principal=TRUE
        {where}
        ORDER BY p.orden, p.nombre
    """, params)
    return prods


def get_producto_publico(prod_id: int) -> dict:
    p = query("SELECT * FROM catalogo_productos WHERE id=%s AND activo=TRUE",
              (prod_id,), many=False)
    if not p:
        return None
    p["imagenes"] = query("SELECT * FROM catalogo_imagenes WHERE producto_id=%s ORDER BY orden, es_principal DESC", (prod_id,))
    p["specs"]    = query("SELECT * FROM catalogo_specs    WHERE producto_id=%s ORDER BY orden", (prod_id,))
    return p


def get_categorias_publico() -> list:
    rows = query("""
        SELECT DISTINCT categoria FROM catalogo_productos
        WHERE activo=TRUE AND categoria IS NOT NULL AND categoria <> ''
        ORDER BY categoria
    """)
    return [r["categoria"] for r in rows]


def registrar_contacto(nombre, email, telefono, empresa, mensaje,
                       producto_ref="") -> dict:
    return execute("""
        INSERT INTO contacto (nombre, email, telefono, empresa, mensaje, producto_ref)
        VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
    """, (nombre, email or None, telefono or None, empresa or None,
          mensaje, producto_ref or None),
         returning=True)


def get_proyectos_publico(categoria="") -> list:
    filtros = ["activo=TRUE"]
    params  = []
    if categoria:
        filtros.append("categoria ILIKE %s"); params.append(f"%{categoria}%")
    where = "WHERE " + " AND ".join(filtros)
    return query(f"SELECT * FROM proyectos {where} ORDER BY orden, fecha DESC NULLS LAST", params)


def registrar_cotizacion(nombre, email, telefono, empresa, nota, items, total_sin_iva, total_con_iva, iva_pct=13) -> dict:
    import json
    return execute("""
        INSERT INTO cotizaciones (nombre, email, telefono, empresa, nota, items, total_sin_iva, total_con_iva, iva_pct)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (nombre, email or None, telefono or None, empresa or None, nota or None,
          json.dumps(items, ensure_ascii=False),
          total_sin_iva, total_con_iva, iva_pct),
         returning=True)

def get_cotizaciones(leido=None) -> list:
    import json
    where  = "" if leido is None else "WHERE leido=%s"
    params = () if leido is None else (leido,)
    rows   = query(f"SELECT * FROM cotizaciones {where} ORDER BY creado_en DESC", params)
    for r in rows:
        try:    r["items"] = json.loads(r["items"]) if isinstance(r["items"], str) else r["items"]
        except: r["items"] = []
    return rows

def get_stats_cotizaciones() -> dict:
    rows = query("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE NOT leido) AS no_leidas FROM cotizaciones")
    return rows[0] if rows else {"total": 0, "no_leidas": 0}

def marcar_cotizacion_leida(cot_id: int):
    execute("UPDATE cotizaciones SET leido=TRUE WHERE id=%s", (cot_id,))
