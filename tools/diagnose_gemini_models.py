import os
import sys
from dotenv import load_dotenv

load_dotenv('.env')

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print('API_KEY_PRESENT=False')
    sys.exit(0)

print('API_KEY_PRESENT=True')

try:
    from google import genai
except Exception as exc:
    print('IMPORT_ERROR', type(exc).__name__, exc)
    sys.exit(1)

client = genai.Client(api_key=api_key)
print('CLIENT_OK', type(client).__name__)

candidate_models = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
]

try:
    available_models = client.models.list()
except Exception as exc:
    print('MODELS_LIST_ERROR', type(exc).__name__, exc)
    sys.exit(1)

listed_names = {
    getattr(model, 'name', None) or getattr(model, 'model', None)
    for model in available_models
    if getattr(model, 'name', None) or getattr(model, 'model', None)
}

for model_name in candidate_models:
    if model_name not in listed_names:
        print(f'{model_name}|SKIP|not-listed')
        continue

    try:
        response = client.models.generate_content(
            model=model_name,
            contents='Reply with the single word OK.',
        )
        text = getattr(response, 'text', None) or getattr(response, 'output_text', None) or ''
        if 'ok' in str(text).strip().lower():
            print(f'{model_name}|SUCCESS|ok')
        else:
            print(f'{model_name}|SUCCESS|unexpected-text:{text}')
    except Exception as exc:
        message = str(exc)
        if '429' in message or 'RESOURCE_EXHAUSTED' in message or 'quota' in message.lower() or 'limit: 0' in message.lower():
            print(f'{model_name}|429|quota-exhausted')
        elif '404' in message or 'NOT_FOUND' in message or 'not found' in message.lower():
            print(f'{model_name}|404|not-found')
        else:
            print(f'{model_name}|ERROR|{type(exc).__name__}:{message}')
