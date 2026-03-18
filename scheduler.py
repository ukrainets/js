"""
Scheduler entry point.

Usage:
    python scheduler.py              # start scheduler, wait for scheduled times
    python scheduler.py --run-now    # run a scan immediately, then follow the schedule
"""

import argparse
from integrations.scheduler import run_scheduler


def main():
    parser = argparse.ArgumentParser(
        description="Run job search scanner on a schedule.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--run-now", action="store_true",
        help="Run a scan immediately on startup, then follow the schedule",
    )
    args = parser.parse_args()
    run_scheduler(run_now=args.run_now)


if __name__ == "__main__":
    main()
