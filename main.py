import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request, Query, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import uuid

from config import APP_HOST, APP_PORT, SECRET_KEY, UPLOAD_PRODUCTOS, UPLOAD_PROYECTOS
from db import init_db, query as dbq, execute as dbx
from admin.catalogo    import (get_catalogo, get_producto, crear_producto, actualizar_producto,
                                eliminar_producto, actualizar_ficha, agregar_imagen,
                                eliminar_imagen, set_imagen_principal, reemplazar_specs,
                                get_categorias, buscar_en_syma)
from admin.proyectos   import (get_proyectos, get_proyecto, crear_proyecto,
                                actualizar_proyecto, actualizar_imagen_proyecto,
                                eliminar_proyecto, get_categorias_proyectos)
from admin.importar_imagenes import listar_pendientes, ejecutar_importacion
from admin.config_site import (get_config, set_config_bulk, get_contactos,
                                marcar_leido, get_stats_contacto)
from public.catalogo_pub import (get_catalogo_publico, get_producto_publico,
                                  get_categorias_publico, registrar_contacto,
                                  get_hero_productos, get_proyectos_publico, registrar_cotizacion,
                                  get_cotizaciones, get_stats_cotizaciones,
                                  marcar_cotizacion_leida, get_cotizacion_by_id,
                                  registrar_pedido, get_pedidos, get_pedido_by_id,
                                  actualizar_estado_pedido, set_link_pago,
                                  get_stats_pedidos)
from notificaciones import (enviar_notificacion_contacto, enviar_notificacion_cotizacion,
                             enviar_notificacion_pedido, enviar_link_pago)
from pdf_cotizacion import generar_pdf_cotizacion

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()
os.makedirs(UPLOAD_PRODUCTOS, exist_ok=True)
os.makedirs(UPLOAD_PROYECTOS, exist_ok=True)

app = FastAPI(title="MUNDOTEC Web", version="1.0")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY,
                   session_cookie="mw_session", max_age=28800,
                   https_only=False, same_site="lax")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

ADMIN_USER = "admin"
ADMIN_PASS = "Mundotec2026!"   # cambiar en producción

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _require_admin(request: Request):
    if not request.session.get("admin"):
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})

def _save_upload(file: UploadFile, dest_dir: str, prefix: str) -> str:
    ext  = os.path.splitext(file.filename)[1].lower()
    name = f"{prefix}_{uuid.uuid4().hex[:8]}{ext}"
    with open(os.path.join(dest_dir, name), "wb") as f:
        f.write(file.file.read())
    return name

# ─────────────────────────────────────────────────────────────────────────────
# PÚBLICO — Sitio web
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    cfg        = get_config()
    hero       = get_hero_productos()
    destacados = get_catalogo_publico(destacado=True)[:6]
    proyectos  = get_proyectos_publico()[:4]
    return templates.TemplateResponse("public/index.html", {
        "request": request, "cfg": cfg,
        "hero": hero, "destacados": destacados, "proyectos": proyectos,
        "pagina": "home"
    })

@app.get("/catalogo", response_class=HTMLResponse)
async def catalogo_pub(request: Request,
                       categoria: str = Query(""),
                       busqueda:  str = Query("")):
    cfg       = get_config()
    productos = get_catalogo_publico(categoria=categoria, busqueda=busqueda)
    cats      = get_categorias_publico()
    return templates.TemplateResponse("public/catalogo.html", {
        "request": request, "cfg": cfg,
        "productos": productos, "categorias": cats,
        "categoria_sel": categoria, "busqueda": busqueda,
        "pagina": "catalogo"
    })

@app.get("/catalogo/{prod_id}", response_class=HTMLResponse)
async def producto_detalle(request: Request, prod_id: int):
    cfg = get_config()
    p   = get_producto_publico(prod_id)
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return templates.TemplateResponse("public/producto.html", {
        "request": request, "cfg": cfg, "producto": p, "pagina": "catalogo"
    })

