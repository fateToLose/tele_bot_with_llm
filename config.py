import os

# Directory #
BASE_PATH: str = os.getcwd()
LOG_PATH = os.path.join(BASE_PATH, "logs")
DB_PATH = os.path.join(BASE_PATH, "data")
QUERY_PATH = os.path.join(BASE_PATH, "query")

DB_MASTER_FPATH = os.path.join(DB_PATH, "master.db")


# Model Configuration
MAX_TOKENS = 2048


# LLM Models
MODEL_CHOICES: dict = {
    "Claude": [
        {
            "name": "Claude 3.7 (Sonnet)",
            "id": "claude-3-7-sonnet-20250219",
        },
        {
            "name": "Claude 3.5 (Haiku)",
            "id": "claude-3-5-haiku-20241022",
        },
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
        {
            "name": "GPT-4o-mini",
            "id": "gpt-4o-mini",
        },
    ],
    "Perplexity": [
        {
            "name": "Sonar Deep Research",
            "id": "sonar-deep-research",
        },
        {
            "name": "Sonar",
            "id": "sonar",
        },
    ],
}


MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-3-7-sonnet-20250219": {
        "input_cost": 0.000003,
        "output_cost": 0.000015,
    },
    "claude-3-5-haiku-20241022": {
        "input_cost": 0.0000008,
        "output_cost": 0.000004,
    },
    "deepseek-reasoner": {
        "input_cost": 0.00000014,
        "output_cost": 0.00000219,
    },
    "deepseek-chat": {
        "input_cost": 0.00000007,
        "output_cost": 0.0000011,
    },
    "gpt-4o": {
        "input_cost": 0.0000025,
        "output_cost": 0.00001,
    },
    "gpt-4o-mini": {
        "input_cost": 0.00000015,
        "output_cost": 0.0000006,
    },
    "sonar-deep-research": {
        "input_cost": 0.0000005,
        "output_cost": 0.000002,
        "search_cost": 0.005,
    },
    "sonar": {
        "input_cost": 0.000001,
        "output_cost": 0.000001,
        "search_cost": 0.005,
    },
}
