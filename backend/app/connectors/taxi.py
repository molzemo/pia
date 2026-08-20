import random

from .base import Cart, Connector

VEHICLE_OPTIONS = [
    {"type": "Auto", "base": 45, "per_km": 12},
    {"type": "Mini (Sedan)", "base": 60, "per_km": 16},
    {"type": "Premium (SUV)", "base": 90, "per_km": 24},
]


class TaxiConnector(Connector):
    domain = "taxi"

    def _distance_km(self, destination: str) -> float:
        # Simulated distance lookup — a real integration would call the
        # provider's directions/geocoding API with pickup + destination.
        rnd = random.Random(destination.lower().strip())
        return round(rnd.uniform(4, 32), 1)

    def search(self, prefs: dict, slots: dict) -> list[dict]:
        destination = slots.get("destination", "")
        km = self._distance_km(destination)
        options = []
        for v in VEHICLE_OPTIONS:
            fare = round(v["base"] + v["per_km"] * km, 2)
            options.append({"vehicle": v["type"], "distance_km": km, "fare": fare})
        return options

    def quote(self, prefs: dict, slots: dict) -> Cart:
        provider = prefs.get("preferred_app", "app not yet chosen")
        pickup = slots.get("pickup_address", "your saved home address")
        destination = slots.get("destination", "destination")
        vehicle_pref = prefs.get("preferred_vehicle", "Mini (Sedan)")
        options = self.search(prefs, slots)
        chosen = next((o for o in options if o["vehicle"] == vehicle_pref), options[1])
        items = [{
            "item": f"{chosen['vehicle']} ride",
            "route": f"{pickup} → {destination}",
            "distance": f"{chosen['distance_km']} km",
            "price": chosen["fare"],
        }]
        return Cart(
            title=f"Taxi booking via {provider}",
            items=items,
            total=chosen["fare"],
            notes=f"Other options: " + ", ".join(f"{o['vehicle']} ₹{o['fare']}" for o in options if o['vehicle'] != chosen['vehicle']),
        )

    def execute(self, prefs: dict, slots: dict, cart: Cart) -> dict:
        rnd = random.Random(cart.total + hash(slots.get("destination", "")) % 1000)
        eta_minutes = rnd.randint(3, 12)
        driver_names = ["Ramesh", "Suresh", "Anita", "Kavya", "Farhan", "Deepak"]
        return {
            "provider": prefs.get("preferred_app", "app not yet chosen"),
            "booking_id": f"TXI-{rnd.randint(100000, 999999)}",
            "driver": rnd.choice(driver_names),
            "eta_minutes": eta_minutes,
            "status": "confirmed",
        }
