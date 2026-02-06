# familybot/__init__.py
import os
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple


@dataclass
class MemberSummary:
    paid: float = 0.0
    consumed: float = 0.0
    net: float = 0.0
    owes: float = 0.0
    due: float = 0.0
    monthly_obligations: float = 0.0


@dataclass
class Transaction:
    description: str
    payer: str
    amount: float
    currency: str
    beneficiaries: List[str]
    shares: Dict[str, float]
    category: str


class FamilyFinanceAgent:
    def __init__(self, members: List[str], currency: str = "AED") -> None:
        self.members = members
        self.currency = currency

    def analyze(self, text: str) -> Dict[str, Any]:
        transactions, debts, loans = self._fallback_parse(text)
        summary_members = {m: MemberSummary() for m in self.members}
        for tx in transactions:
            payer = tx.payer
            amount = tx.amount
            summary_members[payer].paid += amount
            for b, share in tx.shares.items():
                summary_members[b].consumed += share
        for d in debts:
            debtor = d["from"]
            creditor = d["to"]
            amount = d["amount"]
            summary_members[debtor].net -= amount
            summary_members[creditor].net += amount
        for name, s in summary_members.items():
            s.net += s.paid - s.consumed
        settlements = self._compute_settlements(summary_members)
        for name, s in summary_members.items():
            if s.net < 0:
                s.owes = round(-s.net, 2)
                s.due = 0.0
            elif s.net > 0:
                s.due = round(s.net, 2)
                s.owes = 0.0
            else:
                s.owes = 0.0
                s.due = 0.0
            s.paid = round(s.paid, 2)
            s.consumed = round(s.consumed, 2)
            s.net = round(s.net, 2)
        debts_from_settlements = [
            {"from": s["from"], "to": s["to"], "amount": s["amount"]}
            for s in settlements
        ]
        result = {
            "transactions": [
                {
                    "description": tx.description,
                    "payer": tx.payer,
                    "amount": tx.amount,
                    "currency": tx.currency,
                    "beneficiaries": tx.beneficiaries,
                    "shares": tx.shares,
                    "category": tx.category,
                }
                for tx in transactions
            ],
            "loans": loans,
            "summary": {
                "members": {
                    name: {
                        "paid": s.paid,
                        "consumed": s.consumed,
                        "net": s.net,
                        "owes": s.owes,
                        "due": s.due,
                        "monthly_obligations": round(
                            s.monthly_obligations, 2
                        ),
                    }
                    for name, s in summary_members.items()
                },
                "debts": debts_from_settlements,
                "settlements": settlements,
            },
        }
        return result

    def _fallback_parse(
        self, text: str
    ) -> Tuple[List[Transaction], List[Dict[str, Any]], List[Dict[str, Any]]]:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        transactions: List[Transaction] = []
        debts: List[Dict[str, Any]] = []
        loans: List[Dict[str, Any]] = []
        for line in lines:
            lower = line.lower()
            tokens = lower.replace(".", "").split()
            payer = None
            amount = None
            for name in self.members:
                if name.lower() in lower and "paid" in tokens:
                    payer = name
                    break
            if payer is not None:
                amount = self._extract_number(lower)
                if amount is not None:
                    beneficiaries = [
                        name
                        for name in self.members
                        if name != payer and name.lower() in lower
                    ]
                    if not beneficiaries:
                        beneficiaries = [m for m in self.members if m != payer]
                    share = round(amount / max(len(beneficiaries), 1), 2)
                    shares = {b: share for b in beneficiaries}
                    category = self._guess_category(lower)
                    tx = Transaction(
                        description=line,
                        payer=payer,
                        amount=amount,
                        currency=self.currency,
                        beneficiaries=beneficiaries,
                        shares=shares,
                        category=category,
                    )
                    transactions.append(tx)
                    continue
            debtor, creditor, amount = self._parse_owes_line(line)
            if debtor and creditor and amount is not None:
                debts.append(
                    {
                        "from": debtor,
                        "to": creditor,
                        "amount": round(amount, 2),
                    }
                )
                continue
            loan = self._parse_loan_line(line)
            if loan is not None:
                loans.append(loan)
        return transactions, debts, loans

    def _extract_number(self, s: str) -> float | None:
        buf = []
        for ch in s:
            if ch.isdigit() or ch == ".":
                buf.append(ch)
            else:
                buf.append(" ")
        parts = [p for p in "".join(buf).split() if p]
        for p in parts[::-1]:
            try:
                return float(p)
            except ValueError:
                continue
        return None

    def _guess_category(self, lower: str) -> str:
        if "rent" in lower or "إيجار" in lower:
            return "إيجار"
        if "grocery" in lower or "بقالة" in lower or "سوبرماركت" in lower:
            return "بقالة"
        if "school" in lower or "رسوم" in lower or "مدرسة" in lower:
            return "رسوم مدرسة"
        if "salik" in lower or "سالك" in lower:
            return "سالِك"
        if "parking" in lower or "موقف" in lower or "مواقف" in lower:
            return "مواقف"
        if "electric" in lower or "كهرباء" in lower:
            return "كهرباء"
        if "water" in lower or "ماء" in lower or "مياه" in lower:
            return "ماء"
        if (
            "etisalat" in lower
            or "du" in lower.split()
            or "اتصالات" in lower
            or "إنترنت" in lower
        ):
            return "اتصالات"
        if "loan" in lower or "قرض" in lower:
            return "قرض"
        return "غير مصنف"

    def _parse_owes_line(
        self, line: str
    ) -> Tuple[str | None, str | None, float | None]:
        lower = line.lower()
        if "owes" not in lower and "مديون" not in lower:
            return None, None, None
        debtor = None
        creditor = None
        for name in self.members:
            if name.lower() in lower and debtor is None:
                debtor = name
                break
        if "owes" in lower:
            after = lower.split("owes", 1)[1]
            for name in self.members:
                if name.lower() in after:
                    creditor = name
                    break
        if "لـ" in line or "لى" in lower:
            for name in self.members:
                if name in line:
                    if debtor is None:
                        debtor = name
                    elif creditor is None and name != debtor:
                        creditor = name
        amount = self._extract_number(lower)
        if debtor and creditor and amount is not None:
            return debtor, creditor, amount
        return None, None, None

    def _parse_loan_line(self, line: str) -> Dict[str, Any] | None:
        lower = line.lower()
        if "loan" not in lower and "قرض" not in lower:
            return None
        borrower = None
        for name in self.members:
            if name.lower() in lower:
                borrower = name
                break
        if borrower is None:
            return None
        principal = self._extract_number(lower)
        monthly_payment = None
        if "month" in lower or "شهري" in lower or "شهرياً" in lower:
            monthly_payment = self._extract_number(lower)
        loan = {
            "description": line,
            "borrower": borrower,
            "lender": "البنك",
            "principal": principal or 0.0,
            "currency": self.currency,
            "monthly_payment": monthly_payment or 0.0,
            "months_total": None,
            "months_paid": None,
            "remaining_principal": None,
        }
        return loan

    def _compute_settlements(
        self, members: Dict[str, MemberSummary]
    ) -> List[Dict[str, Any]]:
        creditors: List[Tuple[str, float]] = []
        debtors: List[Tuple[str, float]] = []
        for name, s in members.items():
            if s.net > 0.01:
                creditors.append((name, s.net))
            elif s.net < -0.01:
                debtors.append((name, -s.net))
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)
        settlements: List[Dict[str, Any]] = []
        i = 0
        j = 0
        while i < len(debtors) and j < len(creditors):
            d_name, d_amt = debtors[i]
            c_name, c_amt = creditors[j]
            pay = min(d_amt, c_amt)
            pay = round(pay, 2)
            if pay > 0:
                settlements.append(
                    {"from": d_name, "to": c_name, "amount": pay}
                )
            d_amt -= pay
            c_amt -= pay
            if d_amt <= 0.01:
                i += 1
            else:
                debtors[i] = (d_name, d_amt)
            if c_amt <= 0.01:
                j += 1
            else:
                creditors[j] = (c_name, c_amt)
        return settlements


