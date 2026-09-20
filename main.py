from __future__ import annotations

import argparse


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    mission = sub.add_parser("mission"); mission.add_argument("hypothesis"); mission.add_argument("--no-ai", action="store_true"); mission.add_argument("--viz", action="store_true")
    queue = sub.add_parser("queue"); queue.add_argument("--n", type=int); queue.add_argument("--no-ai", action="store_true")
    indicators = sub.add_parser("indicators"); indicators.add_argument("--source")
    fetch = sub.add_parser("fetch"); fetch.add_argument("--quick", action="store_true"); fetch.add_argument("--all", action="store_true")
    sub.add_parser("selftest"); sub.add_parser("ui"); viz = sub.add_parser("viz"); viz.add_argument("mission_id")
    args = parser.parse_args()
    if args.command == "mission":
        from warsignal.mission.runner import run_mission
        print(run_mission(args.hypothesis, use_ai=not args.no_ai, viz=args.viz).narrative_md)
    elif args.command == "queue":
        from warsignal.mission.harness import run_queue
        run_queue(args.n, use_ai=not args.no_ai)
    elif args.command == "indicators":
        from warsignal.indicators import list_indicators
        for spec in list_indicators(args.source):
            print(spec.name)
    elif args.command == "fetch":
        from warsignal.fetch.all import run
        run(quick=args.quick)
    elif args.command == "selftest":
        from warsignal.config import env
        from warsignal.indicators import list_indicators
        print(f"OPENAI_API_KEY={'set' if env('OPENAI_API_KEY') else 'missing'}")
        print(f"TYPESAFE_API_KEY={'set' if env('TYPESAFE_API_KEY') else 'missing'}")
        print(f"judge={'jev' if env('TYPESAFE_API_KEY') else ('openai-fallback' if env('OPENAI_API_KEY') else 'heuristic')}")
        print(f"indicators={len(list_indicators())}")
    else:
        print("not yet implemented")


if __name__ == "__main__":
    main()
