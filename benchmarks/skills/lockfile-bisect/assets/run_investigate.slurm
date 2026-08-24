#!/bin/bash
#SBATCH --job-name=iris-bm-bisect
#SBATCH --time=02:00:00
# Dask default = threaded scheduler. ntasks = number of processes (therefore 1),
#  cpus-per-task = how much parallelism we want. tasks-per-core = 1 to avoid
#  oversubscription of threads.
#SBATCH --ntasks=1
#SBATCH --ntasks-per-core=1
#SBATCH --cpus-per-task=12
# Dask recommends 4x RAM per worker assuming standard chunking.
#SBATCH --mem=48G
#SBATCH --output=iris-bm-bisect-%j.out
#SBATCH --error=iris-bm-bisect-%j.err

# ---------------------------------------------------------------------------
# Iris dependency-bisect benchmark run
#
# Usage:
#   sbatch benchmarks/skills/lockfile-bisect/assets/run_investigate.slurm
#
# Before submitting:
#   1. Set REPO_DIR below.
#   2. Choose the run mode: Mode A (full suite) or Mode B (targeted, fast).
#   3. For Mode B: set BENCH_PATTERN to match the regressing benchmark(s).
# ---------------------------------------------------------------------------

set -euo pipefail

REPO_DIR="/path/to/checkout/of/iris"   # <-- edit as needed

# Co-locate the Conda package cache and benchmark environments on a fast file
# system to reduce install time (see benchmarks/README.md § "Reducing run time").
fast_system=${TMPDIR:-/tmp}
tmp_env_dir="${fast_system}/benchmarking-${SLURM_JOB_ID}"
mkdir -p "${tmp_env_dir}"
export CONDA_PKGS_DIRS="${tmp_env_dir}/pkgs"
export ASV_ENV_PARENT="${tmp_env_dir}/env_parent"
mkdir -p "${CONDA_PKGS_DIRS}" "${ASV_ENV_PARENT}"

# Cache environments per-commit to avoid rebuilds across multiple iterations.
export ASV_COMMIT_ENVS="True"

export BENCHMARK_DATA="${DATADIR:-${REPO_DIR}/benchmarks/.data}/benchmark_data"

# Activate a Conda environment containing Nox.
# shellcheck disable=SC1090
env_name="my-environment"  # <-- edit as needed
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${env_name}"

cd "${REPO_DIR}"

# Disable CPU features that can cause SIGILL in some CI environments.
export NPY_DISABLE_CPU_FEATURES="AVX512F,AVX512CD,AVX512_SKX"
# Disable multi-threading in libraries that can spawn threads internally.
export NUMEXPR_MAX_THREADS=1
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

# Prevent tools misinterpreting whole-node resources as available.
export DASK_NUM_WORKERS=$SLURM_CPUS_PER_TASK
export ASV_MACHINE_NUM_CPU=$SLURM_CPUS_PER_TASK
export ASV_MACHINE_RAM="${SLURM_MEM_PER_NODE}MB"

# ===========================================================================
# Choose ONE of the two run modes below.
# ===========================================================================

# ---------------------------------------------------------------------------
# MODE A — full suite (accurate, longer run time ~1 hour).
# Compares HEAD with its merge-base against upstream/main.
# Good for final confirmation once a suspect has been narrowed down.
# ---------------------------------------------------------------------------
echo "Running: nox -s benchmarks -- branch upstream/main"
nox -s benchmarks -- branch upstream/main

# ---------------------------------------------------------------------------
# MODE B — targeted (fast investigation: fewer repeats, single benchmark).
# Un-comment this block and comment out Mode A to use.
#
# Set BENCH_PATTERN to a regex matching the regressing benchmark(s), e.g.:
#   "LoadCubes|Regrid" — matches any benchmark whose name contains these words.
# ASV arguments after "--" are passed through directly to "asv run".
# ---------------------------------------------------------------------------
# BENCH_PATTERN="LoadCubes"   # <-- ASV --bench pattern from PR benchmark report
#
# echo "Running: nox -s benchmarks -- branch upstream/main --quick --bench ${BENCH_PATTERN}"
# nox -s benchmarks -- branch upstream/main \
#     --quick \
#     --bench "${BENCH_PATTERN}"
