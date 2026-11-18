#!/usr/bin/env -S uv run --quiet --locked
"""Build the instrumentation fixture, and check its components locally or in a run.

    fixture.py build           build every image
    fixture.py check-local     run each language's local instrumentation check on the images
    fixture.py check-run RUN   compare `snouty runs modules RUN` with what each component should load
    fixture.py export DIR      copy the build files without the answers, for a blind triage session

Each command prints one row per component, with what was expected and what was found, and
exits 1 if any row differs. Run it where Docker can build linux/amd64 images, and, for
check-run, where snouty is logged in. See README.md for launching the fixture.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Neutral names throughout (images, containers, modules), so an agent triaging a run of the
# fixture can't tell the broken builds from their names.
TAG = "shop"


@dataclass
class Component:
    container: str
    context: str  # build context directory
    program: str  # path of the program or launcher in the image
    check: str  # which local check applies: go, native, java, dotnet, node, python
    healthy: bool  # whether the local check should pass
    modules: list[str]  # module names the run should list in this container
    what: str  # what this component is, for the reports
    args: dict[str, str] = field(default_factory=dict)


COMPONENTS = [
    Component(
        "driver",
        "go",
        "/usr/local/bin/driver",
        "go",
        True,
        ["shop/cmd/driver", "shop/internal/work"],
        "Go, toolexec",
        {"TEST_TEMPLATE": "1"},
    ),
    Component(
        "orders",
        "go",
        "/usr/local/bin/orders",
        "go",
        True,
        ["shop/cmd/orders", "shop/internal/work"],
        "Go, toolexec, shares shop/internal/work with the driver",
    ),
    Component(
        "ledger",
        "ledger",
        "/usr/local/bin/ledger",
        "go",
        False,
        [],
        "Go, -default-no-op SDK with -tags on the command line",
    ),
    Component(
        "pricing",
        "rust",
        "/usr/local/bin/rust-service",
        "native",
        True,
        ["rust-service"],
        "Rust, rustflags and release debug info",
    ),
    Component(
        "search",
        "rust",
        "/usr/local/bin/rust-service",
        "native",
        False,
        [],
        "Rust, no coverage rustflags",
        {"FLAGS": "0"},
    ),
    Component(
        "shipping",
        "rust",
        "/usr/local/bin/rust-service",
        "native",
        False,
        ["rust-service"],
        "Rust, no release debug info",
        {"DEBUG": "0"},
    ),
    Component(
        "cache",
        "cpp",
        "/usr/local/bin/cpp-service",
        "native",
        True,
        ["cpp-service"],
        "C++, header and coverage flags",
    ),
    Component(
        "index",
        "cpp",
        "/usr/local/bin/cpp-service",
        "native",
        False,
        [],
        "C++, header without the coverage flags",
        {"FLAGS": "0"},
    ),
    Component(
        "billing",
        "java",
        "/usr/local/bin/java-service",
        "java",
        True,
        ["java-service"],
        "Java, com.antithesis:ffi on the classpath",
    ),
    Component(
        "audit",
        "java",
        "/usr/local/bin/java-service",
        "java",
        False,
        [],
        "Java, no com.antithesis:ffi: crashes at startup",
        {"FFI": "0"},
    ),
    Component("accounts", "dotnet", "/usr/share/dotnet/dotnet", "dotnet", True, ["DotnetService"], ".NET"),
    Component("web", "node", "/usr/local/bin/node", "node", True, ["node-service"], "JavaScript"),
    Component(
        "reports",
        "python",
        "/usr/local/bin/python-service",
        "python",
        True,
        ["python-service"],
        "Python, antithesis package, python -m antithesis",
    ),
    Component(
        "alerts",
        "python",
        "/usr/local/bin/python-service",
        "python",
        False,
        [],
        "Python, no SDK: no coverage",
        {"SDK": "0"},
    ),
]


def image(c: Component) -> str:
    return f"{TAG}-{c.container}:latest"


def sh(*cmd: str, check: bool = True) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        sys.exit(f"{' '.join(cmd)} failed:\n{result.stderr.strip()}")
    return result.stdout


def latest_cpp_sdk_tag() -> str:
    out = sh("git", "ls-remote", "--tags", "--refs", "https://github.com/antithesishq/antithesis-sdk-cpp")
    tags = re.findall(r"refs/tags/(v\d+\.\d+\.\d+)$", out, re.MULTILINE)
    return max(tags, key=lambda t: tuple(int(n) for n in t[1:].split(".")))


def build(_: argparse.Namespace) -> int:
    cpp_tag = latest_cpp_sdk_tag()
    for c in COMPONENTS:
        args = dict(c.args)
        if c.context == "cpp":
            args["SDK_TAG"] = cpp_tag
        flags = [f"--build-arg={k}={v}" for k, v in args.items()]
        print(f"building {image(c)}", flush=True)
        sh(
            "docker",
            "build",
            "--platform",
            "linux/amd64",
            "-q",
            # Every image installs the latest SDKs and tools, so never reuse a cached layer.
            "--pull",
            "--no-cache",
            "-t",
            image(c),
            *flags,
            str(HERE / c.context),
        )
    return 0


# The setup properties' counterexamples a run of the fixture should report: for the symbols
# property, (binary, reason) pairs, and for build errors, the error codes.
EXPECTED_PROPERTIES = {
    "every instrumented module has symbols": {
        ("cpp-service", "not coverage-instrumented"),
        ("rust-service", "not coverage-instrumented"),
        ("rust-service", "no source locations"),
    },
    "No Antithesis build errors": {("code", "4010")},
}


def property_findings(run_id: str, name: str) -> set[tuple[str, str]] | None:
    """A setup property's counterexamples, in the shape of EXPECTED_PROPERTIES, or None
    if the run hasn't reported the property yet."""
    out = sh("snouty", "runs", "properties", run_id, "--name", name, "--json", check=False).strip()
    if not out:
        return None
    prop = json.loads(out.splitlines()[0])
    found: set[tuple[str, str]] = set()
    stack = list(prop.get("counterexamples") or [])
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)
        elif "binary" in item:
            reason = item.get("reason", "")
            key = "no source locations" if "no source locations" in reason else reason.split(",")[0]
            found.add((Path(item["binary"]).name, key))
        elif "code" in item:
            found.add(("code", str(item["code"])))
    return found


