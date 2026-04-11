# BITÁCORA TÉCNICA — Sitio Web MUNDOTEC
**Proyecto:** Sitio web público + panel de administración
**Stack:** FastAPI + PostgreSQL + Jinja2
**Servidor:** Ubuntu 192.168.88.250:8001
**Ruta local:** `/Users/lroot/Downloads/mundotec-web`
**Ruta servidor:** `/home/lroot/mundotec-web`
**Última actualización:** 2026-04-11

---

## FRASES CLAVE DE SESIÓN

| Frase | Acción |
|-------|--------|
| `"lee la bitácora"` | `Read BITACORA.md` → contexto cargado |
| `"cierra la sesión"` | Actualizar bitácora + commit + push servidor |
| `"realiza respaldo"` | Backup del directorio y la BD PostgreSQL |

---

## ══ ESTADO ACTUAL ══

### Versión: `v1.0.0` — Intranet

### Acceso
| Servicio | URL | Puerto |
|---------|-----|--------|
| Sitio público | `http://192.168.88.250:8001` | 8001 |
| Panel admin | `http://192.168.88.250:8001/admin` | 8001 |
| App reportes | `http://192.168.88.250:8000` | 8000 |

### Credenciales admin web
- **Usuario:** `admin`
- **Contraseña:** `Mundotec2026!` ← cambiar en producción

### Base de datos
- **Motor:** PostgreSQL 14
- **BD:** `mundotec_web`
- **Usuario PG:** `mw_user`
- **Password PG:** `Mw@Web2026!`
- **Host:** `localhost:5432`

---

## ARQUITECTURA

```
/home/lroot/
├── reportes-syma/      ← App interna (puerto 8000) — SQL Server Syma
└── mundotec-web/       ← Sitio web (puerto 8001) — PostgreSQL
    ├── main.py          FastAPI app
    ├── db.py            Conexión PostgreSQL + DDL
    ├── config.py        Configuración (puertos, credenciales)
    ├── admin/           Módulos de gestión (catálogo, proyectos, config)
    ├── public/          Módulos del sitio público
    ├── templates/
    │   ├── public/      Plantillas sitio web
    │   └── admin/       Plantillas panel admin
    └── static/
        └── uploads/
            ├── productos/  Imágenes de productos
            └── proyectos/  Imágenes de proyectos
```

### Tablas PostgreSQL (`mundotec_web`)
| Tabla | Descripción |
|-------|-------------|
| `site_config` | Configuración del sitio (nombre, slogan, colores, contacto) |
| `catalogo_productos` | Productos seleccionados del inventario SYMA para el catálogo |
| `catalogo_imagenes` | Imágenes por producto (múltiples, una principal) |
| `catalogo_specs` | Especificaciones técnicas por producto (clave-valor) |
| `proyectos` | Proyectos/obras de la empresa (con imagen y descripción) |
| `contacto` | Mensajes recibidos del formulario de contacto |

---

## PROTOCOLO DE DEPLOY

```bash
# 1. Editar archivos localmente
# 2. Commit
git add <archivos>
git commit -m "descripción"

# 3. Push al servidor
GIT_SSH_COMMAND="/usr/local/bin/sshpass -p '87060002' ssh -o StrictHostKeyChecking=no" \
  git push servidor main

# 4. Reiniciar servicio
/usr/local/bin/sshpass -p '87060002' ssh -tt lroot@192.168.88.250 \
  "echo '87060002' | sudo -S systemctl restart mundotec-web.service && \
   sleep 2 && systemctl is-active mundotec-web.service"
```

---

## SERVICIO SYSTEMD

```ini
# /etc/systemd/system/mundotec-web.service
[Unit]
Description=MUNDOTEC Sitio Web
After=network.target postgresql.service

[Service]
User=lroot
WorkingDirectory=/home/lroot/mundotec-web
ExecStart=/home/lroot/mundotec-web/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --reload
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## BACKUP POSTGRESQL

```bash
# Backup manual de la BD
pg_dump -U mw_user -h localhost mundotec_web > backup_web_$(date +%Y%m%d).sql

# Restaurar
psql -U mw_user -h localhost mundotec_web < backup_web_FECHA.sql
```

---

## PARA PRODUCCIÓN (con dominio + HTTPS)

```bash
# 1. Instalar Nginx
sudo apt install nginx

# 2. Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# 3. Config Nginx (ver sección abajo)

# 4. Obtener certificado
sudo certbot --nginx -d tudominio.com