@app.get("/proyectos", response_class=HTMLResponse)
async def proyectos_pub(request: Request, categoria: str = Query("")):
    cfg       = get_config()
    proyectos = get_proyectos_publico(categoria=categoria)
    cats      = get_categorias_proyectos()
    return templates.TemplateResponse("public/proyectos.html", {
        "request": request, "cfg": cfg,
        "proyectos": proyectos, "categorias": cats,
        "categoria_sel": categoria, "pagina": "proyectos"
    })

@app.get("/contacto", response_class=HTMLResponse)
async def contacto_get(request: Request, prod_id: int = Query(0)):
    cfg     = get_config()
    producto = get_producto_publico(prod_id) if prod_id else None
    return templates.TemplateResponse("public/contacto.html", {
        "request": request, "cfg": cfg, "pagina": "contacto",
        "enviado": False, "producto": producto
    })

@app.post("/contacto", response_class=HTMLResponse)
async def contacto_post(request: Request,
                        nombre:       str = Form(...),
                        email:        str = Form(""),
                        telefono:     str = Form(""),
                        empresa:      str = Form(""),
                        mensaje:      str = Form(...),
                        producto_ref: str = Form("")):
    cfg = get_config()
    registrar_contacto(nombre, email, telefono, empresa, mensaje, producto_ref)
    # Notificación por correo (no bloquea si falla)
    enviar_notificacion_contacto(nombre, email, telefono, empresa,
                                  mensaje, producto_ref)
    return templates.TemplateResponse("public/contacto.html", {
        "request": request, "cfg": cfg, "pagina": "contacto",
        "enviado": True, "producto": None
    })

# ── API pública (para JS si se necesita) ─────────────────────────────────────
@app.get("/api/catalogo")
async def api_catalogo(categoria: str = Query(""), busqueda: str = Query("")):
    return get_catalogo_publico(categoria=categoria, busqueda=busqueda)

@app.get("/api/catalogo/{prod_id}")
async def api_producto(prod_id: int):
    p = get_producto_publico(prod_id)
    if not p: raise HTTPException(404)
    return p

@app.get("/carrito", response_class=HTMLResponse)
async def carrito(request: Request):
    cfg = get_config()
    iva = int(cfg.get("iva_porcentaje") or 13)
    return templates.TemplateResponse("public/carrito.html", {
        "request": request, "cfg": cfg, "pagina": "carrito", "iva": iva
    })

@app.post("/carrito/cotizar")
async def carrito_cotizar(request: Request):
    data          = await request.json()
    nombre        = data.get("nombre", "")
    email         = data.get("email", "")
    telefono      = data.get("telefono", "")
    empresa       = data.get("empresa", "")
    nota          = data.get("nota", "")
    items         = data.get("items", [])
    total_sin_iva = float(data.get("total_sin_iva", 0))
    total_con_iva = float(data.get("total_con_iva", 0))
    iva_pct       = int(data.get("iva_pct", 13))

    if not nombre or not items:
        raise HTTPException(400, "Datos incompletos")

    cot = registrar_cotizacion(nombre, email, telefono, empresa, nota,
                                items, total_sin_iva, total_con_iva, iva_pct)
    cot_id  = cot["id"] if cot else 0
    num_cot = f"COT-{cot_id:05d}"

    # Generar PDF y enviar con adjunto
    try:
        cot_full = get_cotizacion_by_id(cot_id) if cot_id else {}
        cfg      = get_config()
        pdf      = generar_pdf_cotizacion(cot_full, cfg)
    except Exception:
        pdf = None

    enviar_notificacion_cotizacion(nombre, email, telefono, empresa, nota,
                                    items, total_sin_iva, total_con_iva, iva_pct,
                                    pdf_bytes=pdf, num_cot=num_cot)
    return {"ok": True, "id": cot_id, "num_cot": num_cot}


