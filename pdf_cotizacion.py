"""
Generador de PDF para cotizaciones.
Requiere: pip install reportlab
"""
import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable)


def generar_pdf_cotizacion(cot: dict, cfg: dict) -> bytes:
    """
    Genera el PDF de una cotización y devuelve los bytes.
    cot : dict con los datos de la cotización (de la tabla cotizaciones)
    cfg : dict con la configuración del sitio (empresa_nombre, colores, etc.)
    """
    buffer = io.BytesIO()

    # ── Config empresa ────────────────────────────────────────────────────────
    empresa   = cfg.get("empresa_nombre",   "MUNDOTEC")
    slogan    = cfg.get("empresa_slogan",   "")
    tel       = cfg.get("empresa_telefono", "")
    email_emp = cfg.get("empresa_email",    "")
    direccion = cfg.get("empresa_direccion","")
    web       = cfg.get("empresa_web",      "")

    try:
        color_hex = cfg.get("color_primario", "#1E4E8C")
        c_primary = colors.HexColor(color_hex)
    except Exception:
        c_primary = colors.HexColor("#1E4E8C")

    c_light   = colors.HexColor("#EFF6FF")
    c_gray    = colors.HexColor("#6B7280")
    c_border  = colors.HexColor("#E5E7EB")
    c_rowalt  = colors.HexColor("#F8FAFC")

    iva_pct   = int(cot.get("iva_pct", 13))
    items     = cot.get("items", [])

    # ── Fecha y número ────────────────────────────────────────────────────────
    fecha = cot.get("creado_en") or datetime.now()
    if hasattr(fecha, "strftime"):
        fecha_str = fecha.strftime("%d/%m/%Y")
    else:
        fecha_str = str(fecha)[:10]

    cot_id  = cot.get("id", 0)
    num_cot = f"COT-{cot_id:05d}"

    # ── Documento ─────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1.8*cm, leftMargin=1.8*cm,
        topMargin=1.8*cm,   bottomMargin=1.8*cm,
        title=f"Cotización {num_cot}",
        author=empresa,
    )

    # ── Estilos ───────────────────────────────────────────────────────────────
    def sty(**kw):
        defaults = dict(fontName="Helvetica", fontSize=9, leading=13,
                        textColor=colors.HexColor("#1a1a2e"))
        defaults.update(kw)
        return ParagraphStyle("_", **defaults)

    S = {
        "normal":   sty(),
        "small":    sty(fontSize=7.5, textColor=c_gray),
        "bold":     sty(fontName="Helvetica-Bold"),
        "title":    sty(fontName="Helvetica-Bold", fontSize=22, textColor=c_primary),
        "cot_num":  sty(fontName="Helvetica-Bold", fontSize=16, textColor=c_primary,
                        alignment=TA_RIGHT),
        "r_small":  sty(fontSize=8.5, alignment=TA_RIGHT, leading=13),
        "section":  sty(fontName="Helvetica-Bold", fontSize=7.5, textColor=c_gray,
                        spaceAfter=4),
        "footer":   sty(fontSize=7, textColor=c_gray, alignment=TA_CENTER),
        "total_lbl":sty(fontName="Helvetica-Bold", fontSize=10, alignment=TA_RIGHT),
        "total_val":sty(fontName="Helvetica-Bold", fontSize=10, alignment=TA_RIGHT),
        "grand_lbl":sty(fontName="Helvetica-Bold", fontSize=13, alignment=TA_RIGHT,
                        textColor=c_primary),
        "grand_val":sty(fontName="Helvetica-Bold", fontSize=13, alignment=TA_RIGHT,
                        textColor=c_primary),
    }

    def p(text, style="normal", **kw):
        return Paragraph(str(text), S[style] if isinstance(style, str) else style)

    def fmt(n):
        try:    return f"\u20a1{float(n):,.0f}"
        except: return "\u2014"

    story = []

    # ═══════════════════════════════════════════════════════════════════════════
    # ENCABEZADO
    # ═══════════════════════════════════════════════════════════════════════════
    contact_lines = []
    if tel:       contact_lines.append(f"Tel: {tel}")
    if email_emp: contact_lines.append(f"{email_emp}")
    if direccion: contact_lines.append(direccion)
    if web:       contact_lines.append(web)

    header = Table([
        [p(empresa, "title"),
         p("COTIZACIÓN", "cot_num")],
        [p(slogan, "small"),
         p(f"<b>N°:</b> {num_cot}<br/><b>Fecha:</b> {fecha_str}", "r_small")],
        [p("<br/>".join(contact_lines), "small"), p("", "small")],
    ], colWidths=[10.5*cm, 7*cm])

    header.setStyle(TableStyle([
        ("VALIGN",         (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 2),
        ("TOPPADDING",     (0,0), (-1,-1), 2),
    ]))
    story.append(header)
    story.append(HRFlowable(width="100%", thickness=2.5, color=c_primary,
                             spaceBefore=8, spaceAfter=14))

    # ═══════════════════════════════════════════════════════════════════════════
    # DATOS DEL CLIENTE
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(p("DATOS DEL CLIENTE", "section"))

    cliente_rows = []
    if cot.get("nombre"):   cliente_rows.append(["Nombre:",   cot["nombre"]])
    if cot.get("empresa"):  cliente_rows.append(["Empresa:",  cot["empresa"]])
    if cot.get("telefono"): cliente_rows.append(["Teléfono:", cot["telefono"]])
    if cot.get("email"):    cliente_rows.append(["Correo:",   cot["email"]])

    if cliente_rows:
        ct = Table(cliente_rows, colWidths=[2.8*cm, 14.7*cm])
        ct.setStyle(TableStyle([
            ("FONTNAME",       (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",       (0,0), (-1,-1), 8.5),
            ("TEXTCOLOR",      (0,0), (0,-1), c_gray),
            ("BOTTOMPADDING",  (0,0), (-1,-1), 3),
            ("TOPPADDING",     (0,0), (-1,-1), 2),
            ("BACKGROUND",     (0,0), (-1,-1), c_light),
            ("BOX",            (0,0), (-1,-1), 0.5, c_border),
            ("LEFTPADDING",    (0,0), (-1,-1), 8),
        ]))
        story.append(ct)

    story.append(Spacer(1, 16))

    # ═══════════════════════════════════════════════════════════════════════════
    # TABLA DE PRODUCTOS
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(p("DETALLE DE PRODUCTOS", "section"))

    th_sty = sty(fontName="Helvetica-Bold", fontSize=7.5,
                  textColor=colors.white, alignment=TA_CENTER)

    hdr = [
        p("Código",          th_sty),
        p("Descripción",     th_sty),
        p("Cant.",           th_sty),
        p("P.Unit s/IVA",    th_sty),
        p(f"IVA ({iva_pct}%)",th_sty),
        p("P.Unit c/IVA",    th_sty),
        p("Subtotal",        th_sty),
    ]
    rows = [hdr]

    for it in items:
        p_ref = float(it.get("precio_ref") or 0)
        p_iva_u = p_ref * (1 + iva_pct / 100)
        iva_u   = p_iva_u - p_ref
        qty     = int(it.get("cantidad", 1))
        sub     = p_iva_u * qty

        row_sty = sty(fontSize=8, leading=11)
        rows.append([
            p(it.get("codigo", ""),  sty(fontSize=7.5, fontName="Helvetica-Bold")),
            p(it.get("nombre",  ""), sty(fontSize=8, leading=11)),
            p(str(qty),              sty(fontSize=8, alignment=TA_CENTER)),
            p(fmt(p_ref),            sty(fontSize=8, alignment=TA_RIGHT)),
            p(fmt(iva_u),            sty(fontSize=8, alignment=TA_RIGHT,
                                         textColor=colors.HexColor("#E67E22"))),
            p(fmt(p_iva_u),          sty(fontSize=8, alignment=TA_RIGHT)),
            p(fmt(sub),              sty(fontSize=8, alignment=TA_RIGHT,
                                         fontName="Helvetica-Bold")),
        ])

    col_w = [2.3*cm, 5.5*cm, 1.2*cm, 2.5*cm, 1.8*cm, 2.5*cm, 2.5*cm]
    items_t = Table(rows, colWidths=col_w, repeatRows=1)
    items_t.setStyle(TableStyle([
        # Header
        ("BACKGROUND",     (0,0), (-1,0), c_primary),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, c_rowalt]),
        ("GRID",           (0,0), (-1,-1), 0.3, c_border),
        ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",     (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 5),
        ("LEFTPADDING",    (0,0), (-1,-1), 5),
        ("RIGHTPADDING",   (0,0), (-1,-1), 5),
    ]))
    story.append(items_t)
    story.append(Spacer(1, 12))

    # ═══════════════════════════════════════════════════════════════════════════
    # TOTALES
    # ═══════════════════════════════════════════════════════════════════════════
    sin_iva = float(cot.get("total_sin_iva") or 0)
    con_iva = float(cot.get("total_con_iva") or 0)
    iva_sum = con_iva - sin_iva

    totals = [
        [p(""), p(f"Subtotal sin IVA:", "total_lbl"), p(fmt(sin_iva), "total_val")],
        [p(""), p(f"IVA ({iva_pct}%):",  "total_lbl"), p(fmt(iva_sum), "total_val")],
        [p(""), p("TOTAL:",              "grand_lbl"), p(fmt(con_iva), "grand_val")],
    ]
    totals_t = Table(totals, colWidths=[10.5*cm, 4.5*cm, 2.5*cm])
    totals_t.setStyle(TableStyle([
        ("ALIGN",        (1,0), (2,-1), "RIGHT"),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ("LINEABOVE",    (1,2), (2,2), 1.5, c_primary),
        ("TOPPADDING",   (0,2), (-1,2), 8),
    ]))
    story.append(totals_t)

    # ═══════════════════════════════════════════════════════════════════════════
    # NOTA
    # ═══════════════════════════════════════════════════════════════════════════
    if cot.get("nota"):
        story.append(Spacer(1, 14))
        story.append(p("NOTA ADICIONAL:", "section"))
        nota_t = Table([[p(cot["nota"])]], colWidths=[17.5*cm])
        nota_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), c_light),
            ("BOX",           (0,0), (-1,-1), 0.5, c_border),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(nota_t)

    # ═══════════════════════════════════════════════════════════════════════════
    # PIE DE PÁGINA
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_border, spaceAfter=6))
    story.append(p(
        f"Esta cotización es de carácter informativo y está sujeta a disponibilidad "
        f"de inventario. Precios en colones costarricenses (₡) con IVA ({iva_pct}%) incluido. "
        f"| {empresa}" + (f" · {tel}" if tel else "") + (f" · {email_emp}" if email_emp else ""),
        "footer"
    ))

    doc.build(story)
    return buffer.getvalue()
