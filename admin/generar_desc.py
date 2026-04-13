"""
Generación de descripciones de productos.
- Con API Key de Anthropic: usa Claude IA
- Sin API Key: generador local inteligente por reglas
"""
import re
import json
from config import ANTHROPIC_API_KEY
from db import query


# ─────────────────────────────────────────────────────────────────────────────
# GENERADOR LOCAL (sin API key)
# ─────────────────────────────────────────────────────────────────────────────

# Tupla: (label, articulo, descripcion_cuerpo_sin_repetir_label, generico_chars_categoria)
# El cuerpo empieza minúscula para unirse con "El/La {tipo} {marca} {modelo} + cuerpo"
TIPOS = {
    # Impresoras — abreviaturas primero para mayor prioridad
    "imp mf":       ("impresora multifuncional", "La", "combina impresión, escaneo y copiado en un solo dispositivo compacto y eficiente.", "impresora"),
    "impr mf":      ("impresora multifuncional", "La", "combina impresión, escaneo y copiado en un solo dispositivo compacto y eficiente.", "impresora"),
    "multifuncional":("impresora multifuncional","La", "combina impresión, escaneo y copiado en un solo dispositivo compacto y eficiente.", "impresora"),
    "impresora":    ("impresora",   "La",  "ofrece impresiones nítidas para uso profesional y doméstico, con bajo costo por página.", "impresora"),
    "impr ":        ("impresora",   "La",  "ofrece impresiones nítidas para uso profesional y doméstico, con bajo costo por página.", "impresora"),
    # Mobiliario
    "silla":        ("silla",       "La",  "ergonómica está diseñada para máxima comodidad en largas jornadas de trabajo, con construcción robusta y materiales de alta calidad.", "silla"),
    "escritorio":   ("escritorio",  "El",  "es funcional y espacioso, ideal para optimizar su área de trabajo con comodidad y organización.", "generico"),
    "mesa":         ("mesa",        "La",  "es resistente y versátil, perfecta para trabajo en equipo o uso personal en oficina o hogar.", "generico"),
    # Redes
    "access point": ("access point","El",  "amplía y mejora la cobertura WiFi en su hogar u oficina de manera sencilla y eficiente.", "red"),
    "router":       ("router",      "El",  "ofrece conexión estable y veloz de alto rendimiento, ideal para hogares y oficinas con múltiples dispositivos.", "red"),
    "switch":       ("switch",      "El",  "permite conectar múltiples dispositivos con transferencia de datos rápida y estable.", "red"),
    "gabinete":     ("gabinete",    "El",  "de red organiza y protege su infraestructura de telecomunicaciones de forma segura y ordenada.", "red"),
    # Cómputo
    "laptop":       ("laptop",      "La",  "es potente y portátil, perfecta para trabajo, estudio y entretenimiento con diseño liviano.", "laptop"),
    "notebook":     ("laptop",      "La",  "es potente y portátil, perfecta para trabajo, estudio y entretenimiento con diseño liviano.", "laptop"),
    "monitor":      ("monitor",     "El",  "ofrece alta resolución con colores vibrantes y diseño ergonómico, ideal para trabajo y entretenimiento.", "monitor"),
    "teclado":      ("teclado",     "El",  "está diseñado para mayor comodidad y productividad, con teclas de respuesta precisa para uso intensivo.", "generico"),
    "mouse":        ("mouse",       "El",  "ergonómico cuenta con sensor de alta precisión, diseñado para uso prolongado sin fatiga.", "generico"),
    "ups":          ("UPS",         "El",  "protege sus equipos ante cortes y fluctuaciones eléctricas, garantizando continuidad operativa.", "ups"),
    "disco":        ("disco duro",  "El",  "ofrece almacenamiento de alta capacidad y velocidad para resguardar su información con seguridad.", "generico"),
    "ssd":          ("SSD",         "El",  "de estado sólido acelera el arranque y el rendimiento general del sistema de manera significativa.", "generico"),
    "memoria":      ("memoria RAM", "La",  "de alta velocidad mejora el rendimiento y la capacidad de respuesta de su equipo.", "generico"),
    "tablet":       ("tablet",      "La",  "es versátil para trabajo, entretenimiento y educación, con pantalla clara y batería de larga duración.", "generico"),
    "celular":      ("smartphone",  "El",  "cuenta con funciones avanzadas, cámara de alta resolución y batería de larga duración.", "generico"),
    "proyector":    ("proyector",   "El",  "de alta luminosidad es ideal para presentaciones, cine en casa y uso educativo.", "generico"),
    # Audio/Video
    "audifono":     ("audífonos",   "Los", "ofrecen sonido de alta fidelidad con diseño cómodo para uso extendido en trabajo o entretenimiento.", "generico"),
    "auricular":    ("audífonos",   "Los", "ofrecen sonido de alta fidelidad con diseño cómodo para uso extendido en trabajo o entretenimiento.", "generico"),
    "camara":       ("cámara",      "La",  "de alta resolución captura imágenes y video con calidad profesional.", "generico"),
    "telescopio":   ("telescopio",  "El",  "de alta óptica permite observación astronómica y terrestre, perfecto para aficionados y entusiastas.", "generico"),
}

