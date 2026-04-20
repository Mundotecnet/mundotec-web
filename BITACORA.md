# BITÁCORA TÉCNICA — Sitio Web MUNDOTEC
**Proyecto:** Sitio web público + panel de administración
**Stack:** FastAPI + PostgreSQL + Jinja2
**Servidor:** `mserver` — Ubuntu 22.04 — IP `192.168.88.250`
**Ruta del proyecto:** `/home/lroot/mundotec-web`
**Entorno de trabajo:** Claude Code corre directamente en el servidor
**Última actualización:** 2026-04-20

---

## FRASES CLAVE DE SESIÓN

| Frase | Acción |
|-------|--------|
| `"iniciamos sesión en mundotec"` | Leer esta bitácora → contexto cargado |
| `"iniciamos sesión en reportes"` | Leer `/home/lroot/reportes-syma/BITACORA_TECNICA.md` |
| `"cierra la sesión"` | Actualizar bitácora + commit |
| `"hacer respaldo"` / `"realiza respaldo"` | Ejecutar `bash /home/lroot/scripts/backup_mundotec.sh` |

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
    ├── admin/
    │   ├── catalogo.py       CRUD catálogo + importación SYMA
    │   ├── generar_desc.py   Generador IA descripciones (Claude + local)
    │   └── importar_imagenes.py  Importación desde carpeta auto-import
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
| `cotizaciones` | Cotizaciones generadas desde el carrito (items JSON) |
| `pedidos` | Pedidos con estados y link de pago |
| `ofertas` | Ofertas por tiempo con precio especial, badge y fechas |
| `descuentos_volumen` | Escalones de descuento por cantidad por producto |

---

## PROTOCOLO DE DEPLOY

> Claude Code corre **directamente en el servidor** (`mserver` / `192.168.88.250`).
> No hay sincronización Mac↔servidor. Se edita y commitea en el servidor mismo.

```bash
# 1. Editar archivos en /home/lroot/mundotec-web/
# 2. Commit
git add <archivos>
git commit -m "tipo: descripción breve"

# 3. Reiniciar servicio (si es necesario)
sudo systemctl restart mundotec-web.service
sudo systemctl is-active mundotec-web.service
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

## SISTEMA DE RESPALDO

### Esquema de capas

```
/home/lroot/mundotec-web/          ← Repo de trabajo
        │
        ├── git push backup main
        │         └── /home/lroot/backups/mundotec-web.git     ← Bare repo (historial permanente)
        │
        └── git bundle create
                  ├── /home/lroot/backups/mundotec_git_FECHA.bundle     ← Snapshot diario (14 días)
                  └── /mnt/backup-ext/MUNDOTEC/backups-servidor/        ← Disco externo (si conectado)
```

### Archivos generados
| Archivo | Contenido | Retención |
|---------|-----------|-----------|
| `mundotec-web.git/` | Bare repo — historial git completo | Permanente |
| `mundotec_git_FECHA.bundle` | Snapshot portátil del historial | 14 días |
| `mundotec_db_FECHA.sql.gz` | Base de datos PostgreSQL completa | 14 días |
| `mundotec_uploads_FECHA.tar.gz` | Imágenes (`static/uploads/`) | 14 días |
| `sqlserver/Syma_FECHA.bak.gz` | BD SQL Server 2019 Syma | 14 días |
| `sqlserver/MundoTecAdminDb_*.bak.gz` | BD SQL Server 2012 | Permanente |

### Scripts
| Script | Función | Cron |
|--------|---------|------|
| `backup_mundotec.sh` | Git + PostgreSQL + Imágenes + SQL Server | 02:00 AM diario |
| `backup_reportes.sh` | Git + Static + SQL Server (si no corrió) | 02:30 AM diario |
| `backup_sqlserver.py` | `BACKUP DATABASE [Syma]` vía pyodbc + gzip | Llamado por los anteriores |

### Disco externo
| Campo | Valor |
|-------|-------|
| Punto de montaje | `/mnt/backup-ext` |
| Carpeta | `/mnt/backup-ext/MUNDOTEC/backups-servidor/` |
| UUID | `1CFE7C05FE7BD60C` (NTFS, 932 GB) |
| fstab | `nofail` — servidor arranca aunque no esté conectado |

> Si el disco externo está montado, los scripts copian automáticamente. Si no, solo guardan local y registran aviso en el log.

### Logs
| Log | Ruta |
|-----|------|
| mundotec-web | `/home/lroot/backups/backup.log` |
| reportes-syma | `/home/lroot/backups/backup_reportes.log` |

---

## PROTOCOLO DE RESPALDO

### Respaldo manual (desde Claude Code)
```bash
bash /home/lroot/scripts/backup_mundotec.sh
```

### Verificar último respaldo
```bash
tail -20 /home/lroot/backups/backup.log
```

### Verificar contenido del disco externo
```bash
ls -lh /mnt/backup-ext/MUNDOTEC/backups-servidor/
```

### Restaurar base de datos
```bash
gunzip -c /home/lroot/backups/mundotec_db_FECHA.sql.gz | \
  PGPASSWORD=Mw@Web2026! psql -h localhost -U mw_user mundotec_web
