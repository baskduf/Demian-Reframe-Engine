from __future__ import annotations

import argparse

from eval.synthetic.workflow import promote_reviewed_cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote approved synthetic review records into an evaluator-ready dataset.")
    parser.add_argument("--review-path", required=True)
    parser.add_argument("--output-root", default="eval/synthetic")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--export-dataset-path", default=None)
    args = parser.parse_args()
    promote_reviewed_cases(
        review_path=args.review_path,
        output_root=args.output_root,
        run_name=args.run_name,
        export_dataset_path=args.export_dataset_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

