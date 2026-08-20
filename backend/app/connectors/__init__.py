from .base import Cart, Connector, PaymentRail
from .grocery import GroceryConnector
from .taxi import TaxiConnector
from .flight import FlightConnector
from .shopping import ShoppingConnector

CONNECTORS: dict[str, Connector] = {
    "grocery": GroceryConnector(),
    "taxi": TaxiConnector(),
    "flight": FlightConnector(),
    "shopping": ShoppingConnector(),
}

__all__ = ["Cart", "Connector", "PaymentRail", "CONNECTORS"]
