from __future__ import annotations

import argparse

from eval.synthetic.workflow import generate_synthetic_raw


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic Korean GAD evaluation drafts.")
    parser.add_argument("--config", default="eval/synthetic/config/default_mix.json")
    parser.add_argument("--output-root", default="eval/synthetic")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--count", type=int, default=None)
    args = parser.parse_args()
    generate_synthetic_raw(config_path=args.config, output_root=args.output_root, run_name=args.run_name, total_cases=args.count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

