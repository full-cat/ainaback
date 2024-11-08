# pip install torch transformers python-dotenv requests
import requests
from transformers import AutoTokenizer, AutoModelForCausalLM
import os

HF_TOKEN = "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"
TRANSLATION_URL = "https://o9vasr2oal4oyt2j.us-east-1.aws.endpoints.huggingface.cloud"
CHATBOT_URL = "https://hijbc1ux6ie03ouo.us-east-1.aws.endpoints.huggingface.cloud"


def translate(sentence, src_lang_code="Español", tgt_lang_code="Catalan"):

    # Detectar el idioma de origen si no se proporciona
    '''
    if not src_lang_code:
        try:
            src_lang_code = detect(sentence)
            print(f"Idioma detectado: {src_lang_code}")
        except Exception as e:
            return
    '''
    if not src_lang_code or not tgt_lang_code or not sentence:
        return 'input error'

    headers = {
        "Accept" : "application/json",
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    prompt = f'[{src_lang_code}] {sentence} \n[{tgt_lang_code}]'
    parameters = {"max_tokens": 1000, "temperature": 0.001}
    payload = { "inputs": prompt, "parameters": parameters }

    try:

        text = requests.post(TRANSLATION_URL + "/generate", headers=headers, json=payload)
        return text.json()["generated_text"]
    except Exception as e:
        return 'Inference error'
