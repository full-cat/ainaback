from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup, Comment, NavigableString
from urllib.parse import urljoin
from urllib.parse import urlparse
from inference import translate

app = Flask(__name__)

@app.route('/proxy', methods=['GET'])
def proxy():
    # Obtener la URL de la página principal desde los parámetros
    global base_url
    url = request.args.get('url')
    base_url = "https://" + urlparse(url).netloc
    if not url:
        return "URL no proporcionada", 400
    
    # Obtener la página del sitio de destino
    try:
        resp = requests.get(url)
    except requests.RequestException as e:
        return f"Error al obtener la página: {e}", 500
    
    # Si la respuesta no es HTML, devolverla sin modificar
    content_type = resp.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return Response(resp.content, content_type=content_type)
    
    # Modificar el HTML si es una página web
    soup = BeautifulSoup(resp.content, 'html.parser')
    
        # Traducir y modificar solo los textos
    for text_element in soup.find_all(string=True):
        if isinstance(text_element, NavigableString) and not isinstance(text_element, Comment):
            # Reemplaza la palabra sin afectar los estilos ni la estructura
            #cleaned_text = text_element.replace("fuck", "")
            original_text = text_element
            if "<" in original_text.strip() or ">" in original_text.strip() or len(original_text.strip())  == 0 or "html" == text_element.strip():
                continue

            translation = translate(text_element.strip())
            text_element.replace_with(translation)
            # new_text = f"+{original_text}"
            # text_element.replace_with(new_text)

    # replace all links in html
    # Find all <a> tags
    for link in soup.find_all('a'):
        # Replace the href attribute with a new link (for example, replace it with 'https://new-link.com')
        if link.get('href') is None:
            continue
        stem = url if link.get('href').startswith("/") else ""
        if link.get('href'):
            link['href'] = "http://localhost:5000/proxy?url=" + stem +  link['href']
        # Alternatively, replace the entire content of the <a> tag
        # link.string = "New Link Text"

    # Get the modified HTML content
    modified_html = str(soup)

    
    # # Reescribir los recursos estáticos (CSS, imágenes, etc.) para que apunten al proxy
    # for tag in soup.find_all(['link', 'script', 'img', "spreadsheet"]):
    #     if tag.name == 'link' and tag.get('href'):
    #         tag['href'] = urljoin(url, tag['href'])
    #     elif tag.name == 'script' and tag.get('src'):
    #         tag['src'] = urljoin(url, tag['src'])
    #     elif tag.name == 'img' and tag.get('src'):
    #         tag['src'] = urljoin(url, tag['src'])
    #     elif tag.name == 'spreadsheet' and tag.get('src'):
    #         tag['src'] = urljoin(url, tag['src'])

    # # Convertir el HTML modificado en cadena para enviarlo
    # modified_html = str(soup)
    return Response(modified_html, content_type='text/html')

# @app.route('/<path:filename>')
# allow ALL methods
@app.route('/<path:filename>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def serve_media(filename):
    global base_url

    # Construir la URL completa para el recurso solicitado
    resource_url = urljoin(base_url, filename)
    
    # Realizar la solicitud para obtener el recurso (imagen, CSS, etc.)
    try:
        resource_response = requests.get(resource_url)
        if resource_response.status_code == 200:
            # Determinar el tipo de recurso (imagen, CSS, etc.)
            content_type = resource_response.headers.get('Content-Type')
            return Response(resource_response.content, content_type=content_type)
        else:
            return "Resource not found", 404
    except requests.exceptions.RequestException as e:
        return str(e), 500


if __name__ == '__main__':
    app.run(debug=True)