def run_in(img: str, script: str) -> str:
    return sh(
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "--entrypoint",
        "sh",
        img,
        "-c",
        script,
        check=False,
    )


def copy_out(img: str, path: str, dest: Path) -> Path:
    cid = sh("docker", "create", "--platform", "linux/amd64", img).strip()
    try:
        sh("docker", "cp", f"{cid}:{path}", str(dest))
    finally:
        sh("docker", "rm", cid)
    return dest


def elf_tool(tool_image: str, binary: Path, script: str) -> str:
    return sh("docker", "run", "--rm", "-v", f"{binary}:/b:ro", tool_image, "sh", "-c", script, check=False)


def local_check(c: Component, tmp: Path) -> tuple[bool, str]:
    img = image(c)
    if c.check == "go":
        binary = copy_out(img, c.program, tmp / c.container)
        n = elf_tool(
            "golang:1-trixie", binary, "go tool nm /b | grep -c 'voidstarHandler).init_coverage'"
        ).strip()
        return n not in ("", "0"), f"init_coverage count {n or 0}"
    if c.check == "native":
        binary = copy_out(img, "/symbols/" + Path(c.program).name, tmp / c.container)
        out = elf_tool(
            "rust:1-trixie",
            binary,
            "echo nm=$(nm /b | grep -c ' T antithesis_load_libvoidstar');"
            " echo sancov=$(readelf -S /b | grep -c '__sancov_');"
            " echo debug=$(readelf -S /b | grep -c '.debug_info')",
        )
        found = dict(line.split("=") for line in out.split() if "=" in line)
        counts = [found.get(k, "") for k in ("nm", "sancov", "debug")]
        # A tool container that didn't run leaves the counts missing: that's a failure too.
        ok = all(n.isdigit() and int(n) > 0 for n in counts)
        return (
            ok,
            f"libvoidstar {found.get('nm')}, sancov sections {found.get('sancov')}, debug_info {found.get('debug')}",
        )
    catalog = run_in(img, "ls -L /opt/antithesis/catalog/ 2>&1").split()
    if c.check == "java":
        launcher = run_in(img, f"cat {c.program}")
        ok = any(f.endswith(".jar") for f in catalog) and "ffi" in launcher
        return ok, f"catalog {' '.join(catalog)}; ffi on classpath: {'ffi' in launcher}"
    if c.check == "dotnet":
        return any(f.endswith(".dll") for f in catalog), f"catalog {' '.join(catalog)}"
    if c.check == "node":
        return "node_modules" in catalog, f"catalog {' '.join(catalog)}"
    if c.check == "python":
        sdk = run_in(img, "python -c 'import antithesis' 2>/dev/null && echo yes || echo no").strip()
        launcher = run_in(img, f"cat {c.program}")
        ok = sdk == "yes" and "-m antithesis" in launcher
        return ok, f"antithesis importable: {sdk}; started with -m antithesis: {'-m antithesis' in launcher}"
    raise ValueError(c.check)


