# Quick Eval

## Prepare the Dataset

Download the dataset and DB dumps following the [main README](../README.md):

**LiveSQLBench-Base-Lite:**
```bash
git clone https://huggingface.co/datasets/birdsql/livesqlbench-base-lite
```
Download the [DB dumps (lite)](https://drive.google.com/file/d/1QIGQlRKbkqApAOrQXPqFJgUg8rQ7HRRZ/view), unzip and rename to `evaluation/postgre_table_dumps`.

**LiveSQLBench-Base-Full v1:**
```bash
git clone https://huggingface.co/datasets/birdsql/livesqlbench-base-full-v1
```
Download the [DB dumps (full)](https://drive.google.com/file/d/1V9SFIWebi27JtaDUAScG1xE9ELbYcWLR/view), unzip and rename to `evaluation/postgre_table_dumps_full`.

## Build Required Docker Images

### 1. Build the agent image
We provide agent environment Dockerfiles under adapters/livesqlbench/template/. For the released baseline, build the OpenHands image:
```bash
cd adapters/livesqlbench/template
docker build -t livesqlbench-main-openhands:latest -f environment/Dockerfile.openhands .
cd ../../..
```

This image provides the execution environment used by the OpenHands agent during Harbor runs.

If you want to evaluate a different agent, you can provide your own agent Dockerfile under `adapters/livesqlbench/template/` and build the image accordingly.

### 2. Build the PostgreSQL images

**LiveSQLBench-Base-Lite:**
```bash
./adapters/livesqlbench/build_db_images.sh --db-dir ../evaluation/postgre_table_dumps
```

**LiveSQLBench-Base-Full v1:**
```bash
./adapters/livesqlbench/build_db_images.sh --db-dir ../evaluation/postgre_table_dumps_full
```

To build the image for a single database only, use `--name`, for example:
```bash
./adapters/livesqlbench/build_db_images.sh --db-dir ../evaluation/postgre_table_dumps --name solar_template
```

## Generate Harbor Task Directories

After the required Docker images are built, run the LiveSQLBench adapter to convert LiveSQLBench instances into Harbor task directories.

**LiveSQLBench-Base-Lite:**
```bash
python3 adapters/livesqlbench/run_adapter.py \
  --data-root ../livesqlbench-base-lite \
  --db-dump-root ../evaluation/postgre_table_dumps \
  --output-dir datasets/livesqlbench-lite/ \
  --agent-image livesqlbench-main-openhands:latest
```

**LiveSQLBench-Base-Full v1:**
```bash
python3 adapters/livesqlbench/run_adapter.py \
  --data-root ../livesqlbench-base-full-v1 \
  --db-dump-root ../evaluation/postgre_table_dumps_full \
  --output-dir datasets/livesqlbench-full/ \
  --agent-image livesqlbench-main-openhands:latest
```

- `--agent-image` should match the agent Docker image you built earlier.
- `--data-root` should point to the LiveSQLBench dataset directory for the version you want to evaluate.
- `--db-dump-root` should point to the matching PostgreSQL dump directory.

To generate only one instance for testing, add `--limit 1`.

## Run an Oracle Check
After generating the Harbor task directories, run the Oracle agent once to verify that the generated tasks can be executed correctly:

**LiveSQLBench-Base-Lite:**
```bash
uv run harbor run -p datasets/livesqlbench-lite/ -a oracle -n 1
```

**LiveSQLBench-Base-Full v1:**
```bash
uv run harbor run -p datasets/livesqlbench-full/ -a oracle -n 1
```

- `-p`: path to the generated Harbor task directories.
- `-a oracle`: run the Harbor Oracle script for validation.
- `-n 1`: run with concurrency 1. Increase this value if you want to evaluate multiple tasks in parallel.

This step validates the generated task directories before running model-based agents.

## Set environment variables
Before running Harbor agents, set the required API credentials. For example:

```bash
export ANTHROPIC_API_KEY=your_api_key
# or
export OPENAI_API_KEY=your_api_key
```

To enable openhands agent, set the `LLM_MODEL` and `LLM_API_KEY`:

```bash
export LLM_MODEL=your_model
export LLM_API_KEY=your_api_key
```

## Run Agents
```bash
uv run harbor run -p datasets/livesqlbench-lite/ \
  -a openhands \
  -m <model_name> \
  -n 4
```

- `-p`: path to the generated task directories (`datasets/livesqlbench-lite/` or `datasets/livesqlbench-full/`)
- `-a`: agent to evaluate
- `-m`: model identifier, for example, `bedrock/us.anthropic.claude-3-7-sonnet-20250219-v1:0`
- `-n`: concurrency

## Acknowledgment

This repository component is derived from the [Harbor](https://github.com/harbor-framework/harbor) framework. Our version retains Harbor's overall structure and evaluation harness, with limited modifications and an additional adapter for this benchmark.

We gratefully acknowledge the Harbor Framework Team for open-sourcing Harbor under the Apache-2.0 license.

Please cite Harbor in addition to this benchmark when using this repository:

```bibtex
@software{Harbor_Framework_Team_Harbor_A_framework_2026,
  author = {{Harbor Framework Team}},
  title = {{Harbor: A framework for evaluating and optimizing agents and models in container environments}},
  year = {2026},
  month = jan,
  url = {https://github.com/harbor-framework/harbor}
}
```
