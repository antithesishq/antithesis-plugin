# Lay out the workload

Unless the user or the repository's conventions call for something else, put a new workload here:

```text
antithesis/
  README.md
  <workload>/
    config/     # docker-compose.yaml and the files it mounts; the --config dir
    driver/     # the driver's source and Dockerfile
    scripts/    # the commands you repeat
```

Every other image the workload builds, such as the instrumented SUT, gets its own directory beside `driver/`.

## Keep the config directory minimal

`snouty launch` copies the whole config directory into the config image, on every launch. Keep only the config in it, and manage `.gitignore` and `.dockerignore` so build output, coverage data and run output stay out of the repository and out of every image.

## The README

Keep `antithesis/README.md` short and current. For each workload, it says what the workload tests, what the driver does and which properties it checks, how to build, run locally and launch it, and any known findings it works around.

## The scripts

Write a script for each command you repeat, in the repository's own conventions, and run it rather than retyping the command. Then you and the user run the workload the same way each time, and nothing depends on remembering flags across a context compaction:

- **Launch:** builds, validates and launches with the workload's fault flags and `--param attrs.*`, such as the workload and SUT versions and `attrs.plugin_version`. Pick `--max-compute-hours` and check the compute budget yourself before each launch (`references/launch/MODULE.md`), so take the hours as an argument.
- **Local run:** runs the local loop (`references/workload/local-loop.md`).
