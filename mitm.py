from mitmproxy import http
from bs4 import BeautifulSoup, Comment, NavigableString
from inference import translate_batch_parallel

def response(flow: http.HTTPFlow) -> None:
    # Añadir cabeceras CORS
    flow.response.headers["Access-Control-Allow-Origin"] = "*"
    flow.response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    flow.response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    flow.response.headers["Access-Control-Allow-Credentials"] = "true"

    # Eliminar la cabecera Content-Security-Policy si está presente
    if "Content-Security-Policy" in flow.response.headers:
        del flow.response.headers["Content-Security-Policy"]

    # Procesar solo respuestas HTML
    original_texts = []

    if "text/html" in flow.response.headers.get("content-type", ""):
        html = flow.response.content
        soup = BeautifulSoup(html, "html.parser")

        # Modificar solo el texto visible, evitando <script>, <style>, comentarios y espacio en blanco
        for text_element in soup.find_all(string=True):
            # Ignorar scripts, estilos, comentarios, y contenido dentro de etiquetas no visibles
            if text_element.parent.name in ["script", "style"] or isinstance(text_element, Comment):
                continue

            # Verificar que el texto no es vacío o contiene solo espacio
            if isinstance(text_element, NavigableString):
                original_text = text_element.strip()
                if len(original_text) == 0:
                    continue  # Ignorar espacios en blanco

                # Evitar modificar texto de etiquetas críticas, e.g. 'if' de JS
                if "<" not in original_text and ">" not in original_text:
                    # Añadir un emoji solo si es texto visible
                    original_texts.append(original_text)

        # Translate the text content of the page. Return a dictionary with the original text as the key and the translated text as the value
        translated_texts = translate_batch_parallel(original_texts, src_lang_code='Spanish', tgt_lang_code='Catalan')

        # Replace the original text with the translated text
        for original_text, translated_text in translated_texts.items():
            for text_element in soup.find_all(string=True):
                if original_text in text_element:
                    text_element.replace_with(translated_text)

        # Actualizar el contenido HTML en la respuesta
        flow.response.content = str(soup).encode("utf-8")
