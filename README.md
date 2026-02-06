# FamilyBot

FamilyBot is a lightweight helper that parses plain text transaction notes and reports who paid, who owes, and how to settle up. It is UAE-friendly and defaults to AED when no currency is specified. It also understands loans with monthly installments and can generate human-readable explanations in Modern Standard Arabic.

## Usage

```bash
python familybot.py --members "Alex" "Jamie" "Sam" --file transactions.txt
```

Or via stdin:

```bash
cat transactions.txt | python familybot.py --members "Alex" "Jamie" "Sam"
```

### Example input (AED default)

```
Alex paid 120 for groceries for Jamie and Sam
Jamie owes Alex 40
Sam reimbursed Alex 20
```

### Example output

```
Family Finance Summary
----------------------
Currency: AED
Alex: owes 0.00 AED, due 80.00 AED, net 80.00 AED
Jamie: owes 20.00 AED, due 0.00 AED, net -20.00 AED
Sam: owes 60.00 AED, due 0.00 AED, net -60.00 AED

Settlement Suggestions
- Jamie pays Alex: 20.00 AED
- Sam pays Alex: 60.00 AED
```

### Example input (explicit AED + Arabic)

```
Alex paid 200 AED for groceries
Sara owes Alex 50 درهم
```

### Example input (loan with monthly installments)

```
عمر أخذ قرض ١٢٠٬٠٠٠ درهم ويسدد ٥٬٠٠٠ شهرياً
```

### Example Arabic explanation

```
ملخص العائلة المالي:
- عمر: مدفوع له 0.00 AED، مديون 0.00 AED، صافي 0.00 AED، الالتزامات الشهرية 5000.00 AED.
التسويات المقترحة:
```

## Notes on parsing

- Lines containing **paid** create shared expenses.
- Lines containing **owes** create direct debts.
- Lines containing **reimbursed** or **paid back** reduce debts.
- If a line doesn't specify beneficiaries ("for ..."), the expense is split across all members.
- When no currency is provided, AED is assumed by default.
- Loan phrases with monthly payments add to each member's monthly obligations.
- Arabic explanations are generated in Modern Standard Arabic.
