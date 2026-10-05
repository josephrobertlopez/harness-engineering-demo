"""Discount rules."""


# implements: AC-1
def apply_discount(price: float) -> float:
    if price >= 100:
        return price * 0.9
    return price


# implements: AC-2
def validate_price(price: float) -> float:
    if price < 0:
        raise ValueError("negative price")
    return price
