---
name: lockfile-bisect
description: >
  Investigates which updated dependency caused an Iris performance regression
  by systematically pinning suspects in the conda YAML specs, regenerating
  lockfiles, and re-running benchmarks via SLURM (sbatch). Use when a
  lockfile-update PR shows a benchmark regression and the responsible package
  is not immediately obvious. Covers the full workflow: reading PR benchmark
  results, identifying and prioritising suspects from the lockfile diff,
  choosing a bisect strategy, regenerating lockfiles, committing, submitting
  benchmarks, and concluding.
compatibility: >
  Benchmarks require sbatch (SLURM), and an environment containing nox. Lockfile changes
  require conda-lock (preferred) or a working conda installation as fallback; UK Met 
  Office users also need the ssstack package.
metadata:
  author: iris-contributors
  version: "1.0"
---

# Iris lockfile dependency bisect

This skill guides an agent through finding which changed dependency caused a
performance regression on a lockfile-update PR.

See [references/LOCKFILE.md](references/LOCKFILE.md) for lockfile regeneration
details, and [references/BENCHMARK.md](references/BENCHMARK.md) for benchmark
runner details.

---

## Overview of the workflow

```
1. Collect context   →  PR number, benchmark shifts, lockfile diff
2. Identify suspects →  packages that changed AND are plausible culprits
3. Pick strategy     →  sequential (≤3 suspects) or binary-search (>3)
4. Pin + regenerate  →  edit *.yml, make lockfiles, verify diff
5. Commit + sbatch   →  push a branch, submit SLURM job
6. Interpret results →  regression present? narrow or confirm
7. Conclude          →  report culprit (or clear), clean up pins
```

**Always use `sbatch` for benchmark runs.** Do not run ASV directly on the
login node or interactively.

---

## Step 1 — Collect context

### 1a. Get the PR benchmark comment

Try the GitHub tool to fetch the PR first. Look for a comment posted by
`github-actions[bot]` with the heading
`⏱️ Performance Benchmark Report` that contains a "Performance shifts"
section. This section lists benchmarks with statistically significant changes
and their percentage shifts.

If the GitHub tool is unavailable, ask the user to paste:
- The benchmark performance-shifts table from the PR comment.
- The PR number and the two commit SHAs being compared.

### 1b. Get the lockfile diff

The lockfile-update PR only changes files under `requirements/locks/`. Fetch
the diff for those files (GitHub tool, or `git diff <base>..<head> --
requirements/locks/`). To find the changed packages: focus on the lockfile covering the
latest Python version, as this is the one used in benchmarking.

Extract a list of packages whose **version or build string changed**. Ignore
lines that only changed URL prefix but kept the same version/build.

---

## Step 2 — Identify and prioritise suspects

Filter the changed-package list to plausible performance culprits. Apply the
following priority tiers (highest first):

| Priority | Package examples |
|----------|-----------------|
| **1 – Core compute** | `numpy`, `dask-core`, `libnetcdf`, `netcdf4`, `scipy`, `numba`, `numexpr` |
| **2 – Visualisation / geo** | `cartopy`, `matplotlib-base`, `shapely`, `pyproj`, `proj`, `gdal`, `rasterio` |
| **3 – Python runtime / data** | `python`, `pandas`, `cftime`, `cf-units`, `distributed` |
| **4 – Other scientific** | Any other scientific/numerical library |
| **5 – Infrastructure** | `openssl`, `zlib`, compiler runtimes, `ca-certificates`, fonts |

Tier-5 packages are almost never the culprit; skip them unless all higher-tier
suspects have been cleared.

Present the suspect list to the user before proceeding, grouped by tier, so
they can correct or override it.

---

## Step 3 — Choose investigation strategy

| Condition | Strategy |
|-----------|----------|
| 1–3 suspects | **Sequential** — test each suspect individually, most-likely tier first |
| 4–8 suspects | **Binary search** — test half the suspects (highest tiers) pinned at once, then halve again |
| >8 suspects | **Tiered binary** — test whole tier 1 together, then tier 2, etc. |

Record the current suspect list and which have been cleared/confirmed as you
iterate.

---

## Step 4 — Pin suspects and regenerate lockfiles

### 4a. Add pins to the YAML spec(s)

Edit the relevant `requirements/py*.yml` files (usually all three: `py312.yml`,
`py313.yml`, `py314.yml`). Pin the suspect package(s) below the version in
the **head** commit of the PR (i.e. the version after the update):

```yaml
# Example: rolling back numpy
- numpy <2.1.3
```

Avoid `==` pins, as these can cause problems during solving.

