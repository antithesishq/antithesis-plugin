#!/usr/bin/env -S uv run --quiet --locked
"""Token usage and cost per session, task and target, and compute per Antithesis run, for one eval.

    cost_report.py DATA_DIR [--ch-price 2.50]

Reads, under DATA_DIR:
    notes/sessions.json   NAME -> {"id": session id, "target": profile, ...}, from `evalctl.py start`
    transcripts/          raw Claude transcripts (`evalctl.py sync`), subagents included, and
                          Codex rollouts in transcripts/codex/, found by logs/NAME.thread
    runs/usage.json       billed compute hours per run (`evalctl.py usage`)
    runs/runs.json        the run log (`evalctl.py runlog`): {run_id: {"session", "purpose", "cap", "task"}}
    notes/tasks.json      optional: [{"id", "session", "label", "start", "end"}], RFC 3339 times.
                          An API call belongs to the task of its session whose window holds
                          its timestamp; calls outside every window go to "<session>:other".
Writes report/cost.json and report/cost.md.

One API response is split across several transcript lines, one per content block, each
repeating the same usage, so usage is deduplicated by message id within each file. A run
that `runs usage` doesn't list yet counts at its cap, and is marked as not billed yet.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Don't leave a __pycache__ in the skill: every file in it must be one the skill names.
sys.dont_write_bytecode = True
from evalctl import read_jsonl

# $ per million tokens. Check the current prices before a report, and add any model
# the sessions used. cw5m/cw1h are cache writes with a 5-minute / 1-hour TTL.
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cw5m": 5.00, "cw1h": 8.00, "cr": 0.20},
}
DEFAULT_MODEL = "claude-opus-5-5"
# Models whose price we don't know, such as Codex models behind a proxy: their tokens
# are counted and their token cost is left at 0.
UNPRICED = ("gpt-",)


def calls_in(path: Path) -> list[dict]:
    """The deduplicated API calls in one transcript file."""
    seen: dict[str, dict] = {}
    with open(path) as f:
        # Only assistant lines carry usage; skip the rest before decoding them.
        for e in read_jsonl(line for line in f if '"usage"' in line):
            m = e.get("message") or {}
            if e.get("type") == "assistant" and m.get("usage") and m.get("id"):
                seen.setdefault(m["id"], {"ts": e["timestamp"], "model": m.get("model"), "usage": m["usage"]})
    return list(seen.values())


def codex_calls_in(path: Path) -> list[dict]:
    """The API calls in one Codex rollout, with Claude-shaped usage, and the model of their turn."""
    calls, model = [], None
    with open(path) as f:
        for e in read_jsonl(f):
            p = e.get("payload") or {}
            if e.get("type") == "turn_context":
                model = p.get("model") or model
            elif e.get("type") == "token_usage_record" and p.get("usage"):
                u = p["usage"]
                cached = u.get("cached_input_tokens") or 0
                usage = {
                    # OpenAI counts cached tokens inside input_tokens.
                    "input_tokens": (u.get("input_tokens") or 0) - cached,
                    "output_tokens": u.get("output_tokens") or 0,
                    "cache_creation_input_tokens": u.get("cache_write_input_tokens") or 0,
                    "cache_read_input_tokens": cached,
                }
                calls.append({"ts": e["timestamp"].replace("Z", "+00:00"), "model": model, "usage": usage})
    return calls


def codex_subagents(root: Path, tid: str) -> list[Path]:
    """The rollouts of every subagent that thread tid spawned, at any depth."""
    children: dict[str, list[Path]] = defaultdict(list)
    for f in root.glob("**/rollout-*.jsonl"):
        with open(f) as lines:
            meta = next(read_jsonl(lines), {})
        source = (meta.get("payload") or {}).get("source")
        spawn = (source.get("subagent") or {}).get("thread_spawn") if isinstance(source, dict) else None
        if spawn:
            children[spawn["parent_thread_id"]].append(f)
    found, todo = [], [tid]
    while todo:
        for f in children.pop(todo.pop(), []):
            found.append(f)
            todo.append(f.stem[-36:])
    return found


def cost(call: dict, warned: set) -> Counter:
    u, model = call["usage"], call["model"] or "?"
    if model.startswith(UNPRICED):
        if model not in warned:
            warned.add(model)
            print(f"warning: no price for {model}; counting its tokens at $0", file=sys.stderr)
        p = dict.fromkeys(("input", "output", "cw5m", "cw1h", "cr"), 0.0)
    elif model not in PRICES and model not in warned:
        warned.add(model)
        print(f"warning: no price for {model}; using {DEFAULT_MODEL}'s", file=sys.stderr)
    else:
        p = PRICES.get(model, PRICES[DEFAULT_MODEL])
    cw1h = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens") or 0
    row = Counter(
        calls=1,
        input=u.get("input_tokens") or 0,
        output=u.get("output_tokens") or 0,
        cache_write_5m=(u.get("cache_creation_input_tokens") or 0) - cw1h,
        cache_write_1h=cw1h,
        cache_read=u.get("cache_read_input_tokens") or 0,
    )
    row["token_usd"] = (
        row["input"] * p["input"]
        + row["output"] * p["output"]
        + row["cache_write_5m"] * p["cw5m"]
        + row["cache_write_1h"] * p["cw1h"]
        + row["cache_read"] * p["cr"]
    ) / 1e6
    return row


def table(headers: list[str], rows: list[list]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "---|" * len(headers),
        *("| " + " | ".join(str(c) for c in r) + " |" for r in rows),
    ]


def tok(x: float) -> str:
    return f"{x / 1e6:.2f}M" if x >= 1e5 else f"{x / 1e3:.1f}K"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("data", type=Path)
    p.add_argument("--ch-price", type=float, default=2.50, help="$ per Antithesis compute hour")
    a = p.parse_args()
    d = a.data.resolve()

    def load(rel: str, default):
        f = d / rel
        return json.loads(f.read_text()) if f.exists() else default

    sessions = load("notes/sessions.json", {})
    tasks = load("notes/tasks.json", [])
    usage = {r["run_id"]: r["hours"] for r in load("runs/usage.json", [])}
    runs = load("runs/runs.json", {})

    # Each session's task windows, parsed once. A task with no end runs to the end.
    windows = defaultdict(list)
    for t in tasks:
        end = datetime.fromisoformat(t["end"]) if t.get("end") else None
        windows[t["session"]].append((datetime.fromisoformat(t["start"]), end, t["id"]))

    def task_of(session: str, when: datetime) -> str:
        for start, end, tid in windows[session]:
            if start <= when and (end is None or when < end):
                return tid
        return f"{session}:other"

    warned: set = set()
    per_session: dict = defaultdict(Counter)
    per_task: dict = defaultdict(Counter)
    for name, s in sessions.items():
        thread = d / "logs" / f"{name}.thread"
        if s.get("harness") == "codex" and thread.exists():
            tid = thread.read_text().strip()
            rollouts = list((d / "transcripts" / "codex").glob(f"**/rollout-*-{tid}.jsonl"))
            if not rollouts:
                print(f"warning: no rollout for session {name} ({tid})", file=sys.stderr)
            subagents = codex_subagents(d / "transcripts" / "codex", tid)
            per_session[name]["subagents"] = len(subagents)
            rollouts += subagents
            for f in rollouts:
                for c in codex_calls_in(f):
                    row = cost(c, warned)
                    per_session[name] += row
                    per_task[task_of(name, datetime.fromisoformat(c["ts"]))] += row
            continue
        files = list((d / "transcripts").glob(f"*/{s['id']}.jsonl"))
        if not files:
            print(f"warning: no transcript for session {name} ({s['id']})", file=sys.stderr)
            continue
        subagents = sorted((files[0].parent / s["id"] / "subagents").glob("*.jsonl"))
        per_session[name]["subagents"] = len(subagents)
        for f in [files[0], *subagents]:
            for c in calls_in(f):
                row = cost(c, warned)
                per_session[name] += row
                per_task[task_of(name, datetime.fromisoformat(c["ts"]))] += row

    run_rows = []
    for rid, info in runs.items():
        hours = usage.get(rid, float(info.get("cap", 0)))
        run_rows.append({"run_id": rid, **info, "hours": hours, "billed": rid in usage})
        compute = Counter(compute_hours=hours, compute_usd=hours * a.ch_price)
        if info.get("session"):
            per_session[info["session"]] += compute
        if info.get("task"):
            per_task[info["task"]] += compute
    per_target: dict = defaultdict(Counter)
    for name, v in per_session.items():
        per_target[sessions.get(name, {}).get("target") or "(none)"] += v
    for agg in (per_session, per_task, per_target):
        for v in agg.values():
            v["total_usd"] = v["token_usd"] + v["compute_usd"]

    totals = sum(per_session.values(), Counter())
    labels = {t["id"]: t["label"] for t in tasks}
    (d / "report").mkdir(exist_ok=True)
    report = {
        "ch_price": a.ch_price,
        "prices_per_mtok": PRICES,
        "sessions": per_session,
        "tasks": {k: {"label": labels.get(k, k), **v} for k, v in per_task.items()},
        "targets": per_target,
        "runs": run_rows,
        "totals": totals,
    }
    (d / "report/cost.json").write_text(json.dumps(report, indent=2) + "\n")

    def money(v: Counter) -> list:
        return [
            f"{v['token_usd']:.2f}",
            f"{v['compute_hours']:.1f}",
            f"{v['compute_usd']:.2f}",
            f"{v['total_usd']:.2f}",
        ]

    cols = ["Tokens $", "CH", "Compute $", "Total $"]
    session_rows = [
        [n, v["calls"], tok(v["input"]), tok(v["output"])]
        + [tok(v["cache_write_5m"] + v["cache_write_1h"]), tok(v["cache_read"]), *money(v)]
        for n, v in per_session.items()
    ]
    run_table = [
        [f"`{r['run_id'][:8]}`", r.get("session", ""), r.get("task", ""), r.get("purpose", "")]
        + [r.get("cap", ""), f"{r['hours']:.1f}", "yes" if r["billed"] else "cap (not billed yet)"]
        + [f"{r['hours'] * a.ch_price:.2f}"]
        for r in run_rows
    ]
    lines = ["# Cost report", "", f"Compute at ${a.ch_price:.2f} per compute hour.", "", "## Per session", ""]
    lines += table(["Session", "Calls", "Input", "Output", "Cache write", "Cache read", *cols], session_rows)
    if set(per_target) != {"(none)"}:
        lines += ["", "## Per target", ""]
        lines += table(["Target", *cols], [[t, *money(v)] for t, v in per_target.items()])
    lines += ["", "## Per task", ""]
    lines += table(
        ["Task", "Label", "Calls", *cols],
        [[k, labels.get(k, k), v["calls"], *money(v)] for k, v in per_task.items()],
    )
    lines += ["", "## Per run", ""]
    lines += table(["Run", "Session", "Task", "Purpose", "Cap", "CH", "Billed?", "Compute $"], run_table)
    lines += [
        "",
        (
            f"**Total:** tokens ${totals['token_usd']:.2f} + compute {totals['compute_hours']:.1f} CH "
            f"(${totals['compute_usd']:.2f}) = **${totals['total_usd']:.2f}**"
        ),
    ]
    (d / "report/cost.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
