"""Pricing."""


# implements: AC-1
def total(prices: list[float]) -> float:
    return sum(prices)


def bulk_rebate(amount: float) -> float:
    if amount > 1000:
        return amount * 0.95
    return amount


def legacy_tax(amount: float) -> float:
    return amount * 1.07
