import random

from .base import Cart, Connector

AIRLINES = ["IndiGo", "Air India", "Vistara", "SpiceJet", "Akasa Air"]


class FlightConnector(Connector):
    domain = "flight"

    def search(self, prefs: dict, slots: dict) -> list[dict]:
        origin = slots.get("origin", "your city")
        destination = slots.get("destination", "destination")
        date = slots.get("date", "your travel date")
        seed = f"{origin}-{destination}-{date}"
        rnd = random.Random(seed)
        results = []
        for airline in AIRLINES:
            price = rnd.randint(3200, 18500)
            dep_hour = rnd.randint(5, 22)
            results.append({
                "airline": airline,
                "flight_no": f"{airline[:2].upper()}{rnd.randint(100,999)}",
                "origin": origin,
                "destination": destination,
                "date": date,
                "departure": f"{dep_hour:02d}:{rnd.choice(['00','15','30','45'])}",
                "price": price,
                "stops": rnd.choice([0, 0, 0, 1]),
            })
        return sorted(results, key=lambda r: r["price"])

    def quote(self, prefs: dict, slots: dict) -> Cart:
        provider = prefs.get("preferred_app", "app not yet chosen")
        budget = prefs.get("budget_cap") or slots.get("budget_cap")
        options = self.search(prefs, slots)
        affordable = [o for o in options if not budget or o["price"] <= budget]
        chosen = (affordable or options)[0]
        stops_label = "non-stop" if chosen["stops"] == 0 else f"{chosen['stops']} stop"
        items = [{
            "item": f"{chosen['airline']} {chosen['flight_no']}",
            "route": f"{chosen['origin']} → {chosen['destination']} on {chosen['date']}",
            "detail": f"Departs {chosen['departure']}, {stops_label}",
            "price": chosen["price"],
        }]
        notes = None
        if budget and chosen["price"] > budget:
            notes = f"Cheapest option (₹{chosen['price']}) exceeds your ₹{budget} budget — no flight found under budget."
        else:
            cheaper_alts = ", ".join(f"{o['airline']} ₹{o['price']}" for o in options[1:3])
            notes = f"Also available: {cheaper_alts}" if cheaper_alts else None
        return Cart(
            title=f"Flight booking via {provider}",
            items=items,
            total=chosen["price"],
            notes=notes,
        )

    def execute(self, prefs: dict, slots: dict, cart: Cart) -> dict:
        rnd = random.Random(cart.total + hash(slots.get("date", "")) % 1000)
        pnr = "".join(rnd.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=6))
        return {
            "provider": prefs.get("preferred_app", "app not yet chosen"),
            "pnr": pnr,
            "status": "booked",
        }
