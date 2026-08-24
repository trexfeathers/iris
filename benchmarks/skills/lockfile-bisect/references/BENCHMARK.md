# Benchmark runner reference

## Where to look

- **`benchmarks/README.md`** — Iris-specific setup, environment variables,
  how to run via `nox` or `bm_runner.py` directly, and tips for reducing
  run time.
- **`benchmarks/bm_runner.py`** — read this file directly to get all subcommand
  descriptions, arguments, and epilogs without needing a working environment.
  All help text is present as string literals.
- **ASV usage guide** — https://asv.readthedocs.io/en/stable/using.html
- **ASV command reference** — https://asv.readthedocs.io/en/stable/commands.html

## Run time expectations

Full suite via `branch`: typically **30 minutes to 2 hours**.

With `--quick --bench <pattern>`: less time. The specifics depend on the
benchmark selected. This is the right mode for bisect investigation iterations.

## Reading results

The end of any `nox -s benchmarks` run prints an `asv compare` table showing
performance shifts. This is the same format as the `⏱️ Performance Benchmark
Report` comments on GitHub pull requests — both are `asv compare` output.

To identify which benchmarks to target with `--bench`: read the benchmark names
directly from the `asv compare` output (the full name is always printed there).
The `--bench` argument accepts a Python regex, so a partial name is enough.

## Common failure modes

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Job errors immediately with `SIGILL` | AVX512 on incompatible hardware | Ensure `NPY_DISABLE_CPU_FEATURES` is set |
| `KeyError: 'existing:...'` in ASV output | Environment path not found | Re-run from scratch without `ASV_COMMIT_ENVS` |
| Job runs but no shifts reported | Benchmarks too noisy or `--quick` used | Re-run without `--quick` for confirmation |
| Job exceeds wall time | Full suite too slow for SLURM limit | Use `--bench` to target only the regressing benchmark |
| `conda: command not found` | conda not initialised in SLURM session | Ensure the `source conda.sh` line in the SLURM script is present |
