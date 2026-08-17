import logging
import os

logger = logging.getLogger('cold_email_agent')


class AIProvider:
    def complete(self, prompt, model, max_tokens, temperature):
        raise NotImplementedError

    def test_connection(self, model):
        raise NotImplementedError


class AnthropicProvider(AIProvider):
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = None
        if self.api_key:
            try:
                import anthropic

                self.client = anthropic.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning('Anthropic client unavailable: %s', exc)

    def complete(self, prompt, model, max_tokens, temperature):
        if not self.client:
            return ''
        try:
            if hasattr(self.client, 'responses'):
                response = self.client.responses.create(
                    model=model,
                    input=prompt,
                    max_tokens_to_sample=max_tokens,
                )
                return response.output[0].contents[0].text
            if hasattr(self.client, 'completions'):
                response = self.client.completions.create(
                    model=model,
                    prompt=prompt,
                    max_tokens_to_sample=max_tokens,
                )
                return getattr(response, 'completion', '')
            if hasattr(self.client, 'messages'):
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                return response.content[0].text
        except Exception as exc:
            logger.warning('Anthropic completion failed: %s', exc)
        return ''

    def test_connection(self, model):
        if not self.client:
            raise RuntimeError('API key missing or SDK unavailable')
        try:
            if hasattr(self.client, 'messages'):
                self.client.messages.create(
                    model=model, max_tokens=1, messages=[{'role': 'user', 'content': 'ping'}]
                )
            elif hasattr(self.client, 'responses'):
                self.client.responses.create(model=model, input='ping', max_tokens_to_sample=1)
            else:
                raise RuntimeError('Unsupported Anthropic SDK version')
        except Exception as exc:
            raise RuntimeError(f'Connection failed: {exc}')
        return True


class OpenAIProvider(AIProvider):
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = (base_url or os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')

    def complete(self, prompt, model, max_tokens, temperature):
        if not self.api_key:
            return ''
        try:
            import httpx

            response = httpx.post(
                f'{self.base_url}/chat/completions',
                headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': max_tokens,
                    'temperature': temperature,
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except Exception as exc:
            logger.warning('OpenAI-compatible completion failed: %s', exc)
        return ''

    def test_connection(self, model):
        if not self.api_key:
            raise RuntimeError('API key missing')
        try:
            import httpx

            response = httpx.post(
                f'{self.base_url}/chat/completions',
                headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': 'ping'}],
                    'max_tokens': 1,
                },
                timeout=30,
            )
            response.raise_for_status()
        except Exception as exc:
            raise RuntimeError(f'Connection failed: {exc}')
        return True


class GeminiProvider(AIProvider):
    BASE = 'https://generativelanguage.googleapis.com/v1beta'

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

    def complete(self, prompt, model, max_tokens, temperature):
        if not self.api_key:
            return ''
        try:
            import httpx

            response = httpx.post(
                f'{self.BASE}/models/{model}:generateContent',
                params={'key': self.api_key},
                json={
                    'contents': [{'parts': [{'text': prompt}]}],
                    'generationConfig': {'temperature': temperature, 'maxOutputTokens': max_tokens},
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        except Exception as exc:
            logger.warning('Gemini completion failed: %s', exc)
        return ''

    def test_connection(self, model):
        if not self.api_key:
            raise RuntimeError('API key missing')
        try:
            import httpx

            response = httpx.post(
                f'{self.BASE}/models/{model}:generateContent',
                params={'key': self.api_key},
                json={'contents': [{'parts': [{'text': 'ping'}]}], 'generationConfig': {'maxOutputTokens': 1}},
                timeout=30,
            )
            response.raise_for_status()
        except Exception as exc:
            raise RuntimeError(f'Connection failed: {exc}')
        return True


def provider_for(model_row, api_key=None):
    if not model_row:
        return None
    if model_row.provider == 'openai':
        return OpenAIProvider(api_key=api_key or model_row.api_key_encrypted, base_url=model_row.base_url)
    if model_row.provider == 'anthropic':
        return AnthropicProvider(api_key=api_key or model_row.api_key_encrypted)
    if model_row.provider == 'gemini':
        return GeminiProvider(api_key=api_key or model_row.api_key_encrypted)
    return None


def is_managed(model_row):
    return bool(model_row) and model_row.provider == 'managed'