MARCAS = [
    # Cómputo y periféricos
    "thunderx3","xtech","hp","dell","lenovo","asus","acer","samsung",
    "logitech","intel","amd","kingston","seagate","western digital","wd",
    "corsair","crucial","viewsonic","benq","lg",
    # Impresoras
    "epson","brother","canon",
    # Redes
    "ubiquiti","tp-link","mikrotik","cisco","trendnet","netgear","dlink","d-link",
    # UPS / energía
    "apc","eaton","cyberpower",
    # Móviles / electrónica
    "xiaomi","huawei","sony","panasonic","philips","sharp","toshiba","hyundai",
    # Óptica / telescopios
    "tasco","celestron","meade","orion",
]

COLORES = {
    "black":"negro","white":"blanco","red":"rojo","blue":"azul",
    "green":"verde","pink":"rosado","yellow":"amarillo","gray":"gris",
    "silver":"plateado","gold":"dorado","sakura":"rosado sakura",
}

MATERIALES = {
    "mesh":"malla transpirable","leather":"cuero","fabric":"tela",
    "metal":"estructura metálica","wood":"madera","aluminum":"aluminio",
    "plastic":"plástico de alta resistencia",
}


def _detectar_tipo(nombre: str) -> tuple:
    """Retorna (label, articulo, cuerpo_desc, cat_generica)."""
    n = nombre.lower()
    for k, v in TIPOS.items():
        if k in n:
            return v
    return ("producto", "El", "es de calidad con características técnicas superiores para uso profesional y personal.", "generico")


def _detectar_marca(nombre: str) -> str:
    n = nombre.lower()
    for m in MARCAS:
        if m in n:
            return m.upper() if len(m) <= 5 else m.title()
    return ""


def _detectar_modelo(nombre: str, marca: str) -> str:
    n = nombre.upper()
    if marca:
        n = n.replace(marca.upper(), "").strip()
    # buscar patrones de modelo: letras+números
    modelos = re.findall(r'\b[A-Z]{1,5}[-]?\d{2,6}[A-Z0-9-]*\b', n)
    return modelos[0] if modelos else ""


def _detectar_color(nombre: str) -> str:
    n = nombre.lower()
    for k, v in COLORES.items():
        if k in n:
            return v
    return ""


def _detectar_material(nombre: str) -> str:
    n = nombre.lower()
    for k, v in MATERIALES.items():
        if k in n:
            return v
    return ""


