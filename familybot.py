"""Family finance helper for parsing transaction text."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, Iterable, List, Tuple

DEFAULT_CURRENCY = "AED"
AMOUNT_PATTERN = re.compile(
    r"(?P<currency>\$|€|USD|EUR|AED|Dh|Dirham|Dirhams|درهم|درهماً|درهم إماراتي)?\s*"
    r"(?P<amount>[0-9٠-٩۰-۹][0-9٠-٩۰-۹.,٬]*)"
)
AED_INDICATORS = (
    "aed",
    "dh",
    "dirham",
    "dirhams",
    "درهم",
    "درهماً",
    "درهم إماراتي",
)
ARABIC_DIGITS_MAP = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"
)


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).title()


def _normalize_number(value: str) -> str:
    value = value.translate(ARABIC_DIGITS_MAP)
    value = value.replace(",", "").replace("٬", "")
    return value


def _extract_amount(text: str) -> float | None:
    match = AMOUNT_PATTERN.search(text)
    if not match:
        return None
    normalized = _normalize_number(match.group("amount"))
    return float(normalized)


def _extract_amounts_with_currency(text: str) -> List[Tuple[float, str]]:
    results: List[Tuple[float, str]] = []
    for match in AMOUNT_PATTERN.finditer(text):
        amount_text = _normalize_number(match.group("amount"))
        amount = float(amount_text)
        currency_hint = match.group("currency") or ""
        currency = _detect_currency(currency_hint or text)
        results.append((amount, currency))
    return results


def _detect_currency(text: str) -> str:
    lower_text = text.lower()
    if any(indicator in lower_text for indicator in AED_INDICATORS):
        return "AED"
    if "$" in text or "usd" in lower_text:
        return "USD"
    if "€" in text or "eur" in lower_text:
        return "EUR"
    return DEFAULT_CURRENCY


def _find_members_in_text(text: str, members: Iterable[str]) -> List[str]:
    found = []
    lower_text = text.lower()
    for member in members:
        if member.lower() in lower_text:
            found.append(member)
    return found


@dataclass
class Ledger:
    debts: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def add_debt(self, debtor: str, creditor: str, amount: float) -> None:
        if amount <= 0:
            return
        self.debts.setdefault(debtor, {})
        self.debts[debtor][creditor] = self.debts[debtor].get(creditor, 0.0) + amount

    def reduce_debt(self, debtor: str, creditor: str, amount: float) -> None:
        if amount <= 0:
            return
        if debtor not in self.debts or creditor not in self.debts[debtor]:
            return
        self.debts[debtor][creditor] = max(self.debts[debtor][creditor] - amount, 0.0)

    def totals(self, members: Iterable[str]) -> Dict[str, Dict[str, float]]:
        totals: Dict[str, Dict[str, float]] = {}
        for member in members:
            owes = sum(self.debts.get(member, {}).values())
            due = sum(
                creditor_amounts.get(member, 0.0)
                for creditor_amounts in self.debts.values()
            )
            totals[member] = {
                "owes": round(owes, 2),
                "due": round(due, 2),
                "net": round(due - owes, 2),
            }
        return totals

    def settle_suggestions(self) -> List[Tuple[str, str, float]]:
        suggestions = []
        for debtor, creditors in self.debts.items():
            for creditor, amount in creditors.items():
                if amount > 0:
                    suggestions.append((debtor, creditor, round(amount, 2)))
        return suggestions


@dataclass
class FamilyFinanceAgent:
    family_members: List[str]

    def __post_init__(self) -> None:
        self.family_members = [_normalize_name(name) for name in self.family_members]

    def analyze(self, text: str) -> Dict[str, object]:
        ledger = Ledger()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        detected_currencies = []
        loans = []
        monthly_obligations: Dict[str, float] = {}

        for line in lines:
            normalized_line = line.lower()
            amount = _extract_amount(line)
            if amount is None:
                continue
            detected_currencies.append(_detect_currency(line))

            if self._is_loan_line(normalized_line):
                loan = self._parse_loan_line(line)
                if loan:
                    loans.append(loan)
                    borrower = loan["borrower"]
                    monthly_payment = loan["monthly_payment"]
                    if monthly_payment:
                        monthly_obligations[borrower] = (
                            monthly_obligations.get(borrower, 0.0) + monthly_payment
                        )
                continue

            if "owes" in normalized_line:
                self._handle_owes(line, ledger, amount)
                continue

            if "reimbursed" in normalized_line or "paid back" in normalized_line:
                self._handle_reimbursement(line, ledger, amount)
                continue

            if "paid" in normalized_line:
                self._handle_payment(line, ledger, amount)

        summary = ledger.totals(self.family_members)
        for member in self.family_members:
            summary.setdefault(member, {})
            summary[member]["monthly_obligations"] = round(
                monthly_obligations.get(member, 0.0), 2
            )
        suggestions = ledger.settle_suggestions()

        paid_members = [member for member, data in summary.items() if data["due"] > 0]
        unpaid_members = [
            member for member, data in summary.items() if data["owes"] > 0
        ]

        currencies = sorted({currency for currency in detected_currencies if currency})
        if not currencies:
            currency = DEFAULT_CURRENCY
        elif len(currencies) == 1:
            currency = currencies[0]
        else:
            currency = "mixed"

        return {
            "summary": summary,
            "settlement_suggestions": suggestions,
            "paid_members": paid_members,
            "unpaid_members": unpaid_members,
            "currency": currency,
            "loans": loans,
        }

    def _handle_owes(self, line: str, ledger: Ledger, amount: float) -> None:
        parts = re.split(r"owes", line, flags=re.IGNORECASE)
        if len(parts) < 2:
            return
        debtor_name = _normalize_name(parts[0])
        creditor_candidates = _find_members_in_text(parts[1], self.family_members)
        creditor_name = _normalize_name(creditor_candidates[0]) if creditor_candidates else "Unknown"
        ledger.add_debt(debtor_name, creditor_name, amount)

    def _handle_reimbursement(self, line: str, ledger: Ledger, amount: float) -> None:
        words = line.split()
        if not words:
            return
        debtor_name = _normalize_name(words[0])
        creditor_candidates = _find_members_in_text(line, self.family_members)
        creditor_name = _normalize_name(creditor_candidates[1]) if len(creditor_candidates) > 1 else "Unknown"
        ledger.reduce_debt(debtor_name, creditor_name, amount)

    def _handle_payment(self, line: str, ledger: Ledger, amount: float) -> None:
        words = line.split()
        if not words:
            return
        payer_name = _normalize_name(words[0])
        beneficiaries = self._extract_beneficiaries(line)
        if not beneficiaries:
            beneficiaries = self.family_members
        if not beneficiaries:
            return
        split_amount = round(amount / len(beneficiaries), 2)
        for beneficiary in beneficiaries:
            beneficiary = _normalize_name(beneficiary)
            if beneficiary == payer_name:
                continue
            ledger.add_debt(beneficiary, payer_name, split_amount)

    def _extract_beneficiaries(self, line: str) -> List[str]:
        positions = [m.start() for m in re.finditer(r"\bfor\b", line, flags=re.IGNORECASE)]
        if not positions:
            return []
        remainder = line[positions[-1] + len("for") :].strip()
        if re.search(r"everyone|family|all", remainder, flags=re.IGNORECASE):
            return list(self.family_members)
        tokens = re.split(r",|and", remainder)
        names = []
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            name_match = _find_members_in_text(token, self.family_members)
            if name_match:
                names.extend(name_match)
            else:
                names.append(token)
        return names

    def _is_loan_line(self, normalized_line: str) -> bool:
        return "loan" in normalized_line or "قرض" in normalized_line

    def _parse_loan_line(self, line: str) -> Dict[str, object] | None:
        normalized = line.lower()
        if not self._is_loan_line(normalized):
            return None
        borrower = self._extract_borrower(line)
        lender = "Bank"
        amounts = _extract_amounts_with_currency(line)
        if not amounts:
            return None
        principal = amounts[0][0]
        currency = amounts[0][1]
        monthly_payment = amounts[1][0] if len(amounts) > 1 else None
        if "monthly" not in normalized and "شهري" not in normalized:
            monthly_payment = None
        description = (
            f"قرض حصل عليه {borrower} بمبلغ {principal:.2f} {currency}"
        )
        if monthly_payment:
            description += f" مع دفعة شهرية {monthly_payment:.2f} {currency}"
        return {
            "description": description,
            "borrower": borrower,
            "lender": lender,
            "principal": principal,
            "currency": currency,
            "monthly_payment": monthly_payment,
        }

    def _extract_borrower(self, line: str) -> str:
        tokens = line.split()
        if not tokens:
            return "Unknown"
        if "took" in line.lower():
            return _normalize_name(tokens[0])
        if "أخذ" in line or "اخذ" in line:
            return tokens[0]
        return _normalize_name(tokens[0])

    def explain(self, result: Dict[str, object]) -> str:
        summary = result.get("summary", {})
        suggestions = result.get("settlement_suggestions", [])
        currency = result.get("currency", DEFAULT_CURRENCY)
        lines = ["ملخص العائلة المالي:"]
        for member, data in summary.items():
            lines.append(
                f"- {member}: مدفوع له {data['due']:.2f} {currency}، مديون {data['owes']:.2f} {currency}، "
                f"صافي {data['net']:.2f} {currency}، الالتزامات الشهرية {data['monthly_obligations']:.2f} {currency}."
            )
        if suggestions:
            lines.append("التسويات المقترحة:")
            for debtor, creditor, amount in suggestions:
                lines.append(
                    f"- {debtor} يدفع لـ {creditor}: {amount:.2f} {currency}."
                )
        return "\n".join(lines)


def format_summary(result: Dict[str, object]) -> str:
    currency = result.get("currency", DEFAULT_CURRENCY)
    lines = ["Family Finance Summary", "----------------------", f"Currency: {currency}"]
    summary = result.get("summary", {})
    for member, data in summary.items():
        lines.append(
            f"{member}: owes {data['owes']:.2f} {currency}, due {data['due']:.2f} {currency}, net {data['net']:.2f} {currency}"
        )
        lines.append(
            f"{member}: monthly obligations {data['monthly_obligations']:.2f} {currency}"
        )
    suggestions = result.get("settlement_suggestions", [])
    if suggestions:
        lines.append("\nSettlement Suggestions")
        for debtor, creditor, amount in suggestions:
            lines.append(f"- {debtor} pays {creditor}: {amount:.2f} {currency}")
    loans = result.get("loans", [])
    if loans:
        lines.append("\nLoans")
        for loan in loans:
            monthly = (
                f", monthly {loan['monthly_payment']:.2f} {loan['currency']}"
                if loan.get("monthly_payment")
                else ""
            )
            lines.append(
                f"- {loan['borrower']} borrowed {loan['principal']:.2f} {loan['currency']} from {loan['lender']}{monthly}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Analyze family transactions.")
    parser.add_argument("--members", nargs="+", required=True, help="Family member names")
    parser.add_argument(
        "--file", type=str, help="Path to a text file containing transactions"
    )
    parser.add_argument(
        "--explain-ar", action="store_true", help="Print Arabic explanation"
    )
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            input_text = handle.read()
    else:
        input_text = sys.stdin.read()

    agent = FamilyFinanceAgent(args.members)
    analysis = agent.analyze(input_text)
    print(format_summary(analysis))
    if args.explain_ar:
        print("\n" + agent.explain(analysis))
