"""Prices and the usage cap: what a task costs, and the limit that stops a live run that costs too much.

Prices change: check your provider's current price page. These are the prices of the course's
recordings (Azure, US dollars per million tokens, checked when they were recorded).
"""

PRICES_CHECKED = "2026-10-08"
PRICES = {  # model: (input, output) US$ per million tokens
    "chat-small": (0.10, 0.50),     # gpt-6-luna on Azure
    "chat-strong": (2.00, 10.00),   # gpt-6.1-sol on Azure
    "gemma3:4b": (0.0, 0.0),        # local, through Ollama: no price per token
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """The cost of one call, or None for a model without a known price (None is not 0)."""
    if model not in PRICES:
        return None
    price_in, price_out = PRICES[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000