```

### Restaurar código
```bash
# Desde bare repo (historial completo)
git clone /home/lroot/backups/mundotec-web.git mundotec-web-restaurado

# Desde bundle diario (snapshot portátil)
git clone /home/lroot/backups/mundotec_git_FECHA.bundle mundotec-web-restaurado
```

### Ver historial completo del bare repo
```bash
git --git-dir=/home/lroot/backups/mundotec-web.git log --oneline
```

### Restaurar imágenes
```bash
tar -xzf /home/lroot/backups/mundotec_uploads_FECHA.tar.gz -C /home/lroot/mundotec-web/static/
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

1. **Importar de SYMA**: Requiere pyodbc + ODBC Driver 17 en el venv. Si falla devuelve `[{"error": "..."}]`.
2. **Imágenes**: Se guardan en `static/uploads/`. No están en git (`.gitignore`). Hacer backup manual.
3. **Config del sitio**: Tabla `site_config` en PostgreSQL. Editable desde `/admin/configuracion`.
4. **Colores CSS**: Variables en `templates/public/base.html`. Requieren recarga del navegador.
5. **Admin password**: Hardcodeada en `main.py → ADMIN_PASS`. Cambiar antes de producción.
6. **Anthropic API Key**: Guardada en `/etc/systemd/system/mundotec-web.service.d/env.conf`. No en código.
7. **Ofertas únicas**: `UNIQUE INDEX` impide 2 ofertas activas para el mismo producto simultáneamente.
8. **Carrito y volumen**: El descuento por volumen se aplica en tiempo real vía `/api/precio-volumen/{id}/{qty}`. El precio guardado en localStorage es el precio base; el descuento se recalcula al abrir el carrito.
9. **Samba share**: Imágenes auto-import en `\\192.168.88.250\imagenes-mundotec` (usuario: `lroot`, pass: `Mundotec2026`).
10. **Specs al aprobar IA**: Se parsea "Etiqueta: Valor" → si no hay ":", etiqueta = "Especificación".

---

## BACKUPS

| Fecha | Tipo | Descripción |
|-------|------|-------------|
| 2026-04-08 | Git inicial | v1.0.0 — Primera versión funcional |
| 2026-04-11 | Git | Sesiones 4 y 5 — PDF, pedidos, correcciones cotizaciones |
| 2026-04-12 | Git | Sesiones 6 y 7 — Catálogo inline, imágenes, IA descripciones, ofertas, volumen |
| 2026-04-12 | Backup | Primer respaldo automático — BD + código + imágenes + historial git (104 MB) |
| 2026-04-12 | Git | Sesión 8 — Sistema de respaldo automático completo documentado |
| 2026-04-13 | Git | Sesión 9 — Respaldo SQL Server, disco externo, PDFs de referencia |
| 2026-04-13 | Git | Sesión 10 — Módulo actualizar precios desde SYMA; sincronización Mac↔servidor |

---

## BITÁCORA DE CAMBIOS

### [SESIÓN 11] — 2026-04-20 — Fix catálogo público

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Fix | `templates/public/catalogo.html` — variable `extra` concatenaba `Undefined` en Jinja2 cuando ningún filtro de precio estaba activo (`if x` sin `else ''`), causando Internal Server Error en `/catalogo` |

---

### [SESIÓN 10] — 2026-04-13 — Módulo actualizar precios + sincronización git

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Nuevo | `admin/actualizar_precios.py` — `comparar_precios()` y `aplicar_precios()` |
| 2 | Nuevo | `GET /admin/precios` — tabla de diferencias web vs SYMA con checkboxes |
| 3 | Nuevo | `POST /admin/precios/aplicar` — aplica solo los precios seleccionados |
| 4 | Nuevo | Sidebar: enlace "💰 Actualizar precios" bajo Utilidades |
| 5 | Fix | Conflicto de sincronización Mac↔servidor resuelto con stash + rebase |
| 6 | Sync | Cambios del servidor (ofertas, descuentos por volumen) traídos al Mac |