# 5. Cambiar en config.py:
#    https_only=True en SessionMiddleware
#    Contraseña admin por defecto
```

### Config Nginx básica (cuando se tenga dominio)
```nginx
server {
    listen 80;
    server_name tudominio.com;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    server_name tudominio.com;
    # certbot agrega aquí los parámetros SSL
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /static/ {
        alias /home/lroot/mundotec-web/static/;
    }
}
```

---

## GOTCHAS / ADVERTENCIAS

1. **Importar de SYMA**: Requiere que pyodbc y ODBC Driver 17 estén instalados en el venv. Si falla, el endpoint devuelve `[{"error": "..."}]`.
2. **Imágenes**: Se guardan en `static/uploads/`. No están en git (`.gitignore`). Hacer backup manual de esa carpeta.
3. **Config del sitio**: Se guarda en la tabla `site_config` de PostgreSQL. Editable desde `/admin/configuracion`.
4. **Colores**: Se aplican como variables CSS en `templates/public/base.html`. Requieren recarga del navegador tras cambiar.
5. **Admin password**: Está hardcodeada en `main.py` → `ADMIN_PASS`. Cambiar antes de ir a producción.

---

## BACKUPS

| Fecha | Tipo | Descripción |
|-------|------|-------------|
| 2026-04-08 | Git inicial | v1.0.0 — Primera versión funcional |
| 2026-04-11 | Git | Sesiones 4 y 5 — PDF, pedidos, correcciones cotizaciones |

---

## BITÁCORA DE CAMBIOS

### [SESIÓN 5] — 2026-04-11 — Correcciones cotizaciones

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Fix | `c['items']` en `cotizaciones.html` para evitar conflicto con `dict.items()` |
| 2 | Fix | Corrección en loop de `cotizaciones.html` para iterar items correctamente |

---

### [SESIÓN 4] — 2026-04-08 — PDF cotizaciones + módulo Tramitar Compra (pedidos)

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Nuevo | Generación de PDF de cotización y envío por correo desde el carrito |
| 2 | Nuevo | Datos fiscales, cuentas bancarias y logo en PDF cotización |
| 3 | Nuevo | Logo Mundotec HD agregado al proyecto para usar en PDF |
| 4 | Fix | Fuente DejaVuSans para mostrar símbolo ₡ correctamente en PDF |
| 5 | Fix | Columna total PDF ampliada + label IVA corregido (13%) |
| 6 | Nuevo | Tabla `pedidos` en BD con estados: `pendiente → en_proceso → link_enviado → pagado` |
| 7 | Nuevo | CRUD pedidos en `catalogo_pub.py` (registrar, listar, detalle, cambio de estado, link pago) |
| 8 | Nuevo | Notificaciones email para nuevo pedido y envío de link de pago al cliente |
| 9 | Nuevo | Carrito: botón y modal "Tramitar Compra" con formulario dinámico Ticket/Factura |
| 10 | Nuevo | Admin: sección "Proceso" (`/admin/pedidos`) con lista y detalle por pedido |
| 11 | Nuevo | Admin: envío de link de pago directo desde el panel al correo del cliente |
| 12 | Mejora | Sidebar renombrado: Cotizaciones → Oportunidades, nueva entrada Proceso |

---

### [SESIÓN 3] — 2026-04-07 — Carrito de cotización + precios con IVA

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Nuevo | Carrito de cotización en localStorage (`mw_carrito`) — persistente sin login |
| 2 | Nuevo | Página `/carrito` con tabla de items, control de cantidades, desglose IVA y total |
| 3 | Nuevo | Modal "Solicitar cotización" → POST `/carrito/cotizar` → BD + email |
| 4 | Nuevo | Tabla `cotizaciones` en PostgreSQL (items como JSON, totales, IVA %) |
| 5 | Nuevo | Admin `/admin/cotizaciones` — lista expandible con detalle de items |
| 6 | Nuevo | Email de notificación con tabla de productos y totales al recibir cotización |
| 7 | Mejora | Precios con IVA incluido en catálogo y ficha de producto |
| 8 | Mejora | IVA configurable desde `/admin/configuracion` (default 13%) |
| 9 | Mejora | Botón "Agregar al carrito" en tarjetas del catálogo y ficha de producto |
| 10 | Mejora | Ícono 🛒 en nav con contador de items en tiempo real |
| 11 | Mejora | Toast de confirmación al agregar producto al carrito |
| 12 | Mejora | Botón WhatsApp en ficha con texto pre-llenado del producto |
| 13 | Mejora | Link "Consultar por producto" en formulario de contacto |

---

### [SESIÓN 2] — 2026-04-07 — Notificaciones por email + formulario de contacto

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Nuevo | Módulo `notificaciones.py` — envío de email SMTP al recibir formulario de contacto |
| 2 | Mejora | Config SMTP manejada desde panel admin `/admin/configuracion` (sin reiniciar) |
| 3 | Mejora | Soporta Gmail port 587 TLS y SMTP SSL port 465 |
| 4 | Mejora | Fallo en SMTP no bloquea — mensaje siempre queda guardado en BD |
| 5 | Mejora | DDL actualizado: nuevas claves `smtp_host/port/user/password/from`, `notif_to` en `site_config` |

---

### [SESIÓN 1] — 2026-04-08 — Implementación inicial

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Nuevo | Proyecto `mundotec-web` creado con estructura completa |
| 2 | Nuevo | PostgreSQL 14 (ya instalado) — BD `mundotec_web` + usuario `mw_user` |
| 3 | Nuevo | 6 tablas: `site_config`, `catalogo_productos`, `catalogo_imagenes`, `catalogo_specs`, `proyectos`, `contacto` |
| 4 | Nuevo | Sitio web público: Inicio (hero + stats + destacados + proyectos + CTA), Catálogo (grid + filtros), Detalle producto (galería + specs + ficha PDF), Proyectos, Contacto |
| 5 | Nuevo | Panel admin: Dashboard, Catálogo (listar/editar/imágenes/specs/ficha), Importar de SYMA, Proyectos, Contacto, Configuración |
| 6 | Nuevo | Servicio systemd `mundotec-web.service` en puerto 8001 |
| 7 | Infra | Git repo con remoto `servidor` → `/home/lroot/mundotec-web` |

---
*Actualizar esta bitácora al cierre de cada sesión con `"cierra la sesión"`*
