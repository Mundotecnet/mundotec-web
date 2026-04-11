import os
from db import query, execute

def get_proyectos(activo=None) -> list:
    where = "" if activo is None else "WHERE activo=%s"
    params = () if activo is None else (activo,)
    return query(f"SELECT * FROM proyectos {where} ORDER BY orden, id DESC", params)

def get_proyecto(proj_id: int) -> dict:
    return query("SELECT * FROM proyectos WHERE id=%s", (proj_id,), many=False)

def crear_proyecto(titulo, descripcion="", categoria="", fecha=None) -> dict:
    return execute("""
        INSERT INTO proyectos (titulo, descripcion, categoria, fecha)
        VALUES (%s,%s,%s,%s) RETURNING id, titulo
    """, (titulo, descripcion, categoria, fecha), returning=True)

def actualizar_proyecto(proj_id: int, data: dict):
    execute("""
        UPDATE proyectos SET titulo=%s, descripcion=%s, categoria=%s,
        activo=%s, destacado=%s, en_slider=%s, orden=%s, fecha=%s WHERE id=%s
    """, (data.get("titulo"), data.get("descripcion",""), data.get("categoria",""),
          data.get("activo", True), data.get("destacado", False),
          data.get("en_slider", False),
          data.get("orden", 0), data.get("fecha"), proj_id))

def actualizar_imagen_proyecto(proj_id: int, img_path: str):
    execute("UPDATE proyectos SET imagen_path=%s WHERE id=%s", (img_path, proj_id))

def eliminar_proyecto(proj_id: int):
    row = query("SELECT imagen_path FROM proyectos WHERE id=%s", (proj_id,), many=False)
    if row and row.get("imagen_path"):
        rel  = row["imagen_path"].lstrip("/")
        ruta = os.path.join(os.path.dirname(__file__), '..', rel)
        try: os.remove(os.path.normpath(ruta))
        except FileNotFoundError: pass
    execute("DELETE FROM proyectos WHERE id=%s", (proj_id,))

def get_categorias_proyectos() -> list:
    rows = query("SELECT DISTINCT categoria FROM proyectos WHERE categoria IS NOT NULL AND categoria <> '' ORDER BY categoria")
    return [r["categoria"] for r in rows]
