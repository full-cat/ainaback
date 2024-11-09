from flask import Flask, jsonify, request, Response, render_template
import requests
import redis
import time
from bs4 import BeautifulSoup, Comment, NavigableString
from urllib.parse import urljoin
from urllib.parse import urlparse
from flask_cors import CORS
import json

from inference import translate_batch_parallel, chatbot_single_sentence, tts_single_sentence, speech_recognition_single_audio

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
        time.sleep(5)
        page_source = driver.page_source
        return page_source
    finally:
        driver.quit()


brave_key = 'BSAnLBXo1M0ViAYxmnpWZwbUsLJ0hiR'
search_url = 'https://api.search.brave.com/res/v1/web/search'


@app.route('/search')
def search():
    query = request.args.get('q')
    headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'X-Subscription-Token': brave_key
    }
    response = requests.get(search_url, params={'q': query}, headers=headers)
    # load the response from the file
    # with open('calamar.json', 'r') as file:
    #     response = file.read()
    #parse the response to json
    response = response.json()
    texts_title = [result['title'] for result in response['web']['results']]
    # print(texts_title)
    texts_description = [result['description'] for result in response['web']['results']]
    # print(texts_description)
    translated_texts_title = translate_batch_parallel(texts_title, src_lang_code='Spanish', tgt_lang_code='Catalan')
    translated_texts_description = translate_batch_parallel(texts_description, src_lang_code='Spanish', tgt_lang_code='Catalan')
    print(translated_texts_title)
    print(translated_texts_description)
    for original_title, translated_title in translated_texts_title.items():
        for result in response['web']['results']:
            if result['title'] == original_title:
                result['title'] = translated_title
    for original_description, translated_description in translated_texts_description.items():
        for result in response['web']['results']:
            if result['description'] == original_description:
                result['description'] = translated_description
    return response


@app.route("/proxy", methods=["GET"])
def proxy():
    global base_url
    target_url = request.args.get("url")
    base_url = "https://" + urlparse(target_url).netloc
    if not target_url:
        return "URL no proporcionada", 400

    # target_content = get_content_selenium(target_url)
    target_content = get_content_requests(target_url)

    soup = BeautifulSoup(target_content, "html.parser")

    original_texts = []
    text_elements = []
    for text_element in soup.find_all(string=True):
        if isinstance(text_element, NavigableString) and not isinstance(text_element, Comment):
            original_text = text_element.strip()
            # Filter out empty strings and HTML tags
            if ("<" in original_text 
                or ">" in original_text 
                or len(original_text) == 0 
                or "html" == text_element
                or "{" in text_element 
                or "}" in text_element):
                    continue
            text_elements.append(text_element)
            original_texts.append(original_text)


    cached_translations = {}
    texts_to_translate = []

    for text in original_texts:
        if translated_text := r.hget(target_url, text):
            translated_text = translated_text.decode("utf-8")
            print(f"{original_text} -> {translated_text} (cached)")
            cached_translations[text] = translated_text
        else:
            print(f"{text} (not cached)")
            texts_to_translate.append(text)

    # Translate the text content of the page. Return a dictionary with the original text as the key and the translated text as the value
    # print(texts_to_translate)
    translated_texts = translate_batch_parallel(texts_to_translate, src_lang_code="Spanish", tgt_lang_code="Catalan")
    # translated_texts = {k: k + "🔥" for k in texts_to_translate}

    for original_text, translated_text in translated_texts.items():
        r.hset(target_url, original_text, translated_text)
    
    # print(translated_texts)
    translated_texts.update(cached_translations)

    # Reemplazar el texto original con el texto traducido
    for  original_text, translated_text in translated_texts.items():
        for text_element in text_elements:
            if original_text ==  text_element.strip():
                text_element.replace_with(translated_text)

    # Reemplazar todos los enlaces en el HTML
    for link in soup.find_all("a"):
        if link.get("href") is None:
            continue
        stem = target_url if link.get("href").startswith("/") else ""
        if link.get("href"):
            link["href"] = "http://localhost:5000/proxy?url=" + stem + link["href"]

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

    return render_template("iframe.html", content=modified_html)


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
            return {"originalText": original, "translatedText": translation}, 200

    print(translations)
    return {"message": "No translations found"}, 404



@app.route("/chatbot", methods=["GET"])
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

# content type audio/wav
@app.route("/speech_recognition", methods=["POST"])
def speech_recognition():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    response = speech_recognition_single_audio(audio_file)
    print(response)
    response = response.split(":")[1].replace('"', '').replace("}", "")
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
    # r.flushall()
    app.run()
