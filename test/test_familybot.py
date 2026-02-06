# tests/test_familybot.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from familybot import FamilyFinanceAgent


def test_shared_payment_and_owes():
    agent = FamilyFinanceAgent(["Alex", "Jamie", "Sam"])
    text = """
    Alex paid $90 for Jamie and Sam
    """
    result = agent.analyze(text)
    summary = result["summary"]
    assert summary["Alex"]["due"] == 90.0
    assert summary["Jamie"]["owes"] == 45.0
    assert summary["Sam"]["owes"] == 45.0


def test_default_currency_is_aed():
    agent = FamilyFinanceAgent(["Alex", "Jamie", "Sam"])
    text = "Alex paid 200 for groceries for Jamie and Sam"
    result = agent.analyze(text)
    assert result["currency"] == "AED"


def test_explicit_aed_currency():
    agent = FamilyFinanceAgent(["Alex"])
    text = "Alex paid 200 AED for groceries"
    result = agent.analyze(text)
    assert result["currency"] == "AED"


def test_explicit_usd_currency():
    agent = FamilyFinanceAgent(["Alex"])
    text = "Alex paid $200 for groceries"
    result = agent.analyze(text)
    assert result["currency"] == "USD"


def test_loan_monthly_obligation():
    agent = FamilyFinanceAgent(["Omar"])
    text = "Omar took a car loan of 100,000 AED and will pay 5,000 AED monthly."
    result = agent.analyze(text)
    assert result["loans"]
    assert result["loans"][0]["borrower"] == "Omar"
    assert result["summary"]["Omar"]["monthly_obligations"] == 5000.0


def test_explain_returns_arabic_text():
    agent = FamilyFinanceAgent(["Omar"])
    text = "Omar took a car loan of 100,000 AED and will pay 5,000 AED monthly."
    result = agent.analyze(text)
    explanation = agent.explain(result)
    assert "مديون" in explanation or "درهم" in explanation


def test_category_rent():
    agent = FamilyFinanceAgent(["Sara"])
    result = agent.analyze("Sara paid 3000 for apartment rent")
    assert "إيجار" in result["transactions"][0]["category"]


def test_category_telecom():
    agent = FamilyFinanceAgent(["Sara"])
    result = agent.analyze("سارة دفعت فاتورة اتصالات 200 درهم")
    assert "اتصالات" in result["transactions"][0]["category"]


def test_arabic_summary_includes_member_name():
    agent = FamilyFinanceAgent(["Sara"])
    result = agent.analyze("Sara paid 200 for groceries")
    summary_text = agent.format_arabic_summary(result, "ملخص هذا الشهر")
    assert "سارة" in summary_text or "Sara" in summary_text