@app.post("/carrito/pedido")
async def carrito_pedido(request: Request):
    data          = await request.json()
    tipo_factura  = data.get("tipo_factura", "ticket")
    nombre        = data.get("nombre", "")
    email         = data.get("email", "")
    telefono      = data.get("telefono", "")
    cedula        = data.get("cedula", "")
    direccion     = data.get("direccion", "")
    cod_actividad = data.get("cod_actividad", "")
    nota_cliente  = data.get("nota_cliente", "")
    items         = data.get("items", [])
    total_sin_iva = float(data.get("total_sin_iva", 0))
    total_con_iva = float(data.get("total_con_iva", 0))
    iva_pct       = int(data.get("iva_pct", 13))

    if not nombre or not items:
        raise HTTPException(400, "Datos incompletos")

    ped = registrar_pedido(tipo_factura, nombre, email, telefono, cedula,
                           direccion, cod_actividad, nota_cliente,
                           items, total_sin_iva, total_con_iva, iva_pct)

    num_pedido = ped.get("num_pedido", "") if ped else ""
    pedido_id  = ped.get("id", 0) if ped else 0

    try:
        ped_full = get_pedido_by_id(pedido_id) if pedido_id else {}
        enviar_notificacion_pedido(ped_full)
    except Exception:
        pass

    return {"ok": True, "id": pedido_id, "num_pedido": num_pedido}


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Login
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_get(request: Request):
    if request.session.get("admin"):
        return RedirectResponse("/admin", 302)
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})

@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login_post(request: Request,
                            usuario: str = Form(...),
                            clave:   str = Form(...)):
    if usuario == ADMIN_USER and clave == ADMIN_PASS:
        request.session["admin"] = True
        return RedirectResponse("/admin", 302)
    return templates.TemplateResponse("admin/login.html",
                                      {"request": request, "error": "Credenciales incorrectas"})

@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", 302)

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Dashboard
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request):
    _require_admin(request)
    stats_cat = dbq("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE activo) AS activos FROM catalogo_productos")[0]
    stats_pry = dbq("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE activo) AS activos FROM proyectos")[0]
    stats_cnt = get_stats_contacto()
    stats_cot = get_stats_cotizaciones()
    stats_ped = get_stats_pedidos()
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats_cat": stats_cat, "stats_pry": stats_pry, "stats_cnt": stats_cnt,
        "stats_cot": stats_cot, "stats_ped": stats_ped
    })

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Catálogo de productos
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin/catalogo", response_class=HTMLResponse)
async def admin_catalogo(request: Request, busqueda: str = Query(""), categoria: str = Query("")):
    _require_admin(request)
    productos = get_catalogo(busqueda=busqueda, categoria=categoria)
    cats      = get_categorias()
    return templates.TemplateResponse("admin/catalogo.html", {
        "request": request, "productos": productos,
        "categorias": cats, "busqueda": busqueda, "categoria_sel": categoria
    })

@app.get("/admin/catalogo/importar-syma", response_class=HTMLResponse)
async def admin_importar_syma_get(request: Request,
                                   busqueda: str = Query("")):
    _require_admin(request)
    # Siempre carga productos con ID_PASILLO='02', filtro adicional por búsqueda
    resultados = buscar_en_syma(busqueda)
    return templates.TemplateResponse("admin/importar_syma.html", {
        "request": request, "resultados": resultados, "busqueda": busqueda,
        "categorias": get_categorias()
    })

@app.post("/admin/catalogo/importar-syma")
async def admin_importar_syma_post(request: Request):
    _require_admin(request)
    data = await request.json()
    prods = data.get("productos", [])
    importados = 0
    for p in prods:
        try:
            crear_producto(p["codigo"], p["nombre"],
                           p.get("descripcion_syma",""), "",
                           p.get("categoria",""), p.get("precio_ref"))
            importados += 1
        except Exception:
            pass   # ya existe
    return {"importados": importados}

@app.get("/admin/catalogo/{prod_id}", response_class=HTMLResponse)
async def admin_producto_edit(request: Request, prod_id: int):
    _require_admin(request)
    p = get_producto(prod_id)
    if not p: raise HTTPException(404)
    return templates.TemplateResponse("admin/producto_edit.html", {
        "request": request, "p": p, "categorias": get_categorias()
    })

@app.post("/admin/catalogo/{prod_id}")
async def admin_producto_save(request: Request, prod_id: int):
    _require_admin(request)
    data = await request.json()
    actualizar_producto(prod_id, data)
    return {"ok": True}

@app.delete("/admin/catalogo/{prod_id}")
async def admin_producto_del(request: Request, prod_id: int):
    _require_admin(request)
    eliminar_producto(prod_id)
    return {"ok": True}

