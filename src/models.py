import requests
import logging
from abc import ABC

from config import MAX_TOKENS

logger = logging.getLogger(__name__)


class BaseModelLLM(ABC):
    def __init__(self, api_key: str | None, model_id: str, model_name: str) -> None:
        self.api_key = api_key
        self.model_id = model_id
        self.model_name = model_name

    async def query(self, message: str | None) -> None:
        raise NotImplementedError("Every model should have their own query functions")


class ClaudeModel(BaseModelLLM):
    def __init__(self, api_key: str | None, model_id: str, model_name: str) -> None:
        super().__init__(api_key, model_id, model_name)

    async def query(self, message: str | None) -> str:
        try:
            headers = {
                "x-api-key": self.api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01",
            }

            data = {
                "model": self.model_id,
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": message}],
            }

            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)

            response_json = response.json()
            return response_json["content"][0]["text"]
        except Exception as e:
            logger.error(f"Error querying Claude API: {e}")
            return f"Error communicating with Claude: {str(e)}"


class DeepseekModel(BaseModelLLM):
    def __init__(self, api_key: str | None, model_id: str, model_name: str) -> None:
        super().__init__(api_key, model_id, model_name)

    async def query(self, message: str | None) -> str:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

            data = {
                "model": self.model_id,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": MAX_TOKENS,
            }

            response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)

            response_json = response.json()
            return response_json["choices"][0]["message"]["content"]
        except Exception as e:
            logging.error(f"Error querying DeepSeek API: {e}")
            return f"Error communicating with DeepSeek: {str(e)}"


class ChatGPTModel(BaseModelLLM):
    def __init__(self, api_key: str | None, model_id: str, model_name: str) -> None:
        super().__init__(api_key, model_id, model_name)

    async def query(self, message: str | None) -> str:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

            data = {
                "model": self.model_id,
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": message}],
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)

            response_json = response.json()
            return response_json["choices"][0]["message"]["content"]
        except Exception as e:
            logging.error(f"Error querying OpenAI API: {e}")
        return f"Error communicating with ChatGPT: {str(e)}"


class AllModels:
    def __init__(self, api_keys: dict[str, str | None], given_models: dict[str, list[dict[str, str]]]) -> None:
        self.api_keys: dict[str, str | None] = api_keys
        self.given_models: dict[str, list[dict[str, str]]] = given_models
        self.reg_models: dict[str, BaseModelLLM] = {}

        self._init_models()

    def _init_models(self):
        claude_models = [
            ClaudeModel(self.api_keys["Claude"], sub_model["id"], sub_model["name"])
            for sub_model in self.given_models["Claude"]
        ]

        deepseek_models = [
            DeepseekModel(self.api_keys["Deepseek"], sub_model["id"], sub_model["name"])
            for sub_model in self.given_models["Deepseek"]
        ]

        ChatGPT_models = [
            ChatGPTModel(self.api_keys["ChatGPT"], sub_model["id"], sub_model["name"])
            for sub_model in self.given_models["ChatGPT"]
        ]

        # Register all models
        for model in claude_models:
            self.register_model("Claude", model)

        for model in deepseek_models:
            self.register_model("Deepseek", model)

        for model in ChatGPT_models:
            self.register_model("ChatGPT", model)

    def register_model(self, provider: str, model: BaseModelLLM):
        model_key = f"{provider}_{model.model_id}"
        self.reg_models[model_key] = model

    def get_model(self, provider: str, model_id: str) -> BaseModelLLM | None:
        model_key = f"{provider}_{model_id}"
        return self.reg_models.get(model_key)

    async def query_model(self, provider: str, model_id: str, message: str) -> str:
        model = self.get_model(provider, model_id)
        if model:
            return await model.query(message)
        else:
            return "Model not found. Please select a valid model."
