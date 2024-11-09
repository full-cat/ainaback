# pip install torch transformers python-dotenv requests
import requests
from transformers import AutoTokenizer, AutoModelForCausalLM
import os
from concurrent.futures import ThreadPoolExecutor, as_completed



HF_TOKEN = "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"
TRANSLATION_URL = "https://o9vasr2oal4oyt2j.us-east-1.aws.endpoints.huggingface.cloud"
CHATBOT_URL = "https://hijbc1ux6ie03ouo.us-east-1.aws.endpoints.huggingface.cloud"

# A dictionary for translating languages from codes to names
LanguageCodes = {
    'ca': 'Catalan', 'it': 'Italian', 'pt': 'Portuguese', 'de': 'German', 'en': 'English', 'es': 'Spanish',
    'eu': 'Euskera', 'gl': 'Galician', 'fr': 'French', 'bg': 'Bulgarian', 'cs': 'Czech', 'lt': 'Lithuanian',
    'hr': 'Croatian', 'nl': 'Dutch', 'ro': 'Romanian', 'da': 'Danish', 'el': 'Greek', 'fi': 'Finnish',
    'hu': 'Hungarian', 'sk': 'Slovak', 'sl': 'Slovenian', 'et': 'Estonian', 'pl': 'Polish', 'lv': 'Latvian',
    'sv': 'Swedish', 'mt': 'Maltese', 'ga': 'Irish', 'an': 'Aragonese', 'ast': 'Asturian'
}


def translate_sentence(sentence, src_lang_code, tgt_lang_code):

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    

    # Generate the prompt and payload for the individual translation request
    prompt = f'[{src_lang_code}] {sentence} \n[{tgt_lang_code}]'
    payload = {"inputs": prompt, "parameters": {}}
    

    try:
        # Make the HTTP request for the translation
        response = requests.post(TRANSLATION_URL + "/generate", headers=headers, json=payload, timeout=5)  # Set a timeout
        response.raise_for_status()  # Raise an exception for non-200 status codes
        return response.json()["generated_text"]
    except requests.exceptions.RequestException as e:
        print(f"Error translating sentence '{sentence}': {e}")  # Log the error with details
        return f"Error translating: {e}"






def translate_batch(sentences, src_lang_code='English', tgt_lang_code='Catalan'):
    if not sentences or not src_lang_code or not tgt_lang_code:
        return ['input error'] * len(sentences)

    translations = []
    for sentence in sentences:
        translation = translate(sentence, src_lang_code, tgt_lang_code)
        translations.append(translation)
    
    return translations



def translate_batch_parallel(sentences, src_lang_code='English', tgt_lang_code='Catalan'):
    if not sentences or not src_lang_code or not tgt_lang_code:
        return {}
    
    translations = {}
    with ThreadPoolExecutor() as executor:
        # Submit each sentence to be translated in a separate thread
        future_to_sentence = {executor.submit(translate_sentence, sentence, src_lang_code, tgt_lang_code): sentence for sentence in sentences}
        
        # Collect the results as they complete
        for future in as_completed(future_to_sentence):
            sentence = future_to_sentence[future]
            translations[sentence] = future.result()
    
    return translations




# This option is limited to batch sizes of 4 sentences
def translate_batch_openai(sentences, src_lang_code='Spanish', tgt_lang_code='Catalan'):

    # Lazy import to avoid loading the library when not needed
    from openai import OpenAI

    if not sentences or not src_lang_code or not tgt_lang_code:
        return ['input error'] * len(sentences)

    prompts = [f'[{src_lang_code}] {sentence} \n[{tgt_lang_code}]: ' for sentence in sentences]

    print('Prompts:', prompts)

    try:
        chat_completion = translation_client.completions.create(
            model="tgi",
            prompt=prompts,
            stream=False,
            max_tokens=1000,
            temperature=0.00,

        )
        ordered_translations = sorted(chat_completion.choices, key=lambda choice: choice.index)
        translations = [choice.text for choice in ordered_translations]
        print(translations)
        return translations
    except Exception as e:
        print(f"Error during translation: {e}")
        return ['Inference error'] * len(sentences)