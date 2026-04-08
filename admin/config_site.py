from db import query, execute

def get_config() -> dict:
    rows = query("SELECT clave, valor FROM site_config")
    return {r["clave"]: r["valor"] for r in rows}

def set_config(clave: str, valor: str):
    execute("""
        INSERT INTO site_config (clave, valor) VALUES (%s,%s)
        ON CONFLICT (clave) DO UPDATE SET valor=EXCLUDED.valor
    """, (clave, valor))

def set_config_bulk(data: dict):
    for k, v in data.items():
        set_config(k, v)

def get_contactos(leido=None) -> list:
    where = "" if leido is None else "WHERE leido=%s"
    params = () if leido is None else (leido,)
    return query(f"SELECT * FROM contacto {where} ORDER BY creado_en DESC", params)

def marcar_leido(contact_id: int):
    execute("UPDATE contacto SET leido=TRUE WHERE id=%s", (contact_id,))

def get_stats_contacto() -> dict:
    rows = query("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE NOT leido) AS no_leidos FROM contacto")
    return rows[0] if rows else {"total": 0, "no_leidos": 0}
