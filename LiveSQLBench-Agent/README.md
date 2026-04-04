# LiveSQLBench-Agent — Google ADK Data Agent

**Text-to-SQL data agent built on [Google ADK](https://google.github.io/adk-docs/) with server-based DB environment.** The agent receives a clear natural language query, explores the database using tools, and submits a SQL answer.

## Architecture

```
orchestrator/runner.py          Parallel evaluation runner (--concurrency)
        |
        ├── system_agent (6000)     Google ADK agent with 8 tools + step-based callbacks
        └── db_environment (6002)   SQL execution + evaluation + per-task DB isolation
                |
                └── PostgreSQL      LiveSQLBench databases (Docker)
```

**Key features:**

- **Modular microservices** — 2 independent services communicating via HTTP. Deploy on different machines, swap any component (bring your own agent, or DB backend), or scale services independently.
- **Google ADK-based agent** migrated from [BIRD-Interact-ADK](https://github.com/bird-bench/BIRD-Interact/tree/main/BIRD-Interact-ADK).
- **8 tools** — `get_schema`, `get_all_column_meanings`, `get_column_meaning`, `get_all_external_knowledge_names`, `get_knowledge_definition`, `get_all_knowledge_definitions`, `execute_sql`, `submit_sql`
- **Parallel execution** — `asyncio.Semaphore` + per-task DB copies for lock-free concurrency
- **Multi-provider LLM** — supports any [LiteLlm-compatible provider](https://docs.litellm.ai/docs/providers) (Anthropic, OpenAI, Ollama, etc.)
- **Per-task DB isolation** — each task gets its own database copy; SELECT-only enforcement

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Docker (for PostgreSQL databases)

### 2. Set up PostgreSQL (Optional)

If you already have the LiveSQLBench PostgreSQL container running, reuse it directly.

Otherwise, start the database:

```bash
docker compose up -d postgresql          # lite (18 DBs, 300 tasks)
docker compose up -d --profile full       # full (26 DBs, 600 tasks)
```

Wait for initialization to complete:

```bash
docker compose logs -f postgresql
# Look for: "database system is ready to accept connections"
```

### 3. Install dependencies

```bash
conda create -p ./.venv python=3.10 -y
source activate ./.venv
pip install -r requirements.txt
```

### 4. Configure

```bash
cp .env.example .env
# Edit .env with your settings:
#   - ANTHROPIC_API_KEY (or OPENAI_API_KEY for OpenAI models)
#   - SYSTEM_AGENT_MODEL
#   - DATASET: "lite" or "full"
```

### 5. Start services

```bash
bash scripts/start_services.sh
```

### 6. Run evaluation

```bash
# Run all tasks with concurrency 3
python -m orchestrator.runner --concurrency 3

# Run first 10 tasks
python -m orchestrator.runner --limit 10

# Full dataset
DATASET=full python -m orchestrator.runner --concurrency 3
```

### 7. View results

```bash
# Generate HTML report
python -m orchestrator.report results/eval_single_turn.json
```

## LLM Configuration

LLM calls use [LiteLlm](https://docs.litellm.ai/docs/providers), which supports 100+ providers. Set the API key and model name in `.env`:

```env
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
SYSTEM_AGENT_MODEL=anthropic/claude-sonnet-4-20250514

# OpenAI
# OPENAI_API_KEY=sk-...
# SYSTEM_AGENT_MODEL=openai/gpt-4o

# Ollama (local)
# SYSTEM_AGENT_MODEL=ollama_chat/llama3:instruct
```

See [LiteLlm providers](https://docs.litellm.ai/docs/providers) for the full list.

## Dataset


| Version  | Tasks | Databases | PostgreSQL Image                                | HuggingFace                                                                                  |
| -------- | ----- | --------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Lite** | 270   | 18        | `shawnxxh/bird-interact-postgresql:latest`      | [livesqlbench-base-lite](https://huggingface.co/datasets/birdsql/livesqlbench-base-lite)     |
| **Full** | 600   | 26        | `shawnxxh/bird-interact-postgresql-full:latest` | [livesqlbench-base-full-v1](https://huggingface.co/datasets/birdsql/livesqlbench-base-full-v1) |


### Download & Setup

1. Download the dataset from HuggingFace and place it in the repo root:
  ```bash
   # Lite
   git clone https://huggingface.co/datasets/birdsql/livesqlbench-base-lite livesqlbench-base-lite
   # Full
   git clone https://huggingface.co/datasets/birdsql/livesqlbench-base-full-v1 livesqlbench-base-full
  ```
2. **Ground Truth & Test Cases**: The public dataset does not include `sol_sql` and `test_cases` fields. To obtain them, email [bird.bench25@gmail.com](mailto:bird.bench25@gmail.com) with subject tag `[livesqlbench-base-lite GT&Test Cases]` or `[livesqlbench-base-full-v1 GT&Test Cases]`. You will receive the GT file automatically.
3. Combine public data with GT:
  ```bash
   python scripts/combine_public_with_gt.py \
     livesqlbench-base-lite/livesqlbench_data.jsonl \
     /path/to/livesqlbench_gt_testcases.jsonl \
     livesqlbench-base-lite/livesqlbench_data.jsonl
  ```

Each dataset directory contains:

- `livesqlbench_data.jsonl` — task definitions
- `{db_name}/` — per-database schema, column meanings, external knowledge

Set `DATASET=lite` or `DATASET=full` in `.env`.

## Project Structure

```
.
├── system_agent/           # ADK agent service (port 6000)
│   ├── agent.py            # Agent builder + instruction
│   ├── server.py           # FastAPI endpoints
│   ├── adk_runtime.py      # ADK session management
│   ├── callbacks.py        # Step-based budget + turn limits
│   └── tools.py            # 8 ADK tools (no ask_user)
├── db_environment/         # DB service (port 6002)
│   └── server.py           # SQL execution, evaluation, per-task DB
├── shared/                 # Shared utilities
│   ├── config.py           # Centralized settings
│   ├── llm.py              # LLM provider (LiteLlm)
│   ├── db_utils.py         # PostgreSQL pooling & evaluation
│   └── models.py           # Pydantic models
├── orchestrator/           # Evaluation runner
│   ├── runner.py           # Parallel runner (--concurrency, --limit)
│   ├── single_turn.py      # Single-turn pipeline
│   └── report.py           # HTML report generator
├── livesqlbench-base-lite/  # Lite dataset (270 tasks)
├── livesqlbench-base-full/  # Full dataset (600 tasks)
├── docker-compose.yml      # PostgreSQL containers
├── scripts/                # Service startup scripts
├── .env.example            # Configuration template
└── requirements.txt
```

## How It Works

1. **Orchestrator** loads tasks from JSONL and dispatches them in parallel
2. **System Agent** receives the clear query + step budget
3. **Agent explores** the database using tools (schema, column meanings, external knowledge, execute SQL)
4. **Agent submits** its final SQL — one attempt only, pass or fail
5. **Results** saved incrementally with pass rate and reward metrics

Each tool call costs 1 step out of 30. The agent sees remaining steps after each action.

## License

MIT License. See [LICENSE](LICENSE).

## Citation

```bibtex
@inproceedings{
huo2026birdinteract,
title={{BIRD}-{INTERACT}: Re-imagining Text-to-{SQL} Evaluation via Lens of Dynamic Interactions},
author={Nan Huo and Xiaohan Xu and Jinyang Li and Per Jacobsson and Shipei Lin and Bowen Qin and Binyuan Hui and Xiaolong Li and Ge Qu and Shuzheng Si and Linheng Han and Edward Alexander and Xintong Zhu and Rui Qin and Ruihan Yu and Yiyao Jin and Feige Zhou and Weihao Zhong and Yun Chen and Hongyu Liu and Chenhao Ma and Fatma Ozcan and Yannis Papakonstantinou and Reynold Cheng},
booktitle={The Fourteenth International Conference on Learning Representations},
year={2026},
url={https://openreview.net/forum?id=nHrYBGujps}
}
```

## Acknowledgement

BIRD Team & Google Cloud. Built with [Google ADK](https://google.github.io/adk-docs/).
