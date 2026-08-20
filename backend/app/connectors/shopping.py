import random

from .base import Cart, Connector

CATALOG_HINTS = {
    "shampoo": 220, "soap": 40, "toothpaste": 95, "notebook": 60, "pen": 20,
    "phone charger": 499, "headphones": 1299, "batteries": 150, "light bulb": 90,
    "detergent": 190, "tissues": 80, "socks": 250, "t-shirt": 599,
}


class ShoppingConnector(Connector):
    domain = "shopping"

    def search(self, prefs: dict, slots: dict) -> list[dict]:
        wanted = slots.get("items", [])
        results = []
        for name in wanted:
            key = name.lower().strip()
            base_price = CATALOG_HINTS.get(key, 299)
            rnd = random.Random(key)
            results.append({
                "item": key,
                "brand": prefs.get("preferred_brands", {}).get(key, "top-rated"),
                "price": base_price + rnd.randint(-20, 40),
                "in_stock": True,
            })
        return results

    def quote(self, prefs: dict, slots: dict) -> Cart:
        provider = prefs.get("preferred_app", "app not yet chosen")
        options = self.search(prefs, slots)
        items = [{"item": o["item"], "brand": o["brand"], "qty": "1", "price": o["price"]} for o in options]
        total = round(sum(i["price"] for i in items), 2)
        budget = prefs.get("budget_cap")
        notes = None
        if budget and total > budget:
            notes = f"Order total ₹{total} exceeds your ₹{budget} budget."
        return Cart(title=f"Shopping order via {provider}", items=items, total=total, notes=notes)

    def execute(self, prefs: dict, slots: dict, cart: Cart) -> dict:
        rnd = random.Random(cart.total)
        return {
            "provider": prefs.get("preferred_app", "app not yet chosen"),
            "order_id": f"SHP-{rnd.randint(100000, 999999)}",
            "eta_days": rnd.randint(1, 5),
            "status": "placed",
        }
