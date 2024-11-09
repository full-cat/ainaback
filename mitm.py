from mitmproxy import http
from bs4 import BeautifulSoup, Comment, NavigableString

def response(flow: http.HTTPFlow) -> None:
    # Solo interceptamos las respuestas de tipo HTML
    flow.response.headers["Access-Control-Allow-Origin"] = "*"
    flow.response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE"
    flow.response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    flow.response.headers["Access-Control-Allow-Credentials"] = "true"  # Permitir credenciales
    if "text/html" in flow.response.headers.get("content-type", ""):
        # Parseamos el contenido HTML con BeautifulSoup
        html = flow.response.content
        soup = BeautifulSoup(html, "html.parser")

        # Ejemplo de modificación: eliminar todas las ocurrencias de una palabra específica
        # for text_element in soup.find_all(string=lambda text: text and "palabra_especifica" in text):
        #     updated_text = text_element.replace("palabra_especifica", "")
        #     text_element.replace_with(updated_text)
        for text_element in soup.find_all(string=True):
            if isinstance(text_element, NavigableString) and not isinstance(text_element, Comment):
                # Reemplaza la palabra sin afectar los estilos ni la estructura
                #cleaned_text = text_element.replace("fuck", "")
                original_text = text_element
                if "<" in original_text.strip() or ">" in original_text.strip() or len(original_text.strip())  == 0 or "html" == text_element.strip():
                    continue

                text_element.replace_with("🔥" + text_element.strip())
                # new_text = f"+{original_text}"
                # text_element.replace_with(new_text)

        # Actualizamos el contenido HTML de la respuesta con el HTML modificado
        flow.response.content = str(soup).encode("utf-8")
