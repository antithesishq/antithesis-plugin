"""Keep the image table in the workload module current.

`references/workload/images.md` lists the base image for each role, all on the current Debian
stable release. This finds that release from deb.debian.org, renders each role's image from
its template, and checks that Docker Hub has every tag. `check` fails when the table differs
from that, or when a tag is missing, and `fix` rewrites the table. Nightly CI runs the check,
so a new Debian release, or a tag that disappears, fails the nightly until someone runs
`mise run fix:images`.
"""

import json
import re
import sys
import urllib.error
import urllib.request

from report import ROOT, error, say

PAGE = ROOT / "plugins/antithesis/skills/antithesis/references/workload/images.md"
DEBIAN_RELEASE = "https://deb.debian.org/debian/dists/stable/Release"
# Each role's image, from the Debian stable codename (trixie) and major version (13).
ROLES = [
    ("Runtime image", "debian:{codename}-slim"),
    ("Rust build image", "rust:1-{codename}"),
    ("Go build image", "golang:1-{codename}"),
    ("Python image", "python:3-slim-{codename}"),
    ("OCaml build image", "ocaml/opam:debian-{major}"),
]
START, END = "<!-- images:start -->", "<!-- images:end -->"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "antithesis-plugin-images"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def debian_stable() -> tuple[str, str]:
    """The codename and major version of the current Debian stable release."""
    fields = dict(line.split(": ", 1) for line in fetch(DEBIAN_RELEASE).decode().splitlines() if ": " in line)
    return fields["Codename"], fields["Version"].split(".")[0]


def tag_exists(image: str) -> bool:
    repository, tag = image.split(":")
    if "/" not in repository:
        repository = f"library/{repository}"
    try:
        json.loads(fetch(f"https://hub.docker.com/v2/repositories/{repository}/tags/{tag}"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise
    return True


def render(codename: str, major: str) -> str:
    rows = [(role, f"`{template.format(codename=codename, major=major)}`") for role, template in ROLES]
    width = (max(len(r) for r, _ in rows + [("Role", "")]), max(len(i) for _, i in rows + [("", "Image")]))
    lines = [f"Debian stable: {major} ({codename})", ""]
    lines.append(f"| {'Role'.ljust(width[0])} | {'Image'.ljust(width[1])} |")
    lines.append(f"| {'-' * width[0]} | {'-' * width[1]} |")
    lines += [f"| {role.ljust(width[0])} | {image.ljust(width[1])} |" for role, image in rows]
    return "\n".join(lines)


def current_table(text: str) -> str:
    match = re.search(re.escape(START) + r"\n(.*?)\n" + re.escape(END), text, re.DOTALL)
    if not match:
        raise SystemExit(f"{PAGE.relative_to(ROOT)} has no {START} ... {END} block")
    return match.group(1)


def main(write: bool) -> int:
    codename, major = debian_stable()
    say(f"Debian stable is {major} ({codename})")
    missing = [t.format(codename=codename, major=major) for _, t in ROLES]
    missing = [image for image in missing if not tag_exists(image)]
    for image in missing:
        error(
            "check-images", f"Docker Hub has no `{image}`; update its template in scripts/images.py", PAGE, 1
        )
    text = PAGE.read_text()
    table = render(codename, major)
    if current_table(text) == table:
        if not missing:
            print(f"images.md is current: Debian {major} ({codename}), every tag exists")
        return 1 if missing else 0
    if write:
        PAGE.write_text(text.replace(current_table(text), table))
        print(f"Updated images.md for Debian {major} ({codename})")
        return 1 if missing else 0
    error(
        "check-images",
        f"the table is out of date for Debian {major} ({codename}); run `mise run fix:images`",
        PAGE,
        1,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(write="--write" in sys.argv))
