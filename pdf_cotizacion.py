"""
Generador de PDF para cotizaciones — MUNDOTEC S.A.
Requiere: pip install reportlab
"""
import io
import os
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable, Image as RLImage,
                                 KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Registro de fuentes Unicode (DejaVu soporta el símbolo ₡) ────────────────
_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",          # Ubuntu / Debian
    "/usr/share/fonts/dejavu",                   # otras distros Linux
    "/System/Library/Fonts",                      # macOS (fallback)
]

def _find_font(filename: str) -> str | None:
    for d in _FONT_DIRS:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return path
    return None

_regular = _find_font("DejaVuSans.ttf")
_bold    = _find_font("DejaVuSans-Bold.ttf")

if _regular and _bold:
    pdfmetrics.registerFont(TTFont("MW",     _regular))
    pdfmetrics.registerFont(TTFont("MW-Bold", _bold))
    FONT_NORMAL = "MW"
    FONT_BOLD   = "MW-Bold"
else:
    # Fallback: Helvetica no muestra ₡ pero no rompe el PDF
    FONT_NORMAL = "Helvetica"
    FONT_BOLD   = "Helvetica-Bold"

# ── Datos fijos de la empresa ──────────────────────────────────────────────────
EMPRESA = {
    "razon_social": "MUNDOTEC SOCIEDAD ANONIMA",
    "cedula":       "3-101-565688",
    "telefono":     "2460-2460",
    "email":        "facturacompra@mundoteconline.com",
    "actividad":    "4651.0",
    "direccion":    "Entre Calle 1 y Avenida 3",
    "ciudad":       "Alajuela, San Carlos, Ciudad Quesada",
}

CUENTAS_BANCARIAS = [
    ("BNCR",         "200-01-012-040079-7",  "CR66015101220010400799",  "Colones"),
    ("BNCR",         "200-02-012-016909-8",  "CR17015101220020169096",  "Dólares"),
    ("BCR",          "001-1034468-3",         "CR62015202001103446831",  "Colones"),
    ("BAC SAN JOSE", "909636870",             "CR13010200009096368706",  "Colones"),
    ("BAC SAN JOSE", "943988253",             "CR15010200009439882530",  "Dólares"),
    ("SINPE MÓVIL",  "87060002",              "—",                       "—"),
]

# Ruta del logo (relativa al archivo pdf_cotizacion.py)
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "static", "logo.png")


