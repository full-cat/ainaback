from flask import Flask, request, Response, render_template
from flask_cors import CORS, cross_origin
import requests
import redis
import time
from bs4 import BeautifulSoup, Comment, NavigableString
from urllib.parse import urljoin
from urllib.parse import urlparse
from flask_cors import CORS

from inference import translate_batch_parallel, chatbot_single_sentence, tts_single_sentence

try:
    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
except ImportError as e:
    print(e)
    pass

app = Flask(__name__)
CORS(app)

r = redis.Redis(host="localhost", port=6379, db=0)


def get_content_requests(target_url):
    res = requests.get(target_url)
    return res.content


def get_content_selenium(target_url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Modo sin ventana
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(target_url)
        time.sleep(10)
        page_source = driver.page_source
        return page_source
    finally:
        driver.quit()


@app.route("/translate", methods=["GET"])
def translate():
    global base_url
    target_url = request.args.get("url")
    base_url = "https://" + urlparse(target_url).netloc
    if not target_url:
        return "URL no proporcionada", 400

    target_content = get_content_selenium(target_url)
    # target_content = get_content_requests(target_url)

    soup = BeautifulSoup(target_content, "html.parser")
    original_texts = []
    text_elements = []
    translated_texts = {}


    # Modificar solo el texto visible, evitando <script>, <style>, comentarios y espacio en blanco
    for text_element in soup.find_all(string=True):
        original_text = text_element.strip()
        # Ignorar scripts, estilos, comentarios, y contenido dentro de etiquetas no visibles

        #         for text_element in soup.find_all(string=True):
        # if isinstance(text_element, NavigableString) and not isinstance(text_element, Comment):
        #     # Reemplaza la palabra sin afectar los estilos ni la estructura
        #     #cleaned_text = text_element.replace("fuck", "")
        #     original_text = text_element
        #     if "<" in original_text.strip() or ">" in original_text.strip() or len(original_text.strip())  == 0 or "html" == text_element.strip() or "{" in text_element.strip() or "}" in text_element.strip():
        #         continue

        #     text_element.replace_with("🔥" + text_element.strip())

        # Verificar que el texto no es vacío o contiene solo espacio
        if isinstance(text_element, NavigableString) and not isinstance(text_element, Comment):
            original_text = text_element.strip()
            # if len(original_text) == 0:
            #     continue  # Ignorar espacios en blanco

            if "<" in original_text.strip() or ">" in original_text.strip() or len(original_text.strip())  == 0 or "html" == text_element.strip() or "{" in text_element.strip() or "}" in text_element.strip():
                continue

            # text_element.replace_with("+" + text_element.strip())

        # Evitar modificar texto de etiquetas críticas, e.g. 'if' de JS
        # if "<" not in original_text and ">" not in original_text:
            # Añadir un emoji solo si es texto visible
            original_texts.append(original_text)
            text_elements.append(text_element)

    # Translate the text content of the page. Return a dictionary with the original text as the key and the translated text as the value
    translated_texts = translate_batch_parallel(original_texts, src_lang_code='Spanish', tgt_lang_code='Catalan')

    # Replace the original text with the translated text
    for  original_text, translated_text in translated_texts.items():
        for text_element in text_elements:
            if original_text ==  text_element.strip():
                text_element.replace_with(translated_text)

    modified_html = str(soup)
    return Response(modified_html, content_type="text/html")
    return render_template("iframe.html", content=modified_html)


@app.route('/proxy')
@cross_origin()
def proxy():
    global base_url
    url = request.args.get('url')
    base_url = "https://" + urlparse(url).netloc
    target_url = url
    if not target_url:
        return "Por favor, proporciona una URL en el parámetro 'url'.", 400

    return render_template('iframe.html', target=target_url)


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
        print(translations)
        return {"message": "No translations found"}, 404

    for original, translation in translations.items():
        original = original.decode("utf-8")
        translation = translation.decode("utf-8")
        if text in translation:
            return {"originalText": original}, 200

    print(translations)
    return {"message": "No translations found"}, 404



@app.route("/chatbot", methods=["POST"])
def chatbot():
    sentence = request.args.get("sentence")
    response = chatbot_single_sentence(sentence)
    return {"response": response}


@app.route("/tts", methods=["POST"])
def tts():
    sentence = request.args.get("sentence")
    #Take voice args if present
    voice = request.args.get("voice")
    if voice:
        response = tts_single_sentence(sentence, voice)
    else:
        response = tts_single_sentence(sentence)
    return {"response": response}



# @app.route('/<path:filename>')
# allow ALL methods
@app.route("/<path:filename>", methods=["GET", "POST", "PUT", "DELETE"])
def serve_media(filename):
    global base_url
    print("putilla", base_url)
    # Construir la URL completa para el recurso solicitado
    resource_url = urljoin(base_url, filename)

    # Realizar la solicitud para obtener el recurso (imagen, CSS, etc.)
    try:
        print("resource_url", resource_url) 
        resource_response = requests.get(resource_url)
        content_type = resource_response.headers.get("Content-Type")
        return Response(resource_response.content, content_type=content_type, status=resource_response.status_code)
        print(resource_response)
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
    app.run()
