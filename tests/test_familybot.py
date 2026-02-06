# tests/test_familybot.py
from familybot import FamilyFinanceAgent


def test_shared_payment_and_owes():
    agent = FamilyFinanceAgent(["Alex", "Jamie", "Sam"])
    text = "Alex paid 120 for groceries for Jamie and Sam. Jamie owes Alex 40."
    result = agent.analyze(text)
    members = result["summary"]["members"]
    alex = members["Alex"]
    jamie = members["Jamie"]
    sam = members["Sam"]
    assert alex["paid"] == 120.0
    assert jamie["consumed"] == 60.0
    assert sam["consumed"] == 60.0
    assert jamie["owes"] > 0
    assert sam["owes"] > 0
    total_due = alex["due"]
    total_owes = jamie["owes"] + sam["owes"]
    assert abs(total_due - total_owes) < 0.01
