"""Расчёт рекомендованной цены на основе предложений конкурентов (ТОЛЬКООПТ).

Python 3.10+, только стандартная библиотека.
Запуск примера: python starter.py
"""

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal, ROUND_DOWN
from typing import Any

OWN_SELLER = "myshop"
MAX_DELIVERY_DAYS = 6
UNDERCUT_FACTOR = Decimal("0.985")
MAX_AUTO_DEVIATION_RATIO = Decimal("0.30")
CENT = Decimal("0.01")


def _extract_competitor_prices(offers: list[dict[str, Any]]) -> list[Decimal]:
    """Вернуть цены подходящих конкурентов (не MYSHOP и доставка <= 6 дней)."""
    prices: list[Decimal] = []
    for offer in offers:
        seller = offer["seller"].strip().casefold()
        delivery_days = offer["delivery_days"]
        if seller == OWN_SELLER:
            continue
        if delivery_days is None or delivery_days > MAX_DELIVERY_DAYS:
            continue
        prices.append(offer["price"])
    return prices


def _hold(current_price: Decimal, reason: str) -> dict[str, Any]:
    """Сформировать ответ HOLD с сохранением текущей цены."""
    return {"price": current_price, "decision": "HOLD", "reason": reason}


async def recommend_price(
    fetch_offers: Callable[[], Awaitable[dict[str, Any]]],
    current_price: Decimal,
    min_price: Decimal,
    timeout_s: float = 2.0,
) -> dict[str, Any]:
    """Рассчитать рекомендуемую цену и решение (APPLY / REVIEW / HOLD) по правилам прайсинга."""
    try:
        result = await asyncio.wait_for(fetch_offers(), timeout=timeout_s)
    except TimeoutError:
        return _hold(current_price, f"Тайм-аут источника предложений ({timeout_s} с)")
    except Exception as exc:
        return _hold(current_price, f"Ошибка источника предложений: {type(exc).__name__}")

    if result.get("status") != "success":
        status = result.get("status")
        return _hold(current_price, f"Неполный или ошибочный ответ источника: status={status!r}")

    competitor_prices = _extract_competitor_prices(result.get("offers", []))
    if not competitor_prices:
        return _hold(current_price, "Нет подходящих предложений конкурентов")

    target_price = (min(competitor_prices) * UNDERCUT_FACTOR).quantize(CENT, rounding=ROUND_DOWN)
    recommended_price = max(target_price, min_price)

    deviation = abs(recommended_price - current_price)
    if deviation > current_price * MAX_AUTO_DEVIATION_RATIO:
        return {
            "price": recommended_price,
            "decision": "REVIEW",
            "reason": "Изменение цены превышает 30% от текущей, требуется ручная проверка",
        }

    return {
        "price": recommended_price,
        "decision": "APPLY",
        "reason": "Рассчитано по минимальному предложению конкурента с учётом правил",
    }


async def sample_fetch_offers() -> dict[str, Any]:
    return {
        "status": "success",
        "offers": [
            {"seller": "myshop", "price": Decimal("4300.00"), "delivery_days": 2},
            {"seller": "PARTS", "price": Decimal("4800.00"), "delivery_days": 3},
            {"seller": "SLOW", "price": Decimal("4700.00"), "delivery_days": 8},
        ],
    }


if __name__ == "__main__":
    print(
        asyncio.run(
            recommend_price(
                sample_fetch_offers,
                current_price=Decimal("4900.00"),
                min_price=Decimal("4500.00"),
            )
        )
    )
