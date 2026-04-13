from db import query, execute


def comparar_precios() -> list:
    """
    Compara precio_ref del catálogo web contra PRECIO en SYMA.
    Devuelve solo los productos con diferencia de precio.
    """
    productos = query(
        "SELECT id, codigo, nombre, precio_ref FROM catalogo_productos ORDER BY nombre"
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
            f"SELECT RTRIM(ID_PRODUCTO) AS codigo, ISNULL(PRECIO, 0) AS precio "
            f"FROM PRODUCTOS WHERE RTRIM(ID_PRODUCTO) IN ({placeholders})",
            codigos
        )
        syma = {row[0]: float(row[1]) for row in cur.fetchall()}
        conn.close()
    except Exception as e:
        return [{"error": str(e)}]

    cambios = []
    for p in productos:
        precio_syma = syma.get(p["codigo"])
        if precio_syma is None:
            continue
        precio_web = float(p["precio_ref"]) if p["precio_ref"] else 0.0
        if round(precio_syma, 2) != round(precio_web, 2):
            cambios.append({
                "id":         p["id"],
                "codigo":     p["codigo"],
                "nombre":     p["nombre"],
                "precio_web": precio_web,
                "precio_syma": precio_syma,
                "diferencia": round(precio_syma - precio_web, 2),
            })

    return cambios


def aplicar_precios(cambios: list) -> int:
    """
    Recibe lista de {id, precio_syma} y actualiza precio_ref en la BD web.
    Retorna cantidad de registros actualizados.
    """
    count = 0
    for c in cambios:
        execute(
            "UPDATE catalogo_productos SET precio_ref=%s, actualizado_en=NOW() WHERE id=%s",
            (c["precio_syma"], c["id"])
        )
        count += 1
    return count
