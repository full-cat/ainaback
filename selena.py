from flask import Flask, request, Response
import requests
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup, Comment, NavigableString
from urllib.parse import urljoin
from urllib.parse import urlparse
import time
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from inference import translate_batch_parallel
import json  # Importar json para serializar datos
import redis

app = Flask(__name__)

# Configuración de Selenium para usar Chrome en modo headless (sin abrir la ventana)
def get_selenium_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Modo sin ventana
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

@app.route('/proxy')
def proxy():
    # Obtener la URL de la solicitud
    global base_url
    url = request.args.get('url')
    base_url = "https://" + urlparse(url).netloc
    target_url = url
    if not target_url:
        return "Por favor, proporciona una URL en el parámetro 'url'.", 400

    driver = get_selenium_driver()
    try:
        # Cargar la página con Selenium
        driver.get(target_url)
        time.sleep(5)  # Esperar a que el contenido dinámico se cargue

        # Obtener el HTML completo con el contenido dinámico
        page_source = driver.page_source

        # Procesar el HTML con BeautifulSoup
        soup = BeautifulSoup(page_source, "html.parser")
        
        original_texts = []

        for text_element in soup.find_all(string=True):
            if isinstance(text_element, NavigableString) and not isinstance(text_element, Comment):
                original_text = text_element.strip()
                # Filter out empty strings and HTML tags
                if "<" in original_text or ">" in original_text or len(original_text) == 0 or original_text.lower() == "html":
                    continue
                # Add the original text to the list
                original_texts.append(original_text)

        # Translate the text content of the page. Return a dictionary with the original text as the key and the translated text as the value
        translated_texts = translate_batch_parallel(original_texts, src_lang_code='English', tgt_lang_code='Euskera')

        # Reemplazar el texto original con el texto traducido
        for original_text, translated_text in translated_texts.items():
            for text_element in soup.find_all(string=True):
                if original_text in text_element:
                    text_element.replace_with(translated_text)

        # Reemplazar todos los enlaces en el HTML
        for link in soup.find_all('a'):
            if link.get('href') is None:
                continue
            stem = url if link.get('href').startswith("/") else ""
            if link.get('href'):
                link['href'] = "http://localhost:5000/proxy?url=" + stem + link['href']

        # Obtener el HTML modificado
        modified_html = str(soup)

        # Convertir el diccionario de traducciones a JSON
        translation_data = {
            "original_texts": original_texts,
            "translated_texts": translated_texts
        }

        # Subir el diccionario de traducciones a Redis con el formato [clave, valor]
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.set(target_url, json.dumps(translation_data))

        return Response(modified_html, content_type='text/html')
    
    finally:
        driver.quit()  # Cierra el navegador de Selenium después de la solicitud

# Ruta para manejar recursos estáticos
@app.route('/<path:filename>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def serve_media(filename):
    global base_url

    # Construir la URL completa para el recurso solicitado
    resource_url = urljoin(base_url, filename)
    
    # Realizar la solicitud para obtener el recurso (imagen, CSS, etc.)
    try:
        resource_response = requests.get(resource_url)
        if resource_response.status_code == 200:
            content_type = resource_response.headers.get('Content-Type')
            return Response(resource_response.content, content_type=content_type)
        else:
            return "Resource not found", 404
    except requests.exceptions.RequestException as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
