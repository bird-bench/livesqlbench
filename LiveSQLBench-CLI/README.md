# LiveSQLBench CLI

Harbor-based tooling to turn **LiveSQLBench** instances into **Harbor tasks** and run terminal agents (OpenHands, Codex CLI, Oracle, etc.) against PostgreSQL-backed databases.

For benchmark context, datasets, and citations for LiveSQLBench itself, see the [**repository README**](../README.md).

---

## Prerequisites

- **Docker** (for agent images and per-database PostgreSQL images)
- **[uv](https://docs.astral.sh/uv/)** (Python env / `uv run harbor …`)
- Dataset JSONL + PostgreSQL dumps laid out locally (see below)

Install dependencies from this directory:

```bash
cd LiveSQLBench-CLI
uv sync
```

---

## Layout

Place datasets and dumps under `LiveSQLBench-CLI/` (or paths you pass to `run_adapter.py`). A typical layout:

```text
LiveSQLBench-CLI/
  data/
    livesqlbench-base-lite/
    livesqlbench-base-full/          # e.g. HF clone of base-full-v1
    livesqlbench-large-v1/
    postgre_table_dumps/             # lite dumps (one subdir per DB)
    postgre_table_dumps_base_full/
    postgre_table_dumps_large/       # large-v1 dumps
  evaluation/
    src/                             # verifier helpers used by generated tasks
```

The adapter resolves common paths automatically; you can override with CLI flags (see `python3 adapters/livesqlbench/run_adapter.py --help`), including `--data-jsonl` / `--gt-jsonl` when filenames differ from the defaults.

---

## Prepare datasets and dumps

Full step-by-step setup (including HF clones and evaluation Docker flows) is in the [**repository README**](../README.md) — the same **Google Drive** dump archives are linked in the *Evaluation Environment Setup* / *Download the database dumps* section there.

Hugging Face hosts the public task JSONL; **PostgreSQL dump archives** are distributed via Google Drive (same links as the root README):

| Variant | Hugging Face (task data) | PostgreSQL dumps (Google Drive) | Place under this CLI layout |
|--------|--------------------------|----------------------------------|-----------------------------|
| Base-Lite | [`birdsql/livesqlbench-base-lite`](https://huggingface.co/datasets/birdsql/livesqlbench-base-lite) | [Download dumps](https://drive.google.com/file/d/1QIGQlRKbkqApAOrQXPqFJgUg8rQ7HRRZ/view) | `data/postgre_table_dumps/` |
| Base-Full v1 | [`birdsql/livesqlbench-base-full-v1`](https://huggingface.co/datasets/birdsql/livesqlbench-base-full-v1) | [Download dumps](https://drive.google.com/file/d/1V9SFIWebi27JtaDUAScG1xE9ELbYcWLR/view) | `data/postgre_table_dumps_base_full/` |
| Large-v1 | [`birdsql/livesqlbench-large-v1`](https://huggingface.co/datasets/birdsql/livesqlbench-large-v1) | [Download dumps](https://drive.google.com/file/d/1u1L-SvJtOZGfcIST-dINw8DnGEQDMu6C/view?usp=sharing) | `data/postgre_table_dumps_large/` |

The root README uses paths like `evaluation/postgre_table_dumps`; for this directory, keep the same unzip structure but under `data/…` as in the [layout](#layout) above.

Unzip dumps so each database appears as a subdirectory under the matching dump folder.

---

## Build Docker images

### 1. Agent image (OpenHands + Codex in default image)

```bash
cd adapters/livesqlbench/template
docker build -t livesqlbench-main-openhands:latest -f environment/Dockerfile.openhands .
cd ../../..
```

Optional Codex-only image for smaller task regeneration:

```bash
cd adapters/livesqlbench/template
docker build -t livesqlbench-main-codex:latest -f environment/Dockerfile.codex .
cd ../../..
```

### 2. PostgreSQL images (one image per database)

**Base-Lite:**

```bash
bash adapters/livesqlbench/build_db_images.sh --db-dir data/postgre_table_dumps
```

**Base-Full:**

```bash
bash adapters/livesqlbench/build_db_images.sh --db-dir data/postgre_table_dumps_base_full
```

**Large-v1** (newer dumps often need a newer server image):

```bash
bash adapters/livesqlbench/build_db_images.sh \
  --db-dir data/postgre_table_dumps_large \
  --postgres-base-image postgres:18
```

Use `--force` to rebuild existing tags, and `--name <db>` to build a single database.

---

## Generate Harbor task directories

**Base-Lite:**

```bash
python3 adapters/livesqlbench/run_adapter.py \
  --data-root data/livesqlbench-base-lite \
  --db-dump-root data/postgre_table_dumps \
  --eval-src-dir evaluation/src \
  --output-dir datasets/livesqlbench-lite \
  --agent-image livesqlbench-main-openhands:latest
```

**Base-Full:**

```bash
python3 adapters/livesqlbench/run_adapter.py \
  --data-root data/livesqlbench-base-full \
  --db-dump-root data/postgre_table_dumps_base_full \
  --eval-src-dir evaluation/src \
  --output-dir datasets/livesqlbench-full \
  --agent-image livesqlbench-main-openhands:latest
```

**Large-v1:**

```bash
python3 adapters/livesqlbench/run_adapter.py \
  --data-root data/livesqlbench-large-v1 \
  --db-dump-root data/postgre_table_dumps_large \
  --eval-src-dir evaluation/src \
  --output-dir datasets/livesqlbench-large \
  --agent-image livesqlbench-main-openhands:latest
```

Add `--limit 1` for a smoke test; add `--force` to overwrite an existing output tree.

---

## Verify with Oracle

**Lite / Full / Large** (adjust `-p`):

```bash
uv run harbor run -p datasets/livesqlbench-lite -a oracle -n 4
uv run harbor run -p datasets/livesqlbench-full -a oracle -n 4
uv run harbor run -p datasets/livesqlbench-large -a oracle -n 4
```

Use `-n 1` if you prefer a single trial at a time (easier debugging or lighter machine load).

---

## Environment variables

```bash
export OPENAI_API_KEY=your_key
export LLM_API_KEY="$OPENAI_API_KEY"    # OpenHands often expects this as well
```

Use other provider keys as required by your agent and model. Behind a proxy, set `http_proxy` / `https_proxy` (and unset conflicting `all_proxy` if needed) before `harbor run`.

---

## Run agents

Example (OpenHands, replace model id as needed):

```bash
uv run harbor run -p datasets/livesqlbench-lite \
  -a openhands \
  -m openai/gpt-5.5 \
  --ak reasoning_effort=low \
  --ae MAX_ITERATIONS=50 \
  --agent-timeout-multiplier 0.333 \
  -n 4
```

For Large-v1 you can use the helper script:

```bash
./scripts/run_openhands_gpt55_low.sh
```

**Codex CLI** (`-a codex`) uses `OPENAI_API_KEY`; it does not use OpenHands `MAX_ITERATIONS`, but task timeouts and `--agent-timeout-multiplier` still apply.

---

## Acknowledgment

This component builds on the [**Harbor**](https://github.com/harbor-framework/harbor) framework (Apache-2.0). Please cite Harbor when using this CLI stack:

```bibtex
@software{Harbor_Framework_Team_Harbor_A_framework_2026,
  author = {{Harbor Framework Team}},
  title = {{Harbor: A framework for evaluating and optimizing agents and models in container environments}},
  year = {2026},
  month = jan,
  url = {https://github.com/harbor-framework/harbor}
}
```
