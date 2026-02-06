# familybot/cli.py
import sys
from typing import List

from familybot import FamilyFinanceAgent, format_summary_ar


def main(argv: List[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        text = sys.stdin.read()
    else:
        text = " ".join(argv)
    members = ["Alex", "Jamie", "Sam"]
    agent = FamilyFinanceAgent(members)
    result = agent.analyze(text)
    out = format_summary_ar(result, "ملخص من سطر الأوامر:")
    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
