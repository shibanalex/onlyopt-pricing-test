"""Автоматические тесты для recommend_price (только стандартная библиотека)."""

import asyncio
from decimal import Decimal
import unittest

from starter import recommend_price, sample_fetch_offers


class RecommendPriceTests(unittest.IsolatedAsyncioTestCase):
    async def test_sample_calculation_applies_rules(self) -> None:
        res = await recommend_price(
            sample_fetch_offers,
            current_price=Decimal("4900.00"),
            min_price=Decimal("4500.00"),
        )
        self.assertEqual(res["price"], Decimal("4728.00"))
        self.assertEqual(res["decision"], "APPLY")
        self.assertIsInstance(res["reason"], str)

    async def test_timeout_and_error_statuses_return_hold(self) -> None:
        async def slow_fetch():
            await asyncio.sleep(0.2)
            return {"status": "success", "offers": []}

        res_timeout = await recommend_price(
            slow_fetch,
            current_price=Decimal("1200.00"),
            min_price=Decimal("1500.00"),
            timeout_s=0.02,
        )
        self.assertEqual(res_timeout["price"], Decimal("1200.00"))
        self.assertEqual(res_timeout["decision"], "HOLD")

        async def broken_fetch():
            raise ConnectionError("network down")

        res_err = await recommend_price(
            broken_fetch,
            current_price=Decimal("1200.00"),
            min_price=Decimal("1000.00"),
        )
        self.assertEqual(res_err["price"], Decimal("1200.00"))
        self.assertEqual(res_err["decision"], "HOLD")

        async def partial_fetch():
            return {
                "status": "partial",
                "offers": [{"seller": "COMP", "price": Decimal("1000.00"), "delivery_days": 1}],
            }

        res_partial = await recommend_price(
            partial_fetch,
            current_price=Decimal("1200.00"),
            min_price=Decimal("1000.00"),
        )
        self.assertEqual(res_partial["price"], Decimal("1200.00"))
        self.assertEqual(res_partial["decision"], "HOLD")

    async def test_filtering_own_shop_and_delivery_returns_hold_below_min_price(self) -> None:
        async def filtered_out_fetch():
            return {
                "status": "success",
                "offers": [
                    {"seller": "MYSHOP", "price": Decimal("900.00"), "delivery_days": 1},
                    {"seller": "MyShop", "price": Decimal("950.00"), "delivery_days": 0},
                    {"seller": "UNKNOWN", "price": Decimal("800.00"), "delivery_days": None},
                    {"seller": "TOOLONG", "price": Decimal("700.00"), "delivery_days": 7},
                ],
            }

        res = await recommend_price(
            filtered_out_fetch,
            current_price=Decimal("1000.00"),
            min_price=Decimal("1500.00"),
        )
        self.assertEqual(res["price"], Decimal("1000.00"))
        self.assertEqual(res["decision"], "HOLD")

    async def test_rounding_down_and_min_price_clamp(self) -> None:
        async def odd_price_fetch():
            return {
                "status": "success",
                "offers": [
                    {"seller": "C1", "price": Decimal("1000.01"), "delivery_days": 6},
                ],
            }

        res_round = await recommend_price(
            odd_price_fetch,
            current_price=Decimal("1000.00"),
            min_price=Decimal("900.00"),
        )
        self.assertEqual(res_round["price"], Decimal("985.00"))
        self.assertEqual(res_round["decision"], "APPLY")

        res_clamp = await recommend_price(
            odd_price_fetch,
            current_price=Decimal("1000.00"),
            min_price=Decimal("990.00"),
        )
        self.assertEqual(res_clamp["price"], Decimal("990.00"))
        self.assertEqual(res_clamp["decision"], "APPLY")

    async def test_thirty_percent_boundary_review_vs_apply(self) -> None:
        async def exact_boundary_fetch():
            return {
                "status": "success",
                "offers": [{"seller": "C1", "price": Decimal("800.00"), "delivery_days": 2}],
            }

        res_exact = await recommend_price(
            exact_boundary_fetch,
            current_price=Decimal("1000.00"),
            min_price=Decimal("1300.00"),
        )
        self.assertEqual(res_exact["price"], Decimal("1300.00"))
        self.assertEqual(res_exact["decision"], "APPLY")

        res_over = await recommend_price(
            exact_boundary_fetch,
            current_price=Decimal("1000.00"),
            min_price=Decimal("1300.01"),
        )
        self.assertEqual(res_over["price"], Decimal("1300.01"))
        self.assertEqual(res_over["decision"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