def _detectar_specs(nombre: str) -> list:
    """Extrae especificaciones del nombre: resolución, velocidad, WiFi, CPU, etc."""
    specs = []
    n = nombre.upper()

    if "WIFI 6" in n or "WI-FI 6" in n or "AX" in n and "WIFI" in n:
        specs.append("WiFi 6 de alta velocidad")
    elif "WIFI" in n or "WI-FI" in n or "WIRELESS" in n:
        specs.append("Conectividad WiFi inalámbrica")
    if "USB-C" in n or "USB C" in n:
        specs.append("Puerto USB-C")
    elif "USB" in n:
        specs.append("Puerto USB incluido")
    if "BLUETOOTH" in n:
        specs.append("Bluetooth integrado")
    if "4K" in n or "UHD" in n:
        specs.append("Resolución 4K Ultra HD")
    elif "QHD" in n or "2K" in n or "1440" in n:
        specs.append("Resolución QHD 2K")
    elif "FHD" in n or "1080" in n or "FULL HD" in n:
        specs.append("Pantalla Full HD 1080p")
    elif re.search(r'\bHD\b', n) and "4K" not in n and "QHD" not in n:
        specs.append("Resolución HD")
    if "LED" in n:
        specs.append("Tecnología LED")
    if "LASER" in n or "LÁSER" in n:
        specs.append("Tecnología láser de precisión")
    if "TOUCH" in n:
        specs.append("Pantalla táctil")
    if "GAMING" in n or "GAMER" in n:
        specs.append("Diseño gaming de alto rendimiento")
    if "ERGON" in n:
        specs.append("Diseño ergonómico certificado")
    if re.search(r'\b360\b', n):
        specs.append("Rotación 360 grados")
    if "RGB" in n:
        specs.append("Iluminación RGB personalizable")

    # Procesadores
    if "RYZEN 9" in n or "I9" in n or "CORE I9" in n:
        specs.append("Procesador de alto rendimiento")
    elif "RYZEN 7" in n or "I7" in n or "CORE I7" in n:
        specs.append("Procesador Intel Core i7 / AMD Ryzen 7")
    elif "RYZEN 5" in n or "I5" in n or "CORE I5" in n:
        specs.append("Procesador Intel Core i5 / AMD Ryzen 5")
    elif "RYZEN 3" in n or "I3" in n or "CORE I3" in n:
        specs.append("Procesador Intel Core i3 / AMD Ryzen 3")
    elif "CELERON" in n or "PENTIUM" in n:
        specs.append("Procesador Intel Celeron/Pentium")

    # RAM
    ram = re.search(r'(\d+)\s*GB\s*(RAM|DDR)', n)
    if ram:
        specs.append(f"{ram.group(1)} GB RAM")

    # Almacenamiento
    ssd = re.search(r'(\d+)\s*GB\s*SSD|(\d+)\s*TB\s*SSD', n)
    hdd = re.search(r'(\d+)\s*(TB|GB)\s*(HDD|DISCO)', n)
    if ssd:
        val = ssd.group(1) or ssd.group(2)
        unit = "GB" if ssd.group(1) else "TB"
        specs.append(f"Almacenamiento SSD {val}{unit}")
    elif hdd:
        specs.append(f"Disco duro {hdd.group(1)} {hdd.group(2)}")

    # Velocidades de red (solo números reales, no modelos)
    vel = re.search(r'(\d{3,4})\s*MBPS', n)
    if vel:
        specs.append(f"Velocidad hasta {vel.group(1)} Mbps")
    else:
        # Estándares WiFi como AC1200, AC2400...
        est = re.search(r'\b(AC\d{3,4}|AX\d{3,4})\b', n)
        if est:
            specs.append(f"Estándar {est.group(1)}")

    # Tamaño de pantalla (solo si viene acompañado de " o pulgadas/pulg/inch)
    pant = re.search(r'(\d{2})\s*(?:"|PULG|PULGADAS|INCH)\b', n)
    if pant and int(pant.group(1)) in range(13, 50):
        specs.append(f'Pantalla de {pant.group(1)}"')

    return specs[:4]


CHARS_GENERICOS = {
    "silla":      ["Asiento y respaldo acolchonados", "Base con ruedas de alta resistencia",
                   "Ajuste de altura neumático", "Apoyabrazos regulables"],
    "impresora":  ["Impresión en color y blanco/negro", "Compatible con Windows y Mac",
                   "Bajo costo por página", "Conectividad USB"],
    "red":        ["Cobertura de amplio alcance", "Múltiples puertos LAN",
                   "Configuración sencilla vía web", "Firewall integrado"],
    "laptop":     ["Sistema operativo incluido", "Batería de larga duración",
                   "Puertos USB y HDMI", "Teclado retroiluminado"],
    "monitor":    ["Panel IPS de alta calidad", "Ajuste de inclinación ergonómico",
                   "Entrada HDMI y DisplayPort", "Bajo consumo energético"],
    "ups":        ["Protección contra cortes eléctricos", "Tiempo de respaldo garantizado",
                   "Pantalla LCD de estado", "Protección de sobretensión"],
    "telescopio": ["Trípode incluido", "Montura altazimutal",
                   "Uso astronómico y terrestre", "Ocular y buscador incluidos"],
    "generico":   ["Garantía de fábrica", "Diseño compacto y moderno",
                   "Fácil instalación y configuración", "Soporte técnico disponible"],
}


