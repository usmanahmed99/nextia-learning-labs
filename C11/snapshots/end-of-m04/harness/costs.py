"""Prices per million tokens, as checked on the provider's price page. Check the current price page:
prices change. An unknown model has no price (None), never a price of 0."""

PRICES_CHECKED = "2026-10-08"
PRICES = {  # model -> (US$ per million input tokens, US$ per million output tokens)
    "chat-small": (0.10, 0.50),    # gpt-6-luna on Azure
    "chat-strong": (2.00, 10.00),  # gpt-6.1-sol on Azure
}


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> float | None:
    if model not in PRICES:
        return None
    price_in, price_out = PRICES[model]
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000
