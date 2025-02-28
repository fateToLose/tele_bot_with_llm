import os

# Directory #
BASE_PATH: str = os.getcwd()

# Model Configuration
MAX_TOKENS = 2048

# LLM Models
MODEL_CHOICES: dict[str, list[dict[str, str]]] = {
    "Claude": [
        {"name": "Claude 3.7 (Sonnet)", "id": "claude-3-7-sonnet-20250219"},
        {"name": "Claude 3.5 (Haiku)", "id": "claude-3-5-haiku-20241022"},
    ],
    "Deepseek": [
        {
            "name": "Deepseek R1",
            "id": "deepseek-reasoner",
        },
        {
            "name": "Deepseek V3",
            "id": "deepseek-chat",
        },
    ],
    "ChatGPT": [
        {
            "name": "GPT-4o",
            "id": "gpt-4o",
        },
        {"name": "GPT-4o-mini", "id": "gpt-4o-mini"},
    ],
}
