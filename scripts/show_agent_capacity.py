import argparse
import json

from agent_capacity import recommend_workers


def main() -> int:
    parser = argparse.ArgumentParser(description="Show capacity-based max agent workers.")
    parser.add_argument("--task", default="mixed", choices=["io", "mixed", "cpu"], help="Task profile")
    args = parser.parse_args()

    cap = recommend_workers(task=args.task)
    print(json.dumps(cap, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

