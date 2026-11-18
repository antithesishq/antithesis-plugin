#!/usr/bin/env -S uv run --quiet --locked
"""Build the instrumentation fixture, and check its components locally or in a run.

    fixture.py build           build every image
    fixture.py check-local     run each language's local instrumentation check on the images
    fixture.py check-run RUN   compare `snouty runs modules RUN` with what each component should load

Each command prints one row per component, with what was expected and what was found, and
exits 1 if any row differs. Run it where Docker can build linux/amd64 images, and, for
check-run, where snouty is logged in. See README.md for launching the fixture.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAG = "instr-fixture"


@dataclass
class Component:
    container: str
    image: str  # image name suffix: instr-fixture-<image>
    context: str  # build context directory
    program: str  # path of the program or launcher in the image
    check: str  # which local check applies: go, native, java, dotnet, node, python
    healthy: bool  # whether the local check should pass
    modules: list[str]  # module names the run should list in this container
    args: dict[str, str] = field(default_factory=dict)
    note: str = ""


COMPONENTS = [
    Component(
        "driver",
        "go-driver",
        "go",
        "/usr/local/bin/driver",
        "go",
        True,
        ["instrfixture/cmd/driver", "instrfixture/internal/work"],
        {"TEST_TEMPLATE": "1"},
    ),
    Component(
        "goworker",
        "go-worker",
        "go",
        "/usr/local/bin/worker",
        "go",
        True,
        ["instrfixture/cmd/worker", "instrfixture/internal/work"],
    ),
    Component(
        "gonoop",
        "go-noop",
        "gonoop",
        "/usr/local/bin/gonoop",
        "go",
        False,
        [],
        note="-default-no-op SDK, -tags on the command line",
    ),
    Component("rustok", "rust-ok", "rust", "/usr/local/bin/rustfixture", "native", True, ["rustfixture"]),
    Component(
        "rustnoflags",
        "rust-noflags",
        "rust",
        "/usr/local/bin/rustfixture",
        "native",
        False,
        [],
        {"FLAGS": "0"},
        "no coverage rustflags",
    ),
    Component(
        "rustnodebug",
        "rust-nodebug",
        "rust",
        "/usr/local/bin/rustfixture",
        "native",
        False,
        ["rustfixture"],
        {"DEBUG": "0"},
        "no debug info: its symbol catalog has no source locations",
    ),
    Component("cppok", "cpp-ok", "cpp", "/usr/local/bin/cppfixture", "native", True, ["cppfixture"]),
    Component(
        "cppnoflags",
        "cpp-noflags",
        "cpp",
        "/usr/local/bin/cppfixture",
        "native",
        False,
        [],
        {"FLAGS": "0"},
        "header without the coverage flags",
    ),
    Component("java", "java", "java", "/usr/local/bin/javafixture", "java", True, ["javafixture"]),
    Component(
        "javanoffi",
        "java-noffi",
        "java",
        "/usr/local/bin/javafixture",
        "java",
        False,
        [],
        {"FFI": "0"},
        "no com.antithesis:ffi: crashes at startup",
    ),
    Component("dotnet", "dotnet", "dotnet", "/usr/share/dotnet/dotnet", "dotnet", True, ["dotnetfixture"]),
    Component("node", "node", "node", "/usr/local/bin/node", "node", True, ["nodefixture"]),
    Component(
        "python", "python", "python", "/usr/local/bin/pythonfixture", "python", True, ["pythonfixture"]
    ),
    Component(
        "pythonnosdk",
        "python-nosdk",
        "python",
        "/usr/local/bin/pythonfixture",
        "python",
        False,
        [],
        {"SDK": "0"},
        "no antithesis package: no coverage",
    ),
]


def image(c: Component) -> str:
    return f"{TAG}-{c.image}:latest"


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
            "-t",
            image(c),
            *flags,
            str(HERE / c.context),
        )
    return 0


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
        found = dict(line.split("=") for line in out.split())
        ok = found.get("nm") != "0" and found.get("sancov") != "0" and found.get("debug") != "0"
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
            + (f"  ({c.note})" if c.note else "")
        )
    props = sh(
        "snouty",
        "runs",
        "properties",
        a.run_id,
        "--detail",
        "--name",
        "every instrumented module has symbols",
        check=False,
    )
    print("\nEvery instrumented module has symbols:")
    print("\n".join("  " + line for line in props.strip().splitlines()[3:]) or "  (not reported yet)")
    return 1 if bad else 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)
    sub.add_parser("build", help="build every image").set_defaults(func=build)
    sub.add_parser("check-local", help="run the local checks on the images").set_defaults(func=check_local)
    run = sub.add_parser("check-run", help="compare a run's modules with the expected ones")
    run.add_argument("run_id")
    run.set_defaults(func=check_run)
    a = p.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    main()
