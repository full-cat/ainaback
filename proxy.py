from flask import Flask, request, Response, render_template
import requests
import redis
from bs4 import BeautifulSoup, Comment, NavigableString
from urllib.parse import urljoin
from urllib.parse import urlparse

app = Flask(__name__)
r = redis.Redis(host="localhost", port=6379, db=0)


@app.route("/proxy", methods=["GET"])
def proxy():
    # Obtener la URL de la página principal desde los parámetros
    global base_url
    url = request.args.get("url")
    print(url)
    print(urlparse(url).netloc)
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
    soup = BeautifulSoup(resp.content, "html.parser")

    # Traducir y modificar solo los textos
    for text_element in soup.find_all(string=True):
        if isinstance(text_element, NavigableString) and not isinstance(text_element, Comment):
            # Reemplaza la palabra sin afectar los estilos ni la estructura
            # cleaned_text = text_element.replace("fuck", "")
            original_text = text_element
            if (
                "<" in original_text.strip()
                or ">" in original_text.strip()
                or len(original_text.strip()) == 0
                or "html" == text_element.strip()
            ):
                continue

            if translated_text := r.hget(url, original_text):
                # decode utf-8
                translated_text = translated_text.decode("utf-8")
                print(f"{original_text} -> {translated_text} (cached)")
            else:
                print(f"Request translate for '{original_text}' ({url})")

                # TODO get translation from aina
                translated_text = "🔥" + text_element.strip() + "🔥"

                r.hset(url, original_text, translated_text)
                print(f"{original_text} -> {translated_text} (saved to cache)")

            text_element.replace_with(translated_text)
            # new_text = f"+{original_text}"
            # text_element.replace_with(new_text)

    # replace all links in html
    # Find all <a> tags
    for link in soup.find_all("a"):
        # Replace the href attribute with a new link (for example, replace it with 'https://new-link.com')
        if link.get("href") is None:
            continue
        stem = url if link.get("href").startswith("/") else ""
        if link.get("href"):
            link["href"] = "http://localhost:5000/proxy?url=" + stem + link["href"]
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

    return render_template("iframe.html", content=modified_html)

    # return Response(modified_html, content_type="text/html")


@app.route("/feedback", methods=["POST"])
def feedback():
    print("feedback")
    # get json data
    request_data = request.get_json()
    print(request_data)
    return {"status": "ok"}


@app.route("/lookupTranslation", methods=["GET"])
def get_translate():
    url = request.args.get("url")
    text = request.args.get("text")
    print(url, text)
    translations = r.hgetall(url)
    if not translations:
        return {"message": "No translations found"}, 404

    for key in translations.keys():
        original_text = key.decode("utf-8")
        if text in original_text:
            return {"originalText": original_text}, 200

    return {"message": "No translations found"}, 404


# @app.route('/<path:filename>')
# allow ALL methods
@app.route("/<path:filename>", methods=["GET", "POST", "PUT", "DELETE"])
def serve_media(filename):
    global base_url
    print("putilla")
    # Construir la URL completa para el recurso solicitado
    resource_url = urljoin(base_url, filename)

    # Realizar la solicitud para obtener el recurso (imagen, CSS, etc.)
    try:
        resource_response = requests.get(resource_url)
        if resource_response.status_code == 200:
            # Determinar el tipo de recurso (imagen, CSS, etc.)
            content_type = resource_response.headers.get("Content-Type")
            return Response(resource_response.content, content_type=content_type)
        else:
            return "Resource not found", 404
    except requests.exceptions.RequestException as e:
        return str(e), 500


if __name__ == "__main__":
    assert r.ping()
    app.run(debug=True)
