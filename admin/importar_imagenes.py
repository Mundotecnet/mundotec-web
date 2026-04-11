"""
Utilitario de importación automática de imágenes por código de producto.
"""
import os
import shutil
import uuid
from pathlib import Path
from db import query, execute

BASE_DIR    = Path(__file__).resolve().parent.parent
AUTO_DIR    = BASE_DIR / "static" / "uploads" / "auto-import"
PROC_DIR    = AUTO_DIR / "procesados"
DEST_DIR    = BASE_DIR / "static" / "uploads" / "productos"
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}


def listar_pendientes() -> list:
    """Archivos de imagen en la carpeta auto-import (sin procesados)."""
    if not AUTO_DIR.exists():
        return []
    archivos = []
    for f in sorted(AUTO_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in EXTENSIONES:
            codigo  = f.stem
            prod    = _buscar_producto(codigo)
            ya_img  = _tiene_imagen(prod["id"]) if prod else False
            archivos.append({
                "nombre":   f.name,
                "codigo":   codigo,
                "size_kb":  round(f.stat().st_size / 1024, 1),
                "producto": prod["nombre"] if prod else None,
                "ya_tiene": ya_img,
                "encontrado": prod is not None,
            })
    return archivos


def ejecutar_importacion(forzar: bool = False) -> dict:
    """Procesa todos los archivos pendientes. Retorna resumen."""
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    pendientes   = listar_pendientes()
    importadas   = []
    omitidas     = []
    no_encontradas = []
    errores      = []

    for item in pendientes:
        archivo = AUTO_DIR / item["nombre"]
        ext     = Path(item["nombre"]).suffix.lower()

        if not item["encontrado"]:
            no_encontradas.append(item["nombre"])
            continue

        prod = _buscar_producto(item["codigo"])
        prod_id = prod["id"]

        if item["ya_tiene"] and not forzar:
            omitidas.append(item["nombre"])
            continue

        nombre_dest = f"p{prod_id}_{uuid.uuid4().hex[:8]}{ext}"
        ruta_dest   = DEST_DIR / nombre_dest
        url_path    = f"/static/uploads/productos/{nombre_dest}"
        principal   = not item["ya_tiene"]

        try:
            shutil.copy2(archivo, ruta_dest)
            _registrar_imagen(prod_id, url_path, principal)
            shutil.move(str(archivo), str(PROC_DIR / item["nombre"]))
            importadas.append({
                "archivo":  item["nombre"],
                "producto": prod["nombre"],
                "principal": principal,
            })
        except Exception as e:
            errores.append({"archivo": item["nombre"], "error": str(e)})

    return {
        "importadas":     importadas,
        "omitidas":       omitidas,
        "no_encontradas": no_encontradas,
        "errores":        errores,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _buscar_producto(codigo: str):
    return query(
        "SELECT id, codigo, nombre FROM catalogo_productos WHERE UPPER(codigo)=UPPER(%s)",
        (codigo,), many=False
    )

def _tiene_imagen(prod_id: int) -> bool:
    return bool(query(
        "SELECT id FROM catalogo_imagenes WHERE producto_id=%s LIMIT 1", (prod_id,)
    ))

def _registrar_imagen(prod_id: int, url_path: str, es_principal: bool):
    if es_principal:
        execute("UPDATE catalogo_imagenes SET es_principal=FALSE WHERE producto_id=%s", (prod_id,))
    execute("""
        INSERT INTO catalogo_imagenes (producto_id, url_path, es_principal, orden)
        VALUES (%s, %s, %s, 0)
    """, (prod_id, url_path, es_principal))
