from __future__ import annotations

import argparse

from eval.synthetic.workflow import prepare_review_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare synthetic raw records for human review.")
    parser.add_argument("--raw-path", required=True)
    parser.add_argument("--output-root", default="eval/synthetic")
    parser.add_argument("--run-name", required=True)
    args = parser.parse_args()
    prepare_review_records(raw_path=args.raw_path, output_root=args.output_root, run_name=args.run_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

