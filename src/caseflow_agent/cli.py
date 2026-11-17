import argparse
import json
import os
import sys

from pydantic import ValidationError

from .backends import OpenAIBackend
from .models import Review, Ticket
from .service import AgentService


def main():
    parser = argparse.ArgumentParser(description="CaseFlow synthetic support-agent demo")
    parser.add_argument("--db", default=".caseflow/state.sqlite")
    parser.add_argument("--backend", choices=["offline", "openai"], default="offline")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", ""))
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("question")
    run.add_argument("--thread")
    run.add_argument("--order-id")
    show = sub.add_parser("show")
    show.add_argument("thread")
    resume = sub.add_parser("review")
    resume.add_argument("thread")
    group = resume.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve", action="store_true")
    group.add_argument("--reject", action="store_true")
    resume.add_argument("--note", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        backend = OpenAIBackend(args.model) if args.backend == "openai" else None
        if args.command == "serve":
            import uvicorn

            from .api import create_app
            uvicorn.run(create_app(args.db, backend), host="127.0.0.1", port=args.port)
            return
        with AgentService(args.db, backend) as service:
            if args.command == "run":
                result = service.start(Ticket(question=args.question, order_id=args.order_id), args.thread)
            elif args.command == "show":
                result = service.get(args.thread)
            else:
                result = service.resume(args.thread, Review(approve=args.approve, note=args.note))
        print(json.dumps(result, indent=2))
    except (ValueError, ValidationError, ImportError) as exc:
        print(f"caseflow: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()