def generar_descripcion_local(nombre: str, categoria: str = "", descripcion_syma: str = "") -> dict:
    """Genera descripción y características sin API, por análisis del nombre."""
    tipo_label, articulo, cuerpo_desc, cat_gen = _detectar_tipo(nombre)
    marca   = _detectar_marca(nombre)
    modelo  = _detectar_modelo(nombre, marca)
    color   = _detectar_color(nombre)
    mat     = _detectar_material(nombre)
    specs   = _detectar_specs(nombre)

    # ── Descripción ──────────────────────────────────────────────────────────
    # Formato: "{Articulo} {tipo} {Marca} {Modelo} {cuerpo}. Color X."
    partes = [articulo, tipo_label]
    if marca:
        partes.append(marca)
    if modelo:
        partes.append(modelo)
    intro = " ".join(partes)

    descripcion = f"{intro} {cuerpo_desc}"
    if color:
        descripcion = descripcion.rstrip('.') + f". Color {color}."
    if not descripcion.endswith('.'):
        descripcion += "."

    if len(descripcion) > 240:
        descripcion = descripcion[:237] + "..."

    # ── Características ───────────────────────────────────────────────────────
    chars = []
    if marca:
        chars.append(f"Marca: {marca}")
    if modelo:
        chars.append(f"Modelo: {modelo}")
    if color:
        chars.append(f"Color: {color.capitalize()}")
    if mat:
        chars.append(f"Material: {mat.capitalize()}")

    # Specs especiales para telescopios: extraer apertura x focal del nombre
    if tipo_label == "telescopio":
        tel = re.search(r'(\d{2,3})[Xx×](\d{3,4})\s*[Mm][Mm]?', nombre)
        if tel:
            chars.append(f"Apertura: {tel.group(1)} mm")
            chars.append(f"Distancia focal: {tel.group(2)} mm")
        aum = re.search(r'(\d+)\s*[Xx×]\s*(?:AUM|AUMENTOS?)', nombre.upper())
        if aum:
            chars.append(f"Aumentos: {aum.group(1)}x")

    chars.extend(specs)

    # ── Genéricos por categoría ───────────────────────────────────────────────
    cat_lower = (categoria or "").lower() + " " + nombre.lower()
    gen_key = cat_gen  # heredado del tipo detectado
    if "silla" in cat_lower:
        gen_key = "silla"
    elif "impresora" in cat_lower or "imp mf" in cat_lower or "impr" in cat_lower:
        gen_key = "impresora"
    elif any(k in cat_lower for k in ("router", "switch", "red", "network", "access point")):
        gen_key = "red"
    elif any(k in cat_lower for k in ("laptop", "notebook")):
        gen_key = "laptop"
    elif "monitor" in cat_lower:
        gen_key = "monitor"
    elif "ups" in cat_lower:
        gen_key = "ups"
    elif "telescopio" in cat_lower:
        gen_key = "telescopio"

    genericos = CHARS_GENERICOS.get(gen_key, CHARS_GENERICOS["generico"])
    if len(chars) < 5:
        chars += [g for g in genericos if g not in chars]

    return {
        "descripcion":     descripcion,
        "caracteristicas": chars[:5],
        "fuente":          "local",
    }


# ─────────────────────────────────────────────────────────────────────────────
# GENERADOR CON IA (con API key)
# ─────────────────────────────────────────────────────────────────────────────

PROMPT_SISTEMA = """Eres experto en redacción de fichas de productos tecnológicos y mobiliario
para un sitio web de ventas en Costa Rica. Genera descripciones atractivas y precisas.

Responde ÚNICAMENTE con un JSON válido con esta estructura:
{
  "descripcion": "Descripción comercial en 2-3 oraciones. Máximo 220 caracteres.",
  "caracteristicas": [
    "Marca: valor",
    "Modelo: valor",
    "Etiqueta relevante: valor concreto",
    "Etiqueta relevante: valor concreto",
    "Etiqueta relevante: valor concreto"
  ],
  "fuente": "claude"
}

IMPORTANTE: Cada característica DEBE tener formato "Etiqueta: Valor" con dos puntos separando etiqueta y valor.
Ejemplos correctos: "Marca: ThunderX3", "Color: Negro/Rojo", "Capacidad: 150 kg", "Conectividad: WiFi 6"
Ejemplos incorrectos: "Diseño ergonómico con soporte lumbar", "Base de 5 ruedas"

Usa el nombre del producto para inferir atributos reales. Español, tono profesional y accesible."""


def generar_descripcion_claude(nombre: str, categoria: str = "", descripcion_syma: str = "") -> dict:
    import anthropic
    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    ctx     = f"Producto: {nombre}"
    if categoria:       ctx += f"\nCategoría: {categoria}"
    if descripcion_syma: ctx += f"\nInfo técnica: {descripcion_syma[:200]}"

    msg   = client.messages.create(
        model="claude-haiku-4-5", max_tokens=512,
        messages=[{"role":"user","content":ctx}],
        system=PROMPT_SISTEMA,
    )
    texto = msg.content[0].text.strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"): texto = texto[4:]
    return json.loads(texto.strip())


def generar_descripcion(nombre: str, categoria: str = "", descripcion_syma: str = "") -> dict:
    """Punto de entrada: usa Claude si hay API key, si no usa el generador local."""
    if ANTHROPIC_API_KEY:
        return generar_descripcion_claude(nombre, categoria, descripcion_syma)
    return generar_descripcion_local(nombre, categoria, descripcion_syma)


# ─────────────────────────────────────────────────────────────────────────────

def get_productos_sin_descripcion() -> list:
    return query("""
        SELECT p.id, p.codigo, p.nombre, p.categoria,
               p.descripcion_syma, p.descripcion_web,
               i.url_path AS imagen_principal
        FROM catalogo_productos p
        LEFT JOIN catalogo_imagenes i ON i.producto_id=p.id AND i.es_principal=TRUE
        WHERE p.activo=TRUE
        ORDER BY (p.descripcion_web IS NULL OR p.descripcion_web='') DESC, p.nombre
    """)