def format_summary_ar(result: Dict[str, Any], period_label: str) -> str:
    members = result["summary"]["members"]
    settlements = result["summary"].get("settlements", [])
    loans = result.get("loans", [])
    lines: List[str] = []
    lines.append(period_label)
    lines.append("")
    lines.append("ملخص الأعضاء:")
    for name, s in members.items():
        paid = s["paid"]
        consumed = s["consumed"]
        net = s["net"]
        lines.append(
            f"- {name}: دفع {paid:.2f}، استفاد {consumed:.2f}، الصافي {net:.2f} درهم"
        )
    if settlements:
        lines.append("")
        lines.append("طريقة التسوية المقترحة:")
        for s in settlements:
            frm = s["from"]
            to = s["to"]
            amt = s["amount"]
            lines.append(f"- {frm} يدفع {amt:.2f} درهماً إلى {to}")
    else:
        lines.append("")
        lines.append("لا توجد مبالغ متبقية للتسوية بين الأعضاء.")
    if loans:
        lines.append("")
        lines.append("القروض والأقساط:")
        for loan in loans:
            borrower = loan["borrower"]
            principal = loan["principal"]
            monthly = loan["monthly_payment"]
            lines.append(
                f"- {borrower}: قرض قدره {principal:.2f} درهم، قسط شهري {monthly:.2f} درهم"
            )
    return "\n".join(lines)
