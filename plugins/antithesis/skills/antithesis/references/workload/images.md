# Images

Take every base image a workload builds on from this table. Each is the latest of its kind for the current Debian stable release, so build and runtime images share one release, and a binary built in one finds the libraries it was linked against in the other. A Dockerfile on another page names its image by role, such as `<Rust build image>`: substitute the image from this row.

<!-- images:start -->
Debian stable: 13 (trixie)

| Role              | Image                  |
| ----------------- | ---------------------- |
| Runtime image     | `debian:trixie-slim`   |
| Rust build image  | `rust:1-trixie`        |
| Go build image    | `golang:1-trixie`      |
| Python image      | `python:3-slim-trixie` |
| OCaml build image | `ocaml/opam:debian-13` |
<!-- images:end -->

Use another release only for a strong reason, such as a system that doesn't build on this one, and then use it for every image.
