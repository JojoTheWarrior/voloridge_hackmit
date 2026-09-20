from __future__ import annotations

import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    mission = sub.add_parser("mission"); mission.add_argument("hypothesis"); mission.add_argument("--no-ai", action="store_true"); mission.add_argument("--viz", action="store_true"); mission.add_argument("--show", action="store_true"); mission.add_argument("--dry-run", action="store_true"); mission.add_argument("--publish", action="store_true"); mission.add_argument("--brain", choices=("devin", "openai", "heuristic")); mission.add_argument("--detach", action="store_true")
    mission.add_argument("--mission-id"); mission.add_argument("--status", action="store_true", help="write missions/status/<mission-id>.json at each stage")
    status = sub.add_parser("status", help="update a Round 2 mission status file (SCHEMA.md)"); status.add_argument("mission_id")
    status.add_argument("--hypothesis"); status.add_argument("--title"); status.add_argument("--parent"); status.add_argument("--session-url")
    status.add_argument("--state", choices=("queued", "running", "done", "failed")); status.add_argument("--stage"); status.add_argument("--message")
    status.add_argument("--followup", help="append one R2 follow-up hypothesis to missions/queue.txt")
    status.add_argument("--push", action="store_true", help="commit only the status file (+queue if --followup) and push")
    queue = sub.add_parser("queue"); queue.add_argument("--n", type=int); queue.add_argument("--no-ai", action="store_true"); queue.add_argument("--viz", action="store_true"); queue.add_argument("--max-retries", type=int, default=1); queue.add_argument("--publish", action="store_true"); queue.add_argument("--brain", choices=("devin", "openai", "heuristic")); queue.add_argument("--detach", action="store_true")
    queue.add_argument("--reset", action="store_true"); queue.add_argument("--requeue-failed", action="store_true")
    queue.add_argument("--add", metavar="HYPOTHESIS", help="append a hypothesis to missions/queue.txt (Kingdom shows it under Queued Missions)")
    queue.add_argument("--round", help="prefix the added line with a round tag, e.g. R2")
    queue.add_argument("--push", action="store_true", help="with --add: commit queue.txt and push so other machines/agents see it")
    indicators = sub.add_parser("indicators"); indicators.add_argument("--source")
    fetch = sub.add_parser("fetch"); fetch.add_argument("--quick", action="store_true"); fetch.add_argument("--all", action="store_true")
    fetch.add_argument("--rebuild-cache", action="store_true")
    sub.add_parser("selftest")
    ui = sub.add_parser("ui"); ui.add_argument("--port", type=int, default=8000)
    graph = sub.add_parser("graph"); graph.add_argument("--port", type=int, default=8010)
    graph.add_argument("--charts-port", type=int, default=8011)
    viz = sub.add_parser("viz"); viz.add_argument("mission_id"); viz.add_argument("--headless", action="store_true")
    viz.add_argument("--codegen", action="store_true"); viz.add_argument("--allow-exec", action="store_true")
    serve = sub.add_parser("serve", help="run the web app's API server"); serve.add_argument("--port", type=int, default=8030)
    serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--db", default=".kingdom/kingdom.db")
    sub.add_parser("kingdom", add_help=False)
    args, extra = parser.parse_known_args()
    if args.command == "kingdom":
        from kingdom.app import main as kingdom_main

        kingdom_main(extra)
        return
    if extra:
        parser.error(f"unrecognized arguments: {' '.join(extra)}")
    if args.command == "mission":
        if args.detach:
            from warsignal.ai.devin_client import BrainUnavailable
            from warsignal.mission.detach import spawn_mission_agent

            try:
                _, url = spawn_mission_agent(
                    args.hypothesis,
                    brain_backend=args.brain or ("heuristic" if args.no_ai else None),
                )
            except BrainUnavailable as exc:
                print(f"mission detach unavailable: {exc}")
                return
            print(f"mission started: {url}")
            return
        from warsignal.mission.planner import plan_mission
        if args.dry_run:
            import json
            plan, _ = plan_mission(args.hypothesis, use_ai=not args.no_ai, brain_backend=args.brain)
            print(json.dumps(plan.__dict__, indent=2))
        else:
            from warsignal.mission.runner import run_mission
            from warsignal.mission.results import append_result
            result = run_mission(
                args.hypothesis, mission_id=args.mission_id, use_ai=not args.no_ai, viz=args.viz,
                show=args.show, publish=args.publish, brain_backend=args.brain, status=args.status,
            )
            append_result(result)
            print(result.narrative_md)
    elif args.command == "status":
        import json
        from warsignal.mission import status as st
        if st.read_status(args.mission_id) is None:
            st._atomic_write(st.status_path(args.mission_id), st.new_status(
                args.mission_id, args.hypothesis or "", title=args.title, parent_mission_id=args.parent,
                agent_session_url=args.session_url))
        current = st.update_status(
            args.mission_id, hypothesis=args.hypothesis, title=args.title, parent_mission_id=args.parent,
            agent_session_url=args.session_url, state=args.state, stage=args.stage, message=args.message,
        )
        extra = []
        if args.followup:
            st.append_followup(args.mission_id, args.followup)
            extra.append(st.QUEUE)
        if args.push:
            st.publish_status(args.mission_id, extra_paths=extra)
        print(json.dumps(st.read_status(args.mission_id) or current, indent=2))
    elif args.command == "queue":
        if args.add:
            from warsignal.mission import queue as q
            from warsignal.mission.status import QUEUE, git_publish

            line = q.add(args.add, round_tag=args.round)
            if line is None:
                print("already queued")
            else:
                print(f"queued: {line}")
                if args.push:
                    print("pushed" if git_publish([QUEUE], f"queue: {line[:60]}") else "push skipped")
            return
        if args.detach:
            from warsignal.ai.devin_client import BrainUnavailable
            from warsignal.mission.detach import spawn_mission_agent
            from warsignal.mission.queue import pop_next

            count = args.n if args.n is not None else 1
            for _ in range(count):
                hypothesis = pop_next()
                if hypothesis is None:
                    break
                try:
                    _, url = spawn_mission_agent(
                        hypothesis,
                        brain_backend=args.brain or ("heuristic" if args.no_ai else None),
                    )
                except BrainUnavailable as exc:
                    print(f"mission detach unavailable: {exc}")
                    break
                print(f"mission started: {url}")
            return
        from warsignal.mission.harness import requeue_failed_missions, reset_queue, run_queue
        if args.reset:
            reset_queue()
            print("queue reset")
        if args.requeue_failed:
            print(f"requeued {requeue_failed_missions()} failed missions")
        if not args.reset and not args.requeue_failed:
            run_queue(
                args.n,
                use_ai=not args.no_ai,
                viz=args.viz,
                max_retries=args.max_retries,
                publish=args.publish,
                brain_backend=args.brain,
            )
    elif args.command == "indicators":
        from warsignal.indicators import list_indicators
        for spec in list_indicators(args.source):
            print(spec.name)
    elif args.command == "fetch":
        from warsignal.fetch.all import run
        run(quick=args.quick)
        if args.rebuild_cache:
            from warsignal.indicators.gdelt import rebuild_cache
            print(f"GDELT cache rebuilt: {rebuild_cache().shape}")
    elif args.command == "selftest":
        from warsignal.config import env
        from warsignal.indicators import list_indicators
        print(f"OPENAI_API_KEY={'set' if env('OPENAI_API_KEY') else 'missing'}")
        print(f"TYPESAFE_API_KEY={'set' if env('TYPESAFE_API_KEY') else 'missing'}")
        print(f"judge={'jev' if env('TYPESAFE_API_KEY') else ('openai-fallback' if env('OPENAI_API_KEY') else 'heuristic')}")
        print(f"indicators={len(list_indicators())}")
    elif args.command == "viz":
        import json
        from pathlib import Path
        from warsignal.viz.agent import design_viz
        from warsignal.viz.pygame_viz import render

        report = Path("missions/reports") / f"{args.mission_id}.json"
        result = json.loads(report.read_text(encoding="utf-8"))
        spec = design_viz(result, codegen=args.codegen, allow_exec=args.allow_exec)
        target = Path("missions/reports") / f"{args.mission_id}.png"
        path = render(spec, report, target, interactive=not args.headless)
        result.setdefault("artifacts", {})["viz_path"] = str(target)
        report.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        print(path or target)
    elif args.command == "ui":
        from warsignal.ui.app import create_app
        create_app().run(host="0.0.0.0", port=args.port)
    elif args.command == "graph":
        import subprocess
        import sys
        from warsignal.config import ROOT
        from warsignal.graph.app import create_app
        from warsignal.graph.service import GraphService
        charts = subprocess.Popen([sys.executable, "charts.py", "--port", str(args.charts_port)], cwd=ROOT)
        try:
            service = GraphService(charts_url=f"http://127.0.0.1:{args.charts_port}")
            create_app(service).run(host="127.0.0.1", port=args.port)
        finally:
            charts.terminate()
    elif args.command == "serve":
        from server import app as server_app
        server_app.serve(host=args.host, port=args.port, db=args.db)
    else:
        print("not yet implemented")


if __name__ == "__main__":
    main()