The version string comes from the head lockfile line, e.g.:
```
https://.../numpy-2.1.3-py312h..._0.conda
```
→ pin as `numpy <2.1.3`.

### 4b. Regenerate lockfiles

See [references/LOCKFILE.md](references/LOCKFILE.md) for full details.

**Primary method (requires `conda-lock`):**
```bash
make lockfiles
```

**Fallback method (if conda-lock is unavailable or fails):**
```bash
conda env create -f requirements/py313.yml --name tmp-bisect-env --yes
conda run -n tmp-bisect-env conda list --explicit \
    > requirements/locks/py313-linux-64.lock
conda env remove --name tmp-bisect-env --yes
# Repeat for py312.yml and py314.yml
```

**UK Met Office users — normalise URL prefixes with ssstack:**
```bash
ssstack shareable requirements/locks/py313-linux-64.lock \
    > requirements/locks/py313-linux-64.lock.tmp
mv requirements/locks/py313-linux-64.lock.tmp \
    requirements/locks/py313-linux-64.lock
# Repeat for other lockfiles
```
This is required before committing so that URLs use the standard conda-forge
prefix rather than the internal mirror.

### 4c. Verify the lockfile

Confirm the regenerated lockfile:
1. Still contains the suspect package at the pinned (old) version.
2. Does not contain unexpected large changes (a diff of >50 packages warrants
   user confirmation before proceeding).

---

## Step 5 — Commit and submit benchmarks

### 5a. Commit on a dedicated branch

```bash
git checkout -b bisect/<short-description>
git add requirements/locks/ requirements/py*.yml
git commit -m "bisect: pin <package(s)> to investigate regression"
```

The benchmark runner needs a git-addressable commit. Always create a new commit so ASV 
can detect the environment change.

### 5b. Submit the SLURM job

Copy and customise [assets/run_investigate.slurm](assets/run_investigate.slurm),
then submit:

```bash
sbatch <my-customised-slurm-script>
```

For **investigation runs** (faster, fewer repeats): uncomment Mode B and set
`BENCH_PATTERN` to a benchmark name from Step 1 — ASV arguments are passed
through directly to `asv run`, and `branch` handles result presentation
automatically. A single benchmark is enough to confirm or clear a suspect.

For **confirmation runs** (full accuracy): use Mode A (the default).

Monitor job status with `squeue -u $USER` and collect output from the `.out`
and `.err` files once complete.

---

## Step 6 — Interpret results and iterate

Look for the "Benchmarks that have got worse:" section in the ASV output or the generated
benchmark report.

| Result | Interpretation | Next action |
|--------|---------------|-------------|
| Regression **gone** | Pinned package(s) are responsible | If >1 package was pinned, un-pin half and re-test to isolate further |
| Regression **persists** | Pinned package(s) are NOT responsible | Remove the pin(s) and test the next suspect group |
| Regression **changed magnitude** | Partial contribution | Note and continue testing other suspects |
| Job fails or produces no output | Infrastructure issue | See pitfalls below |

Remove pins for cleared suspects before adding the next set, keeping the diff
minimal and interpretable.

---

## Step 7 — Conclude

Once a single package is identified:

1. **Report** the finding to the user with the package name, old version
   (baseline), and new version (regression trigger).
2. **Check for known issues** — search the package's issue tracker for the
   version change and any related performance regressions.
3. **Recommend action** — options include:
   - Pin the package in `requirements/py*.yml` until upstream fixes the issue.
   - Open an issue on the culprit package's repository.
   - Open an Iris issue tracking the regression.
   - Report the regression to Iris users in a What's New entry (see
     `docs/src/developers_guide/documenting/whats_new_contributions.rst`).
4. **Clean up** — remove the investigation branch(es), SLURM files, and any temporary
   pins unless a pin is being kept as a workaround.

---

## Common pitfalls

| Pitfall | Mitigation |
|---------|------------|
| `make lockfiles` silently produces an unchanged lockfile | Check the diff; re-run with `--verbose` or use the fallback method |
| conda-lock resolver times out | Use the fallback `conda env create` method |
| ASV job fails with no benchmark output | Check `.err` file; common causes: missing `OVERRIDE_TEST_DATA_REPOSITORY`, SLURM memory/time exceeded, or environment build failure |
| Benchmark results are noisy (shifts <20%) | Increase repeat count: remove `--quick` from the Mode B command |
| Multiple PRs have merged since the regression was noticed | Check git log for lockfile changes since the last clean run; may need to test across multiple commits |
| ssstack not available at UK Met Office | Try `module load ssstack` or ask a colleague; without it, internal URLs will be committed which fail CI |
