"""Prices of the AI provider's models, to estimate what each task costs.

Prices change: check them on the provider's price page before you use the numbers.
"""

PRICES_CHECKED = "2026-10-08"
# US dollars per 1 million tokens: (input, output).
PRICES = {
    "chat-small": (0.10, 0.50),
    "embed-small": (0.02, 0.0),
}


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> float | None:
    """The cost of one call, or None for a model without a price."""
    price = PRICES.get(model)
    if price is None:
        return None
    return round((tokens_in * price[0] + tokens_out * price[1]) / 1_000_000, 8)