# ── Imágenes ──────────────────────────────────────────────────────────────────
@app.post("/admin/catalogo/{prod_id}/imagen")
async def admin_subir_imagen(request: Request, prod_id: int,
                              foto: UploadFile = File(...),
                              principal: bool = Form(False)):
    _require_admin(request)
    nombre   = _save_upload(foto, UPLOAD_PRODUCTOS, f"p{prod_id}")
    url_path = f"/static/uploads/productos/{nombre}"
    img      = agregar_imagen(prod_id, url_path, principal)
    return img

@app.delete("/admin/imagen/{img_id}")
async def admin_eliminar_imagen(request: Request, img_id: int):
    _require_admin(request)
    eliminar_imagen(img_id)
    return {"ok": True}

@app.patch("/admin/imagen/{img_id}/principal")
async def admin_set_principal(request: Request, img_id: int):
    _require_admin(request)
    data = await request.json()
    set_imagen_principal(img_id, data["prod_id"])
    return {"ok": True}

# ── Ficha técnica (PDF) ───────────────────────────────────────────────────────
@app.post("/admin/catalogo/{prod_id}/ficha")
async def admin_subir_ficha(request: Request, prod_id: int,
                             ficha: UploadFile = File(...)):
    _require_admin(request)
    nombre = _save_upload(ficha, UPLOAD_PRODUCTOS, f"ficha_{prod_id}")
    path   = f"/static/uploads/productos/{nombre}"
    actualizar_ficha(prod_id, path)
    return {"ficha_path": path}

# ── Specs técnicas ────────────────────────────────────────────────────────────
@app.post("/admin/catalogo/{prod_id}/specs")
async def admin_guardar_specs(request: Request, prod_id: int):
    _require_admin(request)
    data = await request.json()
    reemplazar_specs(prod_id, data.get("specs", []))
    return {"ok": True}

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Proyectos
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin/proyectos", response_class=HTMLResponse)
async def admin_proyectos(request: Request):
    _require_admin(request)
    proyectos = get_proyectos()
    return templates.TemplateResponse("admin/proyectos.html",
                                      {"request": request, "proyectos": proyectos})

@app.post("/admin/proyectos/crear")
async def admin_crear_proyecto(request: Request):
    _require_admin(request)
    data = await request.json()
    p = crear_proyecto(data["titulo"], data.get("descripcion",""),
                       data.get("categoria",""), data.get("fecha"))
    return p

@app.post("/admin/proyectos/{proj_id}/guardar")
async def admin_guardar_proyecto(request: Request, proj_id: int):
    _require_admin(request)
    data = await request.json()
    actualizar_proyecto(proj_id, data)
    return {"ok": True}

@app.post("/admin/proyectos/{proj_id}/imagen")
async def admin_imagen_proyecto(request: Request, proj_id: int,
                                 imagen: UploadFile = File(...)):
    _require_admin(request)
    nombre = _save_upload(imagen, UPLOAD_PROYECTOS, f"pry{proj_id}")
    path   = f"/static/uploads/proyectos/{nombre}"
    actualizar_imagen_proyecto(proj_id, path)
    return {"imagen_path": path}

@app.delete("/admin/proyectos/{proj_id}")
async def admin_eliminar_proyecto(request: Request, proj_id: int):
    _require_admin(request)
    eliminar_proyecto(proj_id)
    return {"ok": True}

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Contacto
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin/contacto", response_class=HTMLResponse)
async def admin_contacto(request: Request, leido: str = Query("")):
    _require_admin(request)
    filtro   = True if leido == "si" else (False if leido == "no" else None)
    mensajes = get_contactos(filtro)
    stats    = get_stats_contacto()
    return templates.TemplateResponse("admin/contacto.html",
                                      {"request": request, "mensajes": mensajes,
                                       "stats": stats, "filtro": leido})

@app.post("/admin/contacto/{cid}/leido")
async def admin_marcar_leido(request: Request, cid: int):
    _require_admin(request)
    marcar_leido(cid)
    return {"ok": True}

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Cotizaciones
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin/cotizaciones", response_class=HTMLResponse)
async def admin_cotizaciones(request: Request, leido: str = Query("")):
    _require_admin(request)
    filtro    = True if leido == "si" else (False if leido == "no" else None)
    cots      = get_cotizaciones(filtro)
    stats     = get_stats_cotizaciones()
    return templates.TemplateResponse("admin/cotizaciones.html", {
        "request": request, "cotizaciones": cots,
        "stats": stats, "filtro": leido
    })

