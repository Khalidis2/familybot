# familybot/cli.py
from __future__ import annotations

import argparse
import sys

from familybot import FamilyFinanceAgent, format_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze family transactions.")
    parser.add_argument("--members", nargs="+", required=True, help="Family member names")
    parser.add_argument("--file", type=str, help="Path to a text file containing transactions")
    parser.add_argument("--explain-ar", action="store_true", help="Print Arabic explanation")
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


if __name__ == "__main__":
    main()
