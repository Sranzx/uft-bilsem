import json
import requests
from typing import List, Generator, Optional
from dataclasses import dataclass


class Config:
    OLLAMA_URL = "http://localhost:11434"
    DEFAULT_MODEL = "gemma3"
    TIMEOUT = 60


@dataclass
class AIModel:
    name: str
    available: bool = True


class AIService:
    def __init__(self):
        self.provider = "Ollama"
        self.model = Config.DEFAULT_MODEL
        self.api_key: Optional[str] = None

    def configure(self, provider: str, model: str, api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def check_connection(self) -> bool:
        if self.provider == "Ollama":
            try:
                r = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=3)
                return r.status_code == 200
            except Exception:
                return False
        return True

    def get_available_models(self) -> List[str]:
        if self.provider != "Ollama":
            return [self.model]
        try:
            r = requests.get(f"{Config.OLLAMA_URL}/api/tags", timeout=2)
            if r.status_code == 200:
                models = [m['name'] for m in r.json().get('models', [])]
                return models if models else [Config.DEFAULT_MODEL]
            return [Config.DEFAULT_MODEL]
        except Exception:
            return [Config.DEFAULT_MODEL]

    def generate_stream(self, prompt: str, system_prompt: str) -> Generator[str, None, None]:
        full_prompt = f"{system_prompt}\n\nVERİLER:\n{prompt}"
        try:
            if self.provider == "Ollama":
                yield from self._stream_ollama(full_prompt)
            else:
                yield f"Hata: {self.provider} desteklenmiyor."
        except Exception as e:
            yield f"Hata: {e}"

    def _stream_ollama(self, prompt: str) -> Generator[str, None, None]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.7}
        }
        try:
            with requests.post(
                f"{Config.OLLAMA_URL}/api/generate",
                json=payload,
                stream=True,
                timeout=Config.TIMEOUT
            ) as r:
                if r.status_code == 200:
                    for line in r.iter_lines():
                        if line:
                            try:
                                body = json.loads(line)
                                text = body.get('response', '')
                                if text:
                                    yield text
                            except json.JSONDecodeError:
                                continue
                else:
                    yield f"API Hatası: {r.status_code}"
        except requests.exceptions.ConnectionError:
            yield "Ollama bağlantısı kurulamadı. 'ollama serve' çalıştırın."
        except Exception as e:
            yield f"Bağlantı Hatası: {str(e)}"
