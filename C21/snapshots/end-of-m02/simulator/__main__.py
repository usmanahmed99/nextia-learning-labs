"""Run the simulated AI provider:  python -m simulator [--port 8300] [--mode normal]"""

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="The simulated AI provider (OpenAI-compatible).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SIM_PORT", "8300")))
    parser.add_argument("--mode", choices=["normal", "slow", "outage", "quota"])
    parser.add_argument("--speed", type=float, help="multiply every time by this (default 1)")
    args = parser.parse_args()
    if args.mode:
        os.environ["SIM_MODE"] = args.mode
    if args.speed is not None:
        os.environ["SIM_SPEED"] = str(args.speed)
    from simulator.app import create_app

    print(
        f"Simulated AI provider on http://{args.host}:{args.port}/v1 "
        f"(mode {os.environ.get('SIM_MODE', 'normal')}). Its times and quota come from real "
        "recorded calls; its answers are simple. Stop it with Ctrl+C."
    )
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
