# pip install torch transformers python-dotenv requests
import requests
from transformers import AutoTokenizer, AutoModelForCausalLM
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from langdetect import detect


HF_TOKEN = "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"
TRANSLATION_URL = "https://o9vasr2oal4oyt2j.us-east-1.aws.endpoints.huggingface.cloud"
CHATBOT_URL = "https://hijbc1ux6ie03ouo.us-east-1.aws.endpoints.huggingface.cloud"
TTL_URL = "https://x6g02u4lkf25gcjo.us-east-1.aws.endpoints.huggingface.cloud/api/tts"



# A dictionary for translating languages from codes to names
LanguageCodes = {
    'ca': 'Catalan', 'it': 'Italian', 'pt': 'Portuguese', 'de': 'German', 'en': 'English', 'es': 'Spanish',
    'eu': 'Euskera', 'gl': 'Galician', 'fr': 'French', 'bg': 'Bulgarian', 'cs': 'Czech', 'lt': 'Lithuanian',
    'hr': 'Croatian', 'nl': 'Dutch', 'ro': 'Romanian', 'da': 'Danish', 'el': 'Greek', 'fi': 'Finnish',
    'hu': 'Hungarian', 'sk': 'Slovak', 'sl': 'Slovenian', 'et': 'Estonian', 'pl': 'Polish', 'lv': 'Latvian',
    'sv': 'Swedish', 'mt': 'Maltese', 'ga': 'Irish', 'an': 'Aragonese', 'ast': 'Asturian'
}


def detect_language(sentence):
    """
    This function detects the language of a sentence
    """
    language_code = detect(sentence)
    return LanguageCodes.get(language_code, "English")



## TRANSLATION RELATED FUNCTIONS

def translate_single_sentence(sentence, src_lang_code, tgt_lang_code):
    """
    This function translates a single sentence from the source language to the target language
    """

    print("source language code: ", src_lang_code)

    # If there is no source language code or it is None, try to detect the language
    if not src_lang_code or src_lang_code == "None":
        src_lang_code = detect_language(sentence)
    # Language detection fails sometimes
    #print(f"Translating from {src_lang_code} to {tgt_lang_code}")

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    

    # Generate the prompt and payload for the individual translation request
    prompt = f'[{src_lang_code}] {sentence} \n[{tgt_lang_code}]'
    payload = {"inputs": prompt, "parameters": {"max_tokens": 1000, "temperature": 0.001}}
    

    try:
        # Make the HTTP request for the translation
        response = requests.post(TRANSLATION_URL + "/generate", headers=headers, json=payload, timeout=5)  # Set a timeout
        response.raise_for_status()  # Raise an exception for non-200 status codes
        return response.json()["generated_text"]
    except requests.exceptions.RequestException as e:
        print(f"Error translating sentence '{sentence}': {e}")  # Log the error with details
        return f"Error translating: {e}"




def translate_batch(sentences, src_lang_code=None, tgt_lang_code='Catalan'):
    """
    This function translates a batch of sentences sequentially
    """

    print("source language code: ", src_lang_code)
    if not sentences or not tgt_lang_code:
        return 

    translations = {}

    start_time = time.time()
    for sentence in sentences:
        translation = translate_single_sentence(sentence, src_lang_code, tgt_lang_code)
        translations[sentence] = translation
    
    print(f"Translated {len(sentences)} sentences in {time.time() - start_time:.2f} seconds")

    return translations



def translate_batch_parallel(sentences, src_lang_code=None, tgt_lang_code='Catalan'):
    if not sentences or not tgt_lang_code:
        return {}
    
    translations = {}
    start_time = time.time()

    with ThreadPoolExecutor() as executor:
        # Submit each sentence to be translated in a separate thread
        future_to_sentence = {executor.submit(translate_single_sentence, sentence, src_lang_code, tgt_lang_code): sentence for sentence in sentences}
        
        # Collect the results as they complete
        for future in as_completed(future_to_sentence):
            sentence = future_to_sentence[future]
            translations[sentence] = future.result()
    
    print(f"Translated {len(sentences)} sentences in {time.time() - start_time:.2f} seconds")

    return translations





def train_translation_model(sentences):
    """
    This function receives a dict containing original texts as keys and corrected translated texts as values
    The dict is used to fine tune the model
    """
    # Load the tokenizer and model
    model_id = "BSC-LT/salamandra-7b-instruct-aina-hack"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.bfloat16
    )

    # Prepare the training data
    training_data = []
    for original_text, corrected_text in sentences.items():
        src_lang_code = detect_language(original_text)
        tgt_lang_code = detect_language(corrected_text)
        training_data.append(f"[{src_lang_code}] {original_text} \n[{tgt_lang_code}] {corrected_text}")

    # Tokenize the training data
    tokenized_data = tokenizer(training_data, return_tensors="pt", padding=True, truncation=True)

    # Fine-tune the model
    model.train()

    # Update the model at the endpoint
    # ...




## CHATBOT RELATED FUNCTIONS ##

def chatbot_single_sentence(sentence):
    """
    This function sends a single sentence to the chatbot model and returns the generated response
    """

    if not sentence:
        return "input error"

    model_name = "BSC-LT/salamandra-7b-instruct-aina-hack"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    headers = {
        "Accept" : "application/json",
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    system_prompt = "Respon sempre en cantalan amb respostes el més elaborades i llargues possibles"

    message = [ { "role": "system", "content": system_prompt} ]
    message += [ { "role": "user", "content": sentence } ]
    prompt = tokenizer.apply_chat_template(
        message,
        tokenize=False,
        add_generation_prompt=True,
    )

    payload = {
        "inputs": prompt,
        "parameters": {"max_tokens": 1000, "temperature": 0.5}
    }

    try:
        response = requests.post(CHATBOT_URL + "/generate", headers=headers, json=payload, timeout=5)
        response.raise_for_status()
        return response.json()["generated_text"]
    except requests.exceptions.RequestException as e:
        print(f"Error generating chatbot response for sentence '{sentence}': {e}")
        return f"Error generating chatbot response: {e}"



## TTS RELATED FUNCTIONS ##
def tts_single_sentence(sentence, voice=25):
    """
    This function sends a single sentence to the TTS model and returns the generated audio
    """

    if not sentence:
        return "input error"

    headers = { "Authorization": f"Bearer {HF_TOKEN}",}

    data = {"text": sentence, "voice": voice}

    try:
        response = requests.post(TTL_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error generating TTS response for sentence '{sentence}': {e}")
        return f"Error generating TTS response: {e}"
