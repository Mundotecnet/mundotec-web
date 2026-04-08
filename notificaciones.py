"""
Módulo de notificaciones por correo electrónico.
Lee la configuración SMTP desde la tabla site_config (admin → Configuración).
Fallback a variables de entorno / config.py si no están en BD.
"""
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _get_smtp_cfg() -> dict:
    """Lee la configuración SMTP desde site_config en la BD."""
    try:
        from db import query
        # Seleccionar todas las claves y filtrar en Python para evitar
        # conflicto del % en LIKE con el driver psycopg2
        rows = query("SELECT clave, valor FROM site_config")
        return {r["clave"]: r["valor"] for r in rows
                if r["clave"].startswith("smtp_") or r["clave"] == "notif_to"}
    except Exception:
        import traceback; traceback.print_exc()
        return {}


def enviar_notificacion_contacto(nombre: str, email: str, telefono: str,
                                  empresa: str, mensaje: str,
                                  producto_ref: str = "") -> bool:
    """
    Envía un email de notificación cuando alguien llena el formulario de contacto.
    Retorna True si se envió, False si no está configurado o hubo error.
    """
    cfg = _get_smtp_cfg()

    smtp_host     = cfg.get("smtp_host", "").strip()
    smtp_port     = int(cfg.get("smtp_port") or 587)
    smtp_user     = cfg.get("smtp_user", "").strip()
    smtp_password = cfg.get("smtp_password", "").strip()
    smtp_from     = cfg.get("smtp_from", "").strip() or smtp_user
    notif_to      = cfg.get("notif_to", "").strip()

    if not (smtp_host and smtp_user and smtp_password and notif_to):
        # SMTP no configurado — los mensajes igual quedan en la BD
        return False

    try:
        asunto = f"📬 Nuevo contacto web: {nombre}"

        empresa_row  = (f"<tr><td style='padding:8px 0;color:#666;width:130px'><strong>Empresa:</strong></td>"
                        f"<td style='padding:8px 0'>{empresa}</td></tr>") if empresa else ""
        tel_row      = (f"<tr><td style='padding:8px 0;color:#666'><strong>Teléfono:</strong></td>"
                        f"<td style='padding:8px 0'><a href='tel:{telefono}'>{telefono}</a></td></tr>") if telefono else ""
        email_row    = (f"<tr><td style='padding:8px 0;color:#666'><strong>Email:</strong></td>"
                        f"<td style='padding:8px 0'><a href='mailto:{email}'>{email}</a></td></tr>") if email else ""
        producto_row = (f"<tr><td style='padding:8px 0;color:#666'><strong>Producto:</strong></td>"
                        f"<td style='padding:8px 0;color:#1E4E8C;font-weight:600'>🏷 {producto_ref}</td></tr>") if producto_ref else ""

        cuerpo_html = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto">
          <div style="background:#1E4E8C;padding:20px;border-radius:8px 8px 0 0">
            <h2 style="color:#fff;margin:0">{"🏷 Consulta sobre producto" if producto_ref else "📬 Nuevo mensaje de contacto"}</h2>
            {"<p style='color:rgba(255,255,255,.8);margin-top:4px;font-size:.9rem'>" + producto_ref + "</p>" if producto_ref else ""}
          </div>
          <div style="border:1px solid #ddd;border-top:none;padding:24px;border-radius:0 0 8px 8px">
            <table style="width:100%;border-collapse:collapse">
              <tr><td style="padding:8px 0;color:#666;width:130px"><strong>Nombre:</strong></td>
                  <td style="padding:8px 0"><strong>{nombre}</strong></td></tr>
              {empresa_row}
              {tel_row}
              {email_row}
              {producto_row}
            </table>
            <hr style="margin:16px 0;border:none;border-top:1px solid #eee">
            <p style="color:#666;margin-bottom:8px"><strong>Mensaje:</strong></p>
            <div style="background:#f8fafc;border-left:4px solid #1E4E8C;padding:16px;border-radius:4px;line-height:1.7;white-space:pre-wrap">{mensaje}</div>
            <hr style="margin:16px 0;border:none;border-top:1px solid #eee">
            <p style="font-size:.78rem;color:#999;text-align:center">
              Mensaje recibido desde el formulario de contacto del sitio web MUNDOTEC.<br>
              <a href="http://192.168.88.250:8001/admin/contacto" style="color:#1E4E8C">Ver panel de contacto →</a>
            </p>
          </div>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = smtp_from
        msg["To"]      = notif_to
        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, [notif_to], msg.as_string())
        server.quit()
        print(f"[MAIL] Notificación enviada a {notif_to} — contacto de: {nombre}")
        return True

    except Exception:
        print(f"[MAIL] Error al enviar notificación (el mensaje igual quedó guardado en BD):")
        traceback.print_exc()
        return False


def enviar_notificacion_cotizacion(nombre: str, email: str, telefono: str,
                                    empresa: str, nota: str,
                                    items: list, total_sin_iva: float,
                                    total_con_iva: float, iva_pct: int = 13) -> bool:
    cfg = _get_smtp_cfg()
    smtp_host     = cfg.get("smtp_host", "").strip()
    smtp_port     = int(cfg.get("smtp_port") or 587)
    smtp_user     = cfg.get("smtp_user", "").strip()
    smtp_password = cfg.get("smtp_password", "").strip()
    smtp_from     = cfg.get("smtp_from", "").strip() or smtp_user
    notif_to      = cfg.get("notif_to", "").strip()

    if not (smtp_host and smtp_user and smtp_password and notif_to):
        return False

    try:
        def fmt(n):
            try: return f"₡{float(n):,.0f}"
            except: return "—"

        filas_items = ""
        for it in items:
            p_iva = float(it.get("precio_ref") or 0) * (1 + iva_pct / 100)
            sub   = p_iva * int(it.get("cantidad", 1))
            filas_items += (
                f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>{it.get('codigo','')}</td>"
                f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{it.get('nombre','')}</td>"
                f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:center'>{it.get('cantidad',1)}</td>"
                f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{fmt(p_iva)}</td>"
                f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right;font-weight:600'>{fmt(sub)}</td></tr>"
            )

        nota_html = f"<p style='color:#666;margin-bottom:8px'><strong>Nota:</strong></p><div style='background:#f8fafc;border-left:4px solid #1E4E8C;padding:12px;border-radius:4px'>{nota}</div>" if nota else ""

        cuerpo_html = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;max-width:650px;margin:0 auto">
          <div style="background:#1E4E8C;padding:20px;border-radius:8px 8px 0 0">
            <h2 style="color:#fff;margin:0">🛒 Nueva solicitud de cotización</h2>
          </div>
          <div style="border:1px solid #ddd;border-top:none;padding:24px;border-radius:0 0 8px 8px">
            <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
              <tr><td style="padding:6px 0;color:#666;width:130px"><strong>Nombre:</strong></td><td style="padding:6px 0"><strong>{nombre}</strong></td></tr>
              {'<tr><td style="padding:6px 0;color:#666"><strong>Empresa:</strong></td><td style="padding:6px 0">' + empresa + '</td></tr>' if empresa else ''}
              {'<tr><td style="padding:6px 0;color:#666"><strong>Teléfono:</strong></td><td style="padding:6px 0"><a href="tel:' + telefono + '">' + telefono + '</a></td></tr>' if telefono else ''}
              {'<tr><td style="padding:6px 0;color:#666"><strong>Email:</strong></td><td style="padding:6px 0"><a href="mailto:' + email + '">' + email + '</a></td></tr>' if email else ''}
            </table>
            <hr style="margin:16px 0;border:none;border-top:1px solid #eee">
            <p style="font-weight:700;margin-bottom:12px">📦 Productos solicitados ({len(items)}):</p>
            <table style="width:100%;border-collapse:collapse;font-size:.85rem">
              <thead><tr style="background:#f3f4f6">
                <th style="padding:8px 10px;text-align:left">Código</th>
                <th style="padding:8px 10px;text-align:left">Producto</th>
                <th style="padding:8px 10px;text-align:center">Cant.</th>
                <th style="padding:8px 10px;text-align:right">P. Unit. c/IVA</th>
                <th style="padding:8px 10px;text-align:right">Subtotal</th>
              </tr></thead>
              <tbody>{filas_items}</tbody>
            </table>
            <div style="text-align:right;margin-top:12px;padding:12px;background:#f8fafc;border-radius:8px">
              <div style="font-size:.85rem;color:#666">Sin IVA: {fmt(total_sin_iva)}</div>
              <div style="font-size:.85rem;color:#666">IVA ({iva_pct}%): {fmt(total_con_iva - total_sin_iva)}</div>
              <div style="font-size:1.1rem;font-weight:800;color:#1E4E8C;margin-top:6px">TOTAL: {fmt(total_con_iva)}</div>
            </div>
            {nota_html}
            <hr style="margin:16px 0;border:none;border-top:1px solid #eee">
            <p style="font-size:.78rem;color:#999;text-align:center">
              <a href="http://192.168.88.250:8001/admin/cotizaciones" style="color:#1E4E8C">Ver todas las cotizaciones →</a>
            </p>
          </div>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🛒 Cotización de {nombre} ({len(items)} producto{'s' if len(items)!=1 else ''})"
        msg["From"]    = smtp_from
        msg["To"]      = notif_to
        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.ehlo(); server.starttls(); server.ehlo()

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, [notif_to], msg.as_string())
        server.quit()
        print(f"[MAIL] Cotización enviada a {notif_to} — cliente: {nombre}, items: {len(items)}")
        return True

    except Exception:
        print(f"[MAIL] Error al enviar cotización:")
        traceback.print_exc()
        return False
