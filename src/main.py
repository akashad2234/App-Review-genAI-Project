"""
CLI entry point (Phase 6): full pipeline ingest → theme → pulse → email.
Usage: python -m src.main [--weeks N] [--send] [--output-dir DIR] [--force] [--recipient-name NAME] [--recipient-email EMAIL]
"""

import argparse
import logging
import sys
from pathlib import Path

from src.pipeline import PipelineConfig, run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Groww Weekly Review Pulse: ingest reviews, generate themes, pulse, and optional email."
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=None,
        help="Review window in weeks (default: from config REVIEW_WINDOW_WEEKS)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the pulse email (default: draft only)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for run (default: output/YYYY-MM-DD)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run all phases (no skip based on existing output)",
    )
    parser.add_argument(
        "--recipient-name",
        type=str,
        default=None,
        help="Recipient name for personalized email (e.g. Akash)",
    )
    parser.add_argument(
        "--recipient-email",
        type=str,
        default=None,
        help="Recipient email address",
    )
    args = parser.parse_args()

    config = PipelineConfig(
        weeks=args.weeks,
        send_email=args.send,
        output_dir=args.output_dir,
        recipient_name=args.recipient_name,
        recipient_email=args.recipient_email,
        force=args.force,
    )
    result = run_pipeline(config)

    if result.status == "success":
        print(f"Run {result.run_id} completed. output_dir={result.output_dir}")
        if result.email_sent:
            print("Email sent.")
        else:
            print("Email drafted only (use --send to send).")
        return 0
    else:
        print(f"Run {result.run_id} failed: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
