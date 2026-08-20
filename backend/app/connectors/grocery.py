import random

from .base import Cart, Connector

CATALOG = {
    "milk": {"unit": "1L", "price": 68},
    "eggs": {"unit": "12 pack", "price": 90},
    "bread": {"unit": "loaf", "price": 55},
    "rice": {"unit": "5kg", "price": 420},
    "atta": {"unit": "5kg", "price": 260},
    "onions": {"unit": "1kg", "price": 40},
    "tomatoes": {"unit": "1kg", "price": 45},
    "potatoes": {"unit": "1kg", "price": 35},
    "cooking oil": {"unit": "1L", "price": 165},
    "dal": {"unit": "1kg", "price": 145},
    "paneer": {"unit": "200g", "price": 90},
    "chicken": {"unit": "500g", "price": 160},
    "yogurt": {"unit": "400g", "price": 45},
    "bananas": {"unit": "dozen", "price": 60},
    "apples": {"unit": "1kg", "price": 180},
    "coffee": {"unit": "200g", "price": 220},
    "tea": {"unit": "250g", "price": 150},
    "sugar": {"unit": "1kg", "price": 48},
    "salt": {"unit": "1kg", "price": 22},
    "detergent": {"unit": "1kg", "price": 190},
}

DEFAULT_WEEKLY_BASKET = ["milk", "eggs", "bread", "onions", "tomatoes", "rice", "dal", "cooking oil"]


class GroceryConnector(Connector):
    domain = "grocery"

    def search(self, prefs: dict, slots: dict) -> list[dict]:
        wanted = slots.get("items") or DEFAULT_WEEKLY_BASKET
        preferred_brands = prefs.get("preferred_brands", {})
        results = []
        for name in wanted:
            key = name.lower().strip()
            catalog_entry = CATALOG.get(key, {"unit": "1 unit", "price": 99})
            brand = preferred_brands.get(key)
            results.append({
                "item": key,
                "brand": brand or "store brand",
                "unit": catalog_entry["unit"],
                "price": catalog_entry["price"],
                "in_stock": True,
            })
        return results

    def quote(self, prefs: dict, slots: dict) -> Cart:
        provider = prefs.get("preferred_app", "BigBasket (default)")
        options = self.search(prefs, slots)
        items = [
            {
                "item": o["item"],
                "brand": o["brand"],
                "qty": f"1 x {o['unit']}",
                "price": o["price"],
            }
            for o in options
        ]
        total = round(sum(i["price"] for i in items), 2)
        budget = prefs.get("budget_cap")
        notes = None
        if budget and total > budget:
            over = total - budget
            notes = (
                f"This basket is ₹{over:.0f} over your ₹{budget:.0f} weekly budget. "
                f"Suggest removing/substituting an item before approving."
            )
        return Cart(
            title=f"Weekly grocery order via {provider}",
            items=items,
            total=total,
            notes=notes,
        )

    def execute(self, prefs: dict, slots: dict, cart: Cart) -> dict:
        rnd = random.Random(cart.total)
        eta_minutes = rnd.randint(45, 150)
        return {
            "provider": prefs.get("preferred_app", "BigBasket (default)"),
            "order_id": f"GRC-{rnd.randint(100000, 999999)}",
            "eta_minutes": eta_minutes,
            "status": "placed",
        }
