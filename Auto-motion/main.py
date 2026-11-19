import argparse
from src.camera import run_camera


def main():
    parser = argparse.ArgumentParser(
        description="AUTO-MOTION Exercise Tracking"
    )

    parser.add_argument(
        "--mode",
        choices=["shoulder", "chest"],
        default="shoulder",
        help="Exercise to track"
    )

    parser.add_argument(
        "--no-arduino",
        action="store_true",
        help="Run without connecting to Arduino"
    )

    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Arduino serial port (e.g. COM3)"
    )

    args = parser.parse_args()

    if args.no_arduino and args.port:
        parser.error("Use either --no-arduino or --port, not both.")

    if not args.no_arduino and args.port is None:
        parser.error("Specify --no-arduino or --port COMx.")

    run_camera()


if __name__ == "__main__":
    main()