@app.post("/admin/cotizaciones/{cid}/leido")
async def admin_marcar_cotizacion_leida(request: Request, cid: int):
    _require_admin(request)
    marcar_cotizacion_leida(cid)
    return {"ok": True}

@app.get("/admin/cotizaciones/{cid}/pdf")
async def admin_descargar_pdf(request: Request, cid: int):
    _require_admin(request)
    cot = get_cotizacion_by_id(cid)
    if not cot:
        raise HTTPException(404, "Cotización no encontrada")
    cfg      = get_config()
    num_cot  = f"COT-{cid:05d}"
    cot["id"] = cid
    pdf      = generar_pdf_cotizacion(cot, cfg)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=Cotizacion-{num_cot}.pdf"}
    )

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Pedidos (Proceso)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin/pedidos", response_class=HTMLResponse)
async def admin_pedidos(request: Request, estado: str = Query("")):
    _require_admin(request)
    filtro  = estado if estado else None
    pedidos = get_pedidos(filtro)
    stats   = get_stats_pedidos()
    return templates.TemplateResponse("admin/pedidos.html", {
        "request": request, "pedidos": pedidos,
        "stats": stats, "filtro": estado
    })

@app.get("/admin/pedidos/{pid}", response_class=HTMLResponse)
async def admin_pedido_detalle(request: Request, pid: int):
    _require_admin(request)
    ped = get_pedido_by_id(pid)
    if not ped:
        raise HTTPException(404, "Pedido no encontrado")
    return templates.TemplateResponse("admin/pedido_detalle.html", {
        "request": request, "ped": ped
    })

@app.post("/admin/pedidos/{pid}/estado")
async def admin_pedido_estado(request: Request, pid: int):
    _require_admin(request)
    data   = await request.json()
    estado = data.get("estado", "")
    actualizar_estado_pedido(pid, estado)
    return {"ok": True}

@app.post("/admin/pedidos/{pid}/link-pago")
async def admin_pedido_link_pago(request: Request, pid: int):
    _require_admin(request)
    data          = await request.json()
    link          = data.get("link_pago", "").strip()
    nota_vendedor = data.get("nota_vendedor", "")
    if not link:
        raise HTTPException(400, "Link de pago requerido")
    set_link_pago(pid, link, nota_vendedor)
    ped = get_pedido_by_id(pid)
    try:
        enviar_link_pago(ped, link, nota_vendedor)
    except Exception:
        pass
    return {"ok": True}

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Importar imágenes
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin/importar-imagenes", response_class=HTMLResponse)
async def admin_importar_imagenes_get(request: Request):
    _require_admin(request)
    pendientes = listar_pendientes()
    return templates.TemplateResponse("admin/importar_imagenes.html", {
        "request": request, "pendientes": pendientes
    })

@app.post("/admin/importar-imagenes/ejecutar")
async def admin_importar_imagenes_post(request: Request):
    _require_admin(request)
    data   = await request.json()
    forzar = data.get("forzar", False)
    result = ejecutar_importacion(forzar=forzar)
    return JSONResponse(result)

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — Configuración del sitio
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/admin/configuracion", response_class=HTMLResponse)
async def admin_config_get(request: Request):
    _require_admin(request)
    cfg = get_config()
    return templates.TemplateResponse("admin/configuracion.html",
                                      {"request": request, "cfg": cfg, "guardado": False})

@app.post("/admin/configuracion", response_class=HTMLResponse)
async def admin_config_post(request: Request):
    _require_admin(request)
    form = await request.form()
    set_config_bulk(dict(form))
    cfg = get_config()
    return templates.TemplateResponse("admin/configuracion.html",
                                      {"request": request, "cfg": cfg, "guardado": True})

# ─────────────────────────────────────────────────────────────────────────────
# ARRANQUE
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=APP_HOST, port=APP_PORT, reload=True)