---

### [SESIÓN 9] — 2026-04-13 — Respaldo SQL Server + Disco externo + PDFs de referencia

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Nuevo | Share Samba `\\192.168.88.250\sql-backups` → `/home/lroot/backups/sqlserver/` — SQL Server escribe .bak directamente aquí |
| 2 | Nuevo | Script `/home/lroot/scripts/backup_sqlserver.py` — dispara `BACKUP DATABASE` via pyodbc + comprime con gzip |
| 3 | Nuevo | Respaldo `Syma_FECHA.bak.gz` integrado al cron — corre desde `backup_mundotec.sh` con lock de fecha |
| 4 | Nuevo | Respaldo único `MundoTecAdminDb_20260412.bak.gz` (59 MB) — SQL Server 2012 en `192.168.10.15:1433` |
| 5 | Nuevo | Disco externo NTFS 932 GB montado en `/mnt/backup-ext` — UUID `1CFE7C05FE7BD60C` |
| 6 | Nuevo | fstab con `nofail` — servidor arranca sin problemas aunque el disco no esté conectado |
| 7 | Nuevo | Ambos scripts de backup copian automáticamente al disco externo si está montado |
| 8 | Nuevo | PDF `/home/lroot/backups/Resumen_Sistema_Respaldo_MUNDOTEC.pdf` — referencia completa del sistema de respaldo |
| 9 | Nuevo | PDF `/home/lroot/backups/Credenciales_Sistema_MUNDOTEC.pdf` — credenciales + estructura de proyectos |
| 10 | Infra | `pymssql` instalado en venv de reportes-syma — único driver que soporta TLS 1.0 de SQL Server 2012 |
| 11 | Infra | OpenSSL configurado con `MinProtocol=TLSv1` y `SECLEVEL=1` para compatibilidad con SQL Server 2012 |
| 12 | Infra | SQL Server detectado via UDP 1434 (SQL Browser) — dos instancias: `SQLEXPRESS` (2019) y `MSSQLSERVER` (2012) |

**Scripts del sistema de respaldo:**
| Script | Función |
|--------|---------|
| `backup_mundotec.sh` | Git + PostgreSQL + Imágenes + SQL Server → Local + Disco externo (02:00 AM) |
| `backup_reportes.sh` | Git + Static + SQL Server (si no corrió) → Local + Disco externo (02:30 AM) |
| `backup_sqlserver.py` | `BACKUP DATABASE [Syma]` vía Samba + gzip + limpieza 14 días |
| `generar_resumen_respaldo.py` | Genera PDF de referencia del sistema de respaldo |
| `generar_credenciales.py` | Genera PDF de credenciales + estructura de proyectos |

---

### [SESIÓN 8] — 2026-04-12 — Sistema de respaldo automático con historial Git completo

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Nuevo | Script `/home/lroot/scripts/backup_mundotec.sh` — respaldo automático nocturno |
| 2 | Nuevo | Bare repo git local `/home/lroot/backups/mundotec-web.git` — remoto permanente `backup` |
| 3 | Nuevo | Bundle diario `mundotec_git_FECHA.bundle` — snapshot portátil del historial completo |
| 4 | Nuevo | Respaldo BD `mundotec_db_FECHA.sql.gz` — pg_dump comprimido |
| 5 | Nuevo | Respaldo imágenes `mundotec_uploads_FECHA.tar.gz` — carpeta static/uploads |
| 6 | Nuevo | Cron 02:00 AM diario: `0 2 * * * /home/lroot/scripts/backup_mundotec.sh` |
| 7 | Nuevo | Log en `/home/lroot/backups/backup.log` con timestamps y tamaños |
| 8 | Infra | Retención automática de 14 días — `find -mtime +14 -delete` por tipo de archivo |
| 9 | Fix | Historial git inicialmente excluido del respaldo → corregido: se incluye vía bare repo + bundle |
| 10 | Infra | Remoto `backup` configurado automáticamente con `git remote add/set-url` en cada ejecución |

**Descripción del flujo de respaldo:**
1. `git push backup main` → sincroniza historial al bare repo local
2. `git bundle create --all` → genera snapshot portátil del día
3. `pg_dump | gzip` → exporta BD PostgreSQL completa
4. `tar -czf static/uploads` → archiva imágenes y archivos subidos
5. `find -mtime +14 -delete` → limpia respaldos más antiguos de 14 días

