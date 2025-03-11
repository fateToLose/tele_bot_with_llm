import logging

logger = logging.getLogger(__name__)


def count_token(text: str) -> int | None:
    if text:
        return int(len(text.split()) * 1.3)


def count_pricing(model_pricing: dict, model_id: str, input_tokens: int, output_tokens: int) -> float | None:
    input_cost: float = model_pricing[model_id]["input_cost"] * input_tokens
    output_cost: float = model_pricing[model_id]["output_cost"] * output_tokens

    return input_cost + output_cost