def check_local(_: argparse.Namespace) -> int:
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        for c in COMPONENTS:
            ok, detail = local_check(c, Path(d))
            match = ok == c.healthy
            bad += not match
            want = "pass" if c.healthy else "fail"
            print(
                f"{'ok ' if match else 'BAD'}  {c.container:12} expected {want:4}  got {'pass' if ok else 'fail'}  ({detail})"
            )
    return 1 if bad else 0


def check_run(a: argparse.Namespace) -> int:
    raw = sh("snouty", "runs", "modules", a.run_id, "--detail", "--json")
    loaded: dict[str, set[str]] = {}
    for line in raw.splitlines():
        module = json.loads(line)
        for instance in module.get("instances") or []:
            loaded.setdefault(instance["container_name"], set()).add(module["name"])
    bad = 0
    for c in COMPONENTS:
        found = sorted(loaded.get(c.container, set()))
        match = set(found) == set(c.modules)
        bad += not match
        print(
            f"{'ok ' if match else 'BAD'}  {c.container:12} expected {c.modules or 'no module'}  got {found or 'no module'}"
            + f"  ({c.what})"
        )
    print()
    for name, want in EXPECTED_PROPERTIES.items():
        got = property_findings(a.run_id, name)
        if got is None:
            print(f"wait {name:40} not reported yet: it appears near the end of the run")
            continue
        match = got == want
        bad += not match
        print(f"{'ok ' if match else 'BAD'}  {name:40} expected {sorted(want)}  got {sorted(got)}")
    return 1 if bad else 0


def export(a: argparse.Namespace) -> int:
    """Copy what a user's checkout would hold: the sources, Dockerfiles without their
    comments, and the compose file. Leave out this script and the README, which name the
    broken builds."""
    dest = Path(a.dir)
    if dest.exists():
        sys.exit(f"{dest} exists")
    for c in sorted({c.context for c in COMPONENTS}) + ["config"]:
        shutil.copytree(HERE / c, dest / c, ignore=shutil.ignore_patterns("__pycache__"))
    for dockerfile in dest.rglob("Dockerfile"):
        lines = dockerfile.read_text().splitlines(keepends=True)
        dockerfile.write_text("".join(line for line in lines if not line.lstrip().startswith("#")))
    print(f"exported to {dest}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)
    sub.add_parser("build", help="build every image").set_defaults(func=build)
    sub.add_parser("check-local", help="run the local checks on the images").set_defaults(func=check_local)
    run = sub.add_parser("check-run", help="compare a run's modules with the expected ones")
    run.add_argument("run_id")
    run.set_defaults(func=check_run)
    exp = sub.add_parser("export", help="copy the build files, without the answers, for a blind triage")
    exp.add_argument("dir")
    exp.set_defaults(func=export)
    a = p.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    main()
