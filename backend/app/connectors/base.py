"""
Connector interface.

Every real-world service (grocery platform, taxi app, flight search,
shopping site) implements this same three-step interface:

    search(prefs, slots)  -> list of options the agent found
    quote(prefs, slots)   -> a cart/description + total amount, ready for
                              human approval
    execute(prefs, slots) -> performs the action against the provider and
                              returns a result the activity timeline can show

These implementations are SIMULATED: there are no live Uber/Ola, Amadeus,
BigBasket or Amazon credentials wired into this demo. They return
deterministic-but-realistic data and are written so a real provider SDK
call is a drop-in replacement for the body of each method — the rest of
the platform (orchestrator, approvals, activity log, memory) does not
change at all when a real connector is swapped in.

Payments go through `PaymentRail`, a similarly pluggable seam. The
platform never asks for or stores a UPI PIN, card number or bank OTP —
that always happens inside the payment rail's own regulated flow.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Cart:
    title: str
    items: list[dict]
    total: float
    currency: str = "INR"
    notes: str | None = None


class Connector(ABC):
    domain: str

    @abstractmethod
    def search(self, prefs: dict, slots: dict) -> list[dict]:
        ...

    @abstractmethod
    def quote(self, prefs: dict, slots: dict) -> Cart:
        ...

    @abstractmethod
    def execute(self, prefs: dict, slots: dict, cart: Cart) -> dict:
        ...


class PaymentRail:
    """
    Stand-in for a regulated payment flow (e.g. UPI AutoPay / card network
    tokenisation). The platform hands this a final approved amount and a
    reference; the rail is responsible for its own authentication (PIN /
    biometric / OTP) which never passes through this app.
    """

    def __init__(self, rail_id: str = "simulated_upi"):
        self.rail_id = rail_id

    def charge(self, amount: float, currency: str, reference: str) -> dict:
        return {
            "status": "success",
            "rail": self.rail_id,
            "reference": reference,
            "amount": amount,
            "currency": currency,
            "note": (
                "Simulated payment rail (demo mode). In production this call "
                "is replaced by a regulated payment SDK (e.g. UPI AutoPay / "
                "card network) — the platform never handles the PIN/OTP."
            ),
        }