**Restauración de emergencia:**
```bash
# Código
git clone /home/lroot/backups/mundotec-web.git mundotec-web-nuevo
# Base de datos
gunzip -c /home/lroot/backups/mundotec_db_FECHA.sql.gz | PGPASSWORD=Mw@Web2026! psql -h localhost -U mw_user mundotec_web
# Imágenes
tar -xzf /home/lroot/backups/mundotec_uploads_FECHA.tar.gz -C /home/lroot/mundotec-web/static/
```

---

### [SESIÓN 7] — 2026-04-12 — Módulo de Ofertas y Descuentos por volumen (Fase 1 y 2)

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Nuevo | Tabla `ofertas` — precio especial por tiempo con badge, etiqueta y fechas |
| 2 | Nuevo | Tabla `descuentos_volumen` — escalones de descuento por cantidad por producto |
| 3 | Nuevo | Admin `/admin/ofertas` — CRUD de ofertas con modal, cálculo automático de % descuento |
| 4 | Nuevo | Admin `/admin/descuentos-volumen` — escalones agrupados por producto, vista previa en tiempo real |
| 5 | Nuevo | Página pública `/ofertas` — grid de ofertas vigentes con countdown en tiempo real |
| 6 | Nuevo | API `/api/precio-volumen/{id}/{cantidad}` — descuento aplicable según cantidad |
| 7 | Mejora | Catálogo público: badge rojo de oferta + precio tachado en tarjetas |
| 8 | Mejora | Ficha producto: bloque de oferta con countdown, tabla de precios por volumen |
| 9 | Mejora | Carrito: aplica descuento de volumen automáticamente al cambiar cantidad |
| 10 | Mejora | Nav pública: enlace "🏷️ Ofertas" en rojo |
| 11 | Mejora | Sidebar admin: enlaces "🏷️ Ofertas" y "📦 Desc. por volumen" |
| 12 | Mejora | JOIN de ofertas en `get_catalogo_publico()` y `get_producto_publico()` — campo `precio_efectivo` |

---

### [SESIÓN 6] — 2026-04-12 — Catálogo admin, IA descripciones, imágenes, correcciones

| # | Tipo | Descripción |
|---|------|-------------|
| 1 | Nuevo | Admin catálogo rediseñado como tabla inline-editable (nombre, categoría select, precio, orden, toggles) |
| 2 | Nuevo | Categoría en catálogo: `<select>` con categorías existentes + opción "✏️ Escribir nueva…" |
| 3 | Nuevo | Utilitario importación imágenes — carpeta auto-import sincronizada con productos por código |
| 4 | Nuevo | Samba share `\\192.168.88.250\imagenes-mundotec` para subir imágenes desde Windows |
| 5 | Nuevo | Módulo IA `/admin/generar-desc` — generación y aprobación de descripciones con Claude |
| 6 | Nuevo | Generador local (sin API key) con detección de tipo, marca, modelo, color, specs |
| 7 | Nuevo | Generador Claude (con API key) — `claude-haiku-4-5` — formato "Etiqueta: Valor" en características |
| 8 | Nuevo | API Key Anthropic configurada en systemd override `/etc/systemd/system/mundotec-web.service.d/env.conf` |
| 9 | Mejora | Selección múltiple con checkboxes en generador IA — barra flotante "Re-generar / Aprobar seleccionados" |
| 10 | Mejora | Endpoint `/aprobar` parsea "Etiqueta: Valor" → guarda etiqueta y valor por separado en `catalogo_specs` |
| 11 | Mejora | Specs de telescopio: detección de apertura y focal desde nombre (ej: 114x500mm) |
| 12 | Mejora | Carrusel homepage con autoplay 3 seg, pausa en hover, flechas circulares |
| 13 | Mejora | `object-fit:contain` + `aspect-ratio:3/2` en catálogo y ficha de producto |
| 14 | Mejora | `overflow:hidden` en wrapper de imagen principal para respetar `border-radius` |
| 15 | Fix | `[:120]` en template Jinja2 → reemplazado por `\|truncate(120,true,'')` |
| 16 | Fix | Botones "Generar" deshabilitados sin API key — corregido para usar generador local |
| 17 | Fix | Etiquetas "Característica 1/2/3" en specs → migradas a etiquetas reales con SQL UPDATE |
| 18 | Fix | Modelo Claude `claude-3-5-haiku-20241022` deprecado → actualizado a `claude-haiku-4-5` |
| 19 | Fix | Regex `\b360\b` para no confundir modelo "L4360" con "Rotación 360 grados" |
| 20 | Infra | `_normalize()` en db.py convierte `date`/`datetime` a ISO string para serialización JSON |
| 21 | Infra | Filtro Jinja2 `fmtdt` para formatear fechas desde strings ISO en templates |

---

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
