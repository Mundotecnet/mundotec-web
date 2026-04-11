#!/home/lroot/mundotec-web/venv/bin/python3
"""
import_imagenes.py — Importación automática de imágenes por código de producto
===============================================================================
Coloque las imágenes en:
    /home/lroot/mundotec-web/static/uploads/auto-import/

Nombre del archivo = código del producto exacto (sin importar mayúsculas)
Extensiones soportadas: jpg, jpeg, png, webp, avif, gif

Ejemplos de nombres válidos:
    PRD001.jpg
    ab-123.png
    ROUTER_WRT54G.jpeg

Uso:
    cd /home/lroot/mundotec-web
    python3 scripts/import_imagenes.py

    # Solo ver qué procesaría sin hacer cambios:
    python3 scripts/import_imagenes.py --dry-run

    # Sobreescribir si ya tiene imagen:
    python3 scripts/import_imagenes.py --forzar
"""

import os
import sys
import shutil
import uuid
import argparse
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent.parent
AUTO_DIR     = BASE_DIR / "static" / "uploads" / "auto-import"
PROC_DIR     = AUTO_DIR / "procesados"
DEST_DIR     = BASE_DIR / "static" / "uploads" / "productos"
EXTENSIONES  = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}

# ── Agrega el proyecto al path para importar db ───────────────────────────────
sys.path.insert(0, str(BASE_DIR))
from db import query, execute


# ─────────────────────────────────────────────────────────────────────────────

def buscar_producto(codigo: str):
    """Busca producto por código exacto (case-insensitive)."""
    return query(
        "SELECT id, codigo, nombre FROM catalogo_productos WHERE UPPER(codigo)=UPPER(%s)",
        (codigo,), many=False
    )


def tiene_imagenes(prod_id: int) -> bool:
    rows = query("SELECT id FROM catalogo_imagenes WHERE producto_id=%s LIMIT 1", (prod_id,))
    return len(rows) > 0


def registrar_imagen(prod_id: int, url_path: str, es_principal: bool):
    if es_principal:
        execute("UPDATE catalogo_imagenes SET es_principal=FALSE WHERE producto_id=%s", (prod_id,))
    execute("""
        INSERT INTO catalogo_imagenes (producto_id, url_path, es_principal, orden)
        VALUES (%s, %s, %s, 0)
    """, (prod_id, url_path, es_principal))


def procesar(dry_run: bool, forzar: bool):
    archivos = sorted([
        f for f in AUTO_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSIONES
    ])

    if not archivos:
        print("📂 No hay imágenes en la carpeta de importación.")
        print(f"   Ruta: {AUTO_DIR}")
        return

    print(f"\n🔍 {len(archivos)} imagen(es) encontrada(s) en {AUTO_DIR}\n")
    print(f"{'ARCHIVO':<35} {'CÓDIGO':<20} {'RESULTADO'}")
    print("─" * 75)

    importados   = []
    no_encontrados = []
    omitidos     = []
    errores      = []

    for archivo in archivos:
        codigo  = archivo.stem          # nombre sin extensión
        ext     = archivo.suffix.lower()
        display = archivo.name[:34]

        prod = buscar_producto(codigo)

        if not prod:
            no_encontrados.append(archivo.name)
            print(f"  {display:<35} {codigo:<20} ❌ Código no encontrado en catálogo")
            continue

        prod_id = prod["id"]
        ya_tiene = tiene_imagenes(prod_id)

        if ya_tiene and not forzar:
            omitidos.append(archivo.name)
            print(f"  {display:<35} {codigo:<20} ⚠️  Ya tiene imagen (use --forzar)")
            continue

        # Nombre de destino: p{id}_{uuid8}{ext}
        nombre_dest = f"p{prod_id}_{uuid.uuid4().hex[:8]}{ext}"
        ruta_dest   = DEST_DIR / nombre_dest
        url_path    = f"/static/uploads/productos/{nombre_dest}"
        principal   = not ya_tiene  # primera imagen = principal

        if dry_run:
            importados.append(archivo.name)
            tag = "(reemplazaría principal)" if ya_tiene and forzar else "(sería principal)"
            print(f"  {display:<35} {codigo:<20} ✅ DRY-RUN → {nombre_dest} {tag}")
            continue

        try:
            shutil.copy2(archivo, ruta_dest)
            registrar_imagen(prod_id, url_path, principal)
            # Mover a procesados
            shutil.move(str(archivo), str(PROC_DIR / archivo.name))
            importados.append(archivo.name)
            tag = "← PRINCIPAL" if principal else "(adicional)"
            print(f"  {display:<35} {codigo:<20} ✅ Importada {tag}")
        except Exception as e:
            errores.append(archivo.name)
            print(f"  {display:<35} {codigo:<20} 💥 Error: {e}")

    # Resumen
    print("\n" + "═" * 75)
    print(f"  ✅ Importadas    : {len(importados)}")
    print(f"  ⚠️  Omitidas      : {len(omitidos)}")
    print(f"  ❌ No encontradas: {len(no_encontrados)}")
    if errores:
        print(f"  💥 Con error     : {len(errores)}")
    if dry_run:
        print("\n  ℹ️  Modo DRY-RUN — no se realizó ningún cambio.")
    elif importados:
        print(f"\n  📁 Archivos procesados movidos a: {PROC_DIR}")
    print()

    if no_encontrados:
        print("  Códigos no encontrados:")
        for n in no_encontrados:
            print(f"    • {n}")
        print()


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importar imágenes de productos por código")
    parser.add_argument("--dry-run", action="store_true",
                        help="Ver qué se procesaría sin hacer cambios reales")
    parser.add_argument("--forzar", action="store_true",
                        help="Agregar imagen aunque el producto ya tenga una")
    args = parser.parse_args()

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    procesar(dry_run=args.dry_run, forzar=args.forzar)
