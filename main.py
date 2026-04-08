import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request, Query, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
from admin.config_site import (get_config, set_config_bulk, get_contactos,
                                marcar_leido, get_stats_contacto)
from public.catalogo_pub import (get_catalogo_publico, get_producto_publico,
                                  get_categorias_publico, registrar_contacto,
                                  get_proyectos_publico)

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
    cfg      = get_config()
    destacados = get_catalogo_publico(destacado=True)[:6]
    proyectos  = get_proyectos_publico()[:4]
    return templates.TemplateResponse("public/index.html", {
        "request": request, "cfg": cfg,
        "destacados": destacados, "proyectos": proyectos,
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
async def contacto_get(request: Request):
    cfg = get_config()
    return templates.TemplateResponse("public/contacto.html", {
        "request": request, "cfg": cfg, "pagina": "contacto", "enviado": False
    })

@app.post("/contacto", response_class=HTMLResponse)
async def contacto_post(request: Request,
                        nombre:   str = Form(...),
                        email:    str = Form(""),
                        telefono: str = Form(""),
                        empresa:  str = Form(""),
                        mensaje:  str = Form(...)):
    cfg = get_config()
    registrar_contacto(nombre, email, telefono, empresa, mensaje)
    return templates.TemplateResponse("public/contacto.html", {
        "request": request, "cfg": cfg, "pagina": "contacto", "enviado": True
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
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats_cat": stats_cat, "stats_pry": stats_pry, "stats_cnt": stats_cnt
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
                                   busqueda: str = Query(""),
                                   categoria: str = Query("")):
    _require_admin(request)
    resultados = buscar_en_syma(busqueda, categoria) if (busqueda or categoria) else []
    return templates.TemplateResponse("admin/importar_syma.html", {
        "request": request, "resultados": resultados,
        "busqueda": busqueda, "categoria": categoria
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
    return templates.TemplateResponse("admin/producto_edit.html", {"request": request, "p": p})

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
