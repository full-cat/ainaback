from mitmproxy import http
from bs4 import BeautifulSoup, Comment, NavigableString

def response(flow: http.HTTPFlow) -> None:
    # Añadir cabeceras CORS
    flow.response.headers["Access-Control-Allow-Origin"] = "*"
    flow.response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    flow.response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    flow.response.headers["Access-Control-Allow-Credentials"] = "true"  # Permitir credenciales

    # Eliminar la cabecera Content-Security-Policy si está presente para evitar restricciones de seguridad
    if "Content-Security-Policy" in flow.response.headers:
        del flow.response.headers["Content-Security-Policy"]

    # Procesar solo respuestas HTML
    if "text/html" in flow.response.headers.get("content-type", ""):
        html = flow.response.content
        soup = BeautifulSoup(html, "html.parser")

        # Modificar el texto de la página
        for text_element in soup.find_all(string=True):
            # Solo modificar textos válidos (evitar etiquetas y comentarios)
            if isinstance(text_element, NavigableString) and not isinstance(text_element, Comment):
                original_text = text_element.strip()
                # Saltar textos vacíos o que puedan afectar la estructura HTML
                if "<" in original_text or ">" in original_text or len(original_text) == 0:
                    continue
                # Añadir un emoji al texto como ejemplo de modificación
                text_element.replace_with("🔥" + original_text)

        # Actualizar el contenido HTML en la respuesta
        flow.response.content = str(soup).encode("utf-8")
