# Images

Use these images when you have to choose one, such as for the driver or a build stage you add. When the SUT already builds its own images, build on those instead. Each image here is on the current Debian stable release, so a binary built on one runs on another. A Dockerfile on another page names an image by its row, such as `<Rust build image>`: substitute the image from that row.

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