def generar_pdf_cotizacion(cot: dict, cfg: dict) -> bytes:
    """
    Genera el PDF de una cotización y devuelve los bytes.
    cot : dict con los datos de la cotización (de la tabla cotizaciones)
    cfg : dict con la configuración del sitio (colores, etc.)
    """
    buffer = io.BytesIO()

    # ── Colores ───────────────────────────────────────────────────────────────
    try:
        c_primary = colors.HexColor(cfg.get("color_primario", "#1E4E8C"))
    except Exception:
        c_primary = colors.HexColor("#1E4E8C")

    c_light  = colors.HexColor("#EFF6FF")
    c_gray   = colors.HexColor("#6B7280")
    c_border = colors.HexColor("#E5E7EB")
    c_rowalt = colors.HexColor("#F8FAFC")
    c_white  = colors.white

    # ── Datos de la cotización ─────────────────────────────────────────────────
    iva_pct  = int(cot.get("iva_pct", 13))
    items    = cot.get("items", [])

    fecha = cot.get("creado_en") or datetime.now()
    fecha_str = fecha.strftime("%d/%m/%Y") if hasattr(fecha, "strftime") else str(fecha)[:10]

    cot_id  = cot.get("id", 0)
    num_cot = f"COT-{cot_id:05d}"

    # ── Documento ─────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=1.8*cm, leftMargin=1.8*cm,
        topMargin=1.8*cm,   bottomMargin=1.8*cm,
        title=f"Cotización {num_cot} — {EMPRESA['razon_social']}",
        author=EMPRESA["razon_social"],
    )

    # ── Helper de estilos ─────────────────────────────────────────────────────
    def sty(**kw):
        d = dict(fontName=FONT_NORMAL, fontSize=9, leading=13,
                 textColor=colors.HexColor("#1a1a2e"))
        d.update(kw)
        return ParagraphStyle("_", **d)

    def p(text, style=None, **kw):
        s = style if isinstance(style, ParagraphStyle) else sty(**kw)
        return Paragraph(str(text), s)

    def fmt(n):
        try:    return f"\u20a1{float(n):,.0f}"
        except: return "\u2014"

    story = []

    # ═══════════════════════════════════════════════════════════════════════════
    # ENCABEZADO: Logo | Datos empresa | Nº / Fecha
    # ═══════════════════════════════════════════════════════════════════════════
    # Columna izquierda: logo + nombre
    if os.path.exists(LOGO_PATH):
        logo_img = RLImage(LOGO_PATH, width=3.8*cm, height=2.2*cm, kind="proportional")
        col_logo = logo_img
    else:
        col_logo = p(EMPRESA["razon_social"],
                     sty(fontName=FONT_BOLD, fontSize=18, textColor=c_primary))

    empresa_info = (
        f"<b>{EMPRESA['razon_social']}</b><br/>"
        f"Cédula jurídica: {EMPRESA['cedula']}<br/>"
        f"Tel: {EMPRESA['telefono']}  ·  {EMPRESA['email']}<br/>"
        f"Act. Económica: {EMPRESA['actividad']}<br/>"
        f"{EMPRESA['direccion']}<br/>{EMPRESA['ciudad']}"
    )

    col_empresa = p(empresa_info, sty(fontSize=8, leading=12, textColor=c_gray))

    col_cot = p(
        f"<b>COTIZACIÓN</b><br/>"
        f"<font size='11'>{num_cot}</font><br/>"
        f"<font size='8' color='#6B7280'>Fecha: {fecha_str}</font>",
        sty(fontName=FONT_BOLD, fontSize=16, textColor=c_primary,
            alignment=TA_RIGHT, leading=20)
    )

    if os.path.exists(LOGO_PATH):
        header_data  = [[col_logo, col_empresa, col_cot]]
        header_widths = [4*cm, 9*cm, 4.5*cm]
    else:
        header_data  = [[col_empresa, col_cot]]
        header_widths = [12.5*cm, 5*cm]

    header_t = Table(header_data, colWidths=header_widths)
    header_t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ("RIGHTPADDING",  (0,0), (-1,-1), 4),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(header_t)
    story.append(HRFlowable(width="100%", thickness=2.5, color=c_primary,
                             spaceBefore=10, spaceAfter=14))

    # ═══════════════════════════════════════════════════════════════════════════
    # DATOS DEL CLIENTE
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(p("DATOS DEL CLIENTE",
                   sty(fontName=FONT_BOLD, fontSize=7.5,
                       textColor=c_gray, spaceAfter=4)))

    cliente_rows = []
    if cot.get("nombre"):   cliente_rows.append(["Nombre:",   cot["nombre"]])
    if cot.get("empresa"):  cliente_rows.append(["Empresa:",  cot["empresa"]])
    if cot.get("telefono"): cliente_rows.append(["Teléfono:", cot["telefono"]])
    if cot.get("email"):    cliente_rows.append(["Correo:",   cot["email"]])

    if cliente_rows:
        ct = Table(cliente_rows, colWidths=[2.8*cm, 14.7*cm])
        ct.setStyle(TableStyle([
            ("FONTNAME",      (0,0), (0,-1), FONT_BOLD),
            ("FONTSIZE",      (0,0), (-1,-1), 8.5),
            ("TEXTCOLOR",     (0,0), (0,-1), c_gray),
            ("BACKGROUND",    (0,0), (-1,-1), c_light),
            ("BOX",           (0,0), (-1,-1), 0.5, c_border),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(ct)

    story.append(Spacer(1, 16))

    # ═══════════════════════════════════════════════════════════════════════════
    # TABLA DE PRODUCTOS
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(p("DETALLE DE PRODUCTOS",
                   sty(fontName=FONT_BOLD, fontSize=7.5,
                       textColor=c_gray, spaceAfter=4)))

    th = sty(fontName=FONT_BOLD, fontSize=7.5,
              textColor=c_white, alignment=TA_CENTER)

    rows = [[
        p("Código",           th), p("Descripción",      th),
        p("Cant.",            th), p("P.Unit s/IVA",     th),
        p(f"IVA ({iva_pct}%)", th), p("P.Unit c/IVA",   th),
        p("Subtotal",         th),
    ]]

    for it in items:
        p_ref   = float(it.get("precio_ref") or 0)
        p_iva_u = p_ref * (1 + iva_pct / 100)
        iva_u   = p_iva_u - p_ref
        qty     = int(it.get("cantidad", 1))
        sub     = p_iva_u * qty
        rows.append([
            p(it.get("codigo", ""), sty(fontSize=7.5, fontName=FONT_BOLD)),
            p(it.get("nombre",  ""), sty(fontSize=8, leading=11)),
            p(str(qty),              sty(fontSize=8, alignment=TA_CENTER)),
            p(fmt(p_ref),            sty(fontSize=8, alignment=TA_RIGHT)),
            p(fmt(iva_u),            sty(fontSize=8, alignment=TA_RIGHT,
                                         textColor=colors.HexColor("#E67E22"))),
            p(fmt(p_iva_u),          sty(fontSize=8, alignment=TA_RIGHT)),
            p(fmt(sub),              sty(fontSize=8, alignment=TA_RIGHT,
                                         fontName=FONT_BOLD)),
        ])

    items_t = Table(rows, colWidths=[2.3*cm, 5.5*cm, 1.2*cm, 2.5*cm, 1.8*cm, 2.5*cm, 2.5*cm],
                    repeatRows=1)
    items_t.setStyle(TableStyle([
        ("BACKGROUND",     (0,0), (-1,0), c_primary),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [c_white, c_rowalt]),
        ("GRID",           (0,0), (-1,-1), 0.3, c_border),
        ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",     (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 5),
        ("LEFTPADDING",    (0,0), (-1,-1), 5),
        ("RIGHTPADDING",   (0,0), (-1,-1), 5),
    ]))
    story.append(items_t)
    story.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════════════════════════
    # TOTALES
    # ═══════════════════════════════════════════════════════════════════════════
    sin_iva = float(cot.get("total_sin_iva") or 0)
    con_iva = float(cot.get("total_con_iva") or 0)
    iva_sum = con_iva - sin_iva

    totals_t = Table([
        [p(""), p("Subtotal sin IVA:", sty(fontName=FONT_BOLD, fontSize=9,  alignment=TA_RIGHT)), p(fmt(sin_iva), sty(fontSize=9,  alignment=TA_RIGHT))],
        [p(""), p(f"IVA ({iva_pct})%:", sty(fontName=FONT_BOLD, fontSize=9,  alignment=TA_RIGHT)), p(fmt(iva_sum), sty(fontSize=9,  alignment=TA_RIGHT))],
        [p(""), p("TOTAL:",             sty(fontName=FONT_BOLD, fontSize=13, alignment=TA_RIGHT, textColor=c_primary)), p(fmt(con_iva), sty(fontName=FONT_BOLD, fontSize=13, alignment=TA_RIGHT, textColor=c_primary))],
    ], colWidths=[10.5*cm, 4.5*cm, 2.5*cm])
    totals_t.setStyle(TableStyle([
        ("LINEABOVE",     (1,2), (2,2), 1.5, c_primary),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING",    (0,2), (-1,2), 8),
    ]))
    story.append(totals_t)

    # ═══════════════════════════════════════════════════════════════════════════
    # NOTA ADICIONAL
    # ═══════════════════════════════════════════════════════════════════════════
    if cot.get("nota"):
        story.append(Spacer(1, 12))
        story.append(p("NOTA ADICIONAL:",
                       sty(fontName=FONT_BOLD, fontSize=7.5,
                           textColor=c_gray, spaceAfter=4)))
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
    # CUENTAS BANCARIAS
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=1, color=c_border, spaceAfter=10))

    story.append(KeepTogether([
        p("INFORMACIÓN DE PAGO — CUENTAS BANCARIAS",
          sty(fontName=FONT_BOLD, fontSize=8, textColor=c_primary, spaceAfter=6)),

        Table(
            [
                # Header
                [p("Banco",        sty(fontName=FONT_BOLD, fontSize=7.5, textColor=c_white, alignment=TA_CENTER)),
                 p("N° de Cuenta", sty(fontName=FONT_BOLD, fontSize=7.5, textColor=c_white, alignment=TA_CENTER)),
                 p("IBAN",         sty(fontName=FONT_BOLD, fontSize=7.5, textColor=c_white, alignment=TA_CENTER)),
                 p("Moneda",       sty(fontName=FONT_BOLD, fontSize=7.5, textColor=c_white, alignment=TA_CENTER))],
            ] + [
                [p(banco,   sty(fontSize=7.5, fontName=FONT_BOLD)),
                 p(cuenta,  sty(fontSize=7.5, fontName=FONT_NORMAL, alignment=TA_CENTER)),
                 p(iban,    sty(fontSize=7,   fontName=FONT_NORMAL, textColor=c_gray)),
                 p(moneda,  sty(fontSize=7.5, fontName=FONT_NORMAL, alignment=TA_CENTER))]
                for banco, cuenta, iban, moneda in CUENTAS_BANCARIAS
            ],
            colWidths=[3.5*cm, 4.5*cm, 7*cm, 2.5*cm],
            repeatRows=1
        ),
    ]))

    # Estilo de la tabla de cuentas (aplicado después de construirla)
    # Re-crear con estilo
    cuentas_rows = [
        [p("Banco",        sty(fontName=FONT_BOLD, fontSize=7.5, textColor=c_white, alignment=TA_CENTER)),
         p("N° de Cuenta", sty(fontName=FONT_BOLD, fontSize=7.5, textColor=c_white, alignment=TA_CENTER)),
         p("IBAN",         sty(fontName=FONT_BOLD, fontSize=7.5, textColor=c_white, alignment=TA_CENTER)),
         p("Moneda",       sty(fontName=FONT_BOLD, fontSize=7.5, textColor=c_white, alignment=TA_CENTER))],
    ] + [
        [p(banco,  sty(fontSize=7.5, fontName=FONT_BOLD)),
         p(cuenta, sty(fontSize=7.5, alignment=TA_CENTER)),
         p(iban,   sty(fontSize=7,   textColor=c_gray)),
         p(moneda, sty(fontSize=7.5, alignment=TA_CENTER))]
        for banco, cuenta, iban, moneda in CUENTAS_BANCARIAS
    ]

    cuentas_t = Table(cuentas_rows, colWidths=[3.5*cm, 4.2*cm, 7.3*cm, 2.5*cm], repeatRows=1)
    cuentas_t.setStyle(TableStyle([
        ("BACKGROUND",     (0,0), (-1,0), c_primary),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [c_white, c_rowalt]),
        ("GRID",           (0,0), (-1,-1), 0.3, c_border),
        ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",     (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 4),
        ("LEFTPADDING",    (0,0), (-1,-1), 6),
        ("RIGHTPADDING",   (0,0), (-1,-1), 6),
    ]))

    # Reemplazar el KeepTogether con la versión con estilo correcto
    story[-1] = KeepTogether([
        p("INFORMACIÓN DE PAGO — CUENTAS BANCARIAS",
          sty(fontName=FONT_BOLD, fontSize=8, textColor=c_primary, spaceAfter=6)),
        cuentas_t,
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # PIE FINAL
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_border, spaceAfter=5))
    story.append(p(
        f"Esta cotización es de carácter informativo y está sujeta a disponibilidad de inventario. "
        f"Precios en colones costarricenses (₡) con IVA ({iva_pct}%) incluido. "
        f"| {EMPRESA['razon_social']} · Cédula: {EMPRESA['cedula']} · Tel: {EMPRESA['telefono']}",
        sty(fontSize=6.5, textColor=c_gray, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()
