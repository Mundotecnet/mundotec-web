"""
Generación de descripciones de productos con IA (Claude).
"""
import anthropic
import json
from config import ANTHROPIC_API_KEY
from db import query

PROMPT_SISTEMA = """Eres un experto en redacción de fichas de productos tecnológicos y mobiliario
para un sitio web de ventas en Costa Rica. Tu tarea es generar descripciones atractivas y precisas.

Responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
{
  "descripcion": "Descripción comercial del producto en 2-3 oraciones, atractiva y orientada al cliente. Máximo 200 caracteres.",
  "caracteristicas": [
    "Característica 1 concisa",
    "Característica 2 concisa",
    "Característica 3 concisa",
    "Característica 4 concisa",
    "Característica 5 concisa"
  ]
}

Las características deben ser puntos clave del producto (material, dimensiones, beneficio, uso, garantía, etc.).
Usa el nombre del producto para inferir sus atributos. Escribe en español, tono profesional pero accesible."""


def generar_descripcion(nombre: str, categoria: str = "", descripcion_syma: str = "") -> dict:
    """Llama a Claude y retorna descripcion + caracteristicas."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY no configurada en config.py o variable de entorno.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    contexto = f"Producto: {nombre}"
    if categoria:
        contexto += f"\nCategoría: {categoria}"
    if descripcion_syma:
        contexto += f"\nDescripción técnica: {descripcion_syma}"

    msg = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=512,
        messages=[{"role": "user", "content": contexto}],
        system=PROMPT_SISTEMA,
    )

    texto = msg.content[0].text.strip()
    # Limpiar posible markdown ```json ... ```
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return json.loads(texto.strip())


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
