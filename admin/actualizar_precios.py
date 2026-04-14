from db import query, execute


def comparar_precios() -> list:
    """
    Compara precio_ref y stock del catálogo web contra SYMA.
    Devuelve solo los productos con diferencia en precio O en stock.
    """
    productos = query(
        "SELECT id, codigo, nombre, precio_ref, stock FROM catalogo_productos ORDER BY nombre"
    )
    if not productos:
        return []

    codigos = [p["codigo"] for p in productos]

    try:
        import pyodbc
        from config import SYMA_DSN
        conn = pyodbc.connect(SYMA_DSN)
        cur  = conn.cursor()

        placeholders = ",".join(["?" for _ in codigos])
        cur.execute(
            f"SELECT RTRIM(ID_PRODUCTO) AS codigo, ISNULL(PRECIO, 0) AS precio, ISNULL(CANTIDAD, 0) AS stock "
            f"FROM PRODUCTOS WHERE RTRIM(ID_PRODUCTO) IN ({placeholders})",
            codigos
        )
        syma = {row[0]: {"precio": float(row[1]), "stock": int(row[2])} for row in cur.fetchall()}
        conn.close()
    except Exception as e:
        return [{"error": str(e)}]

    cambios = []
    for p in productos:
        datos_syma = syma.get(p["codigo"])
        if datos_syma is None:
            continue

        precio_web  = float(p["precio_ref"]) if p["precio_ref"] else 0.0
        stock_web   = int(p["stock"]) if p["stock"] is not None else 0
        precio_syma = datos_syma["precio"]
        stock_syma  = datos_syma["stock"]

        precio_diff = round(precio_syma, 2) != round(precio_web, 2)
        stock_diff  = stock_syma != stock_web

        if precio_diff or stock_diff:
            cambios.append({
                "id":          p["id"],
                "codigo":      p["codigo"],
                "nombre":      p["nombre"],
                "precio_web":  precio_web,
                "precio_syma": precio_syma,
                "precio_diff": precio_diff,
                "dif_precio":  round(precio_syma - precio_web, 2),
                "stock_web":   stock_web,
                "stock_syma":  stock_syma,
                "stock_diff":  stock_diff,
            })

    return cambios


def aplicar_precios(cambios: list) -> int:
    """
    Recibe lista de {id, precio_syma, stock_syma} y actualiza precio_ref y stock en la BD web.
    Retorna cantidad de registros actualizados.
    """
    count = 0
    for c in cambios:
        execute(
            "UPDATE catalogo_productos SET precio_ref=%s, stock=%s, actualizado_en=NOW() WHERE id=%s",
            (c["precio_syma"], c["stock_syma"], c["id"])
        )
        count += 1
    return count
