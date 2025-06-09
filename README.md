#  LiveSQLBench <img src="materials/hku-logo.jpg" alt="HKU Logo" width="50" style="vertical-align:middle;margin-left:10px;"> <img src="materials/google-cloud-logo.png" alt="Google Cloud Logo" width="50" style="vertical-align:middle;margin-left:10px;">



<div style="display: flex; justify-content: center; align-items: center; gap: 10px;">
  <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.en">
    <img src="https://img.shields.io/badge/License-CC%20By%20SA%204.0-orange.svg" alt="License">
  </a>
  <a href="https://livesqlbench.ai">
    <img src="https://img.shields.io/badge/Leaderboard-2025-28a745.svg" alt="Leaderboard">
  </a>
  <a href="https://huggingface.co/datasets/birdsql/livesqlbench-base-lite/">
    <img src="https://img.shields.io/badge/Dataset-HuggingFace-FFD21E.svg" alt="HuggingFace">
  </a>
  <a href="https://www.python.org/downloads/release/python-310/">
    <img src="https://img.shields.io/badge/Python-3.10+-teal.svg" alt="Python">
  </a>
  <a href="https://pypi.org/project/openai/">
    <img src="https://img.shields.io/badge/OpenAI-1.40+-beige.svg" alt="OpenAI">
  </a>
</div>


<p align="center">
  <img src="materials/title.png" 
       style="width: %; min-width: 100px; display: block; margin: auto; border-radius: 15px !important;">
</p>

## News

- 📢 **[2025-05-30]** We are pleased to release [**LiveSQLBench-Base-Lite**](https://huggingface.co/datasets/birdsql/livesqlbench-base-lite), featuring 18 end-user level databases and 270 tasks (180 SELECT-only, 90 Management tasks). Each task involves unambiguous and straightforward user queries grounded in external knowledge, with medium to hard complexity SQL statements.


## 🚀 Overview

LiveSQLBench (BIRD-SQL Pro v0.5) is a **contamination-free**, **continuously evolving** benchmark designed to evaluate LLMs on **complex, real-world text-to-SQL tasks**, featuring **diverse real-world user queries**, including **Business Intelligence (BI)**, **CRUD operations**, and more. Each release will include **50 new, fully open-source DBs** curated by the BIRD team through expert collaboration and continuous improvement. It will cover a **wide range of database sizes**, from **end-user level** (around 127 columns) to **industrial level** (1340+ columns).

Here are the features of the LiveSQLBench benchmark:

1. **🗄️ Live Databases:**
Constructed dynamically from extensive and regularly updated CSV datasets, with both base (user-end level) and large (industrial level) versions (1340+ columns each DB) to test scalability.

2. **💬 Live User Queries and SQL:**
Each task pairs unambiguous user queries with annotated, gold-standard SQL statements. The user queries are grounded in an external knowledge base, with medium to hard complexity solution SQL statements.

3. **🧠 Contextual Reasoning (HKB):**
Every DB includes a hierarchical knowledge base (HKB) where each knowledge may have dependencies to others, which requires the multi-hop reasoning ability. Two HKB formats are provided: (1) structured JSON format, and (2) unstructured Document format.

4. **🔍 The First Full SQL Spectrum:**
Supports not just SELECT (Business Intelligence) queries, but also CRUD (e.g., UPDATE, CREATE, and other database management operations) queries.

5. **⚡ Automated Evaluation:**
Support fast evaluation via PostgreSQL template & docker. Each question includes verifiable test cases for accurate, reproducible scoring. Soft EX metric is used to evaluate SELECT-ONLY tasks; customized test cases are designed for DBA tasks, such as CRUD (CREATE, READ, UPDATE, DELETE). 

6. **🔄 Truly Live & Hidden Test:**
New databases and tasks are added over time. Each release features both open development and hidden test phases. The hidden test set from each release becomes the open development set for the next release, ensuring continuous evolution and fair evaluation.

### 🎯 Current Release: LiveSQLBench-Base-Lite

Currently, we are pleased to release **LiveSQLBench-Base-Lite**, featuring:
- **18 end-user level databases**
- **270 tasks** (180 SELECT-only, 90 Management tasks)
- **HKB-JSON** and **JSON operation in SQL** for trial
-  Each task involves unambiguous and straightforward user queries grounded in external knowledge, with medium to hard complexity SQL statements.


## 📦 Dataset Details

### Dataset Description

- **Database:** The database can be downloaded from [the HuggingFace](https://huggingface.co/datasets/birdsql/livesqlbench-base-lite)
- **Data Fields:**
   - `instance_id`: Unique task identifier
   - `selected_database`: Associated database name
   - `query`: Ambiguous user query
   - `sol_sql`: Ground truth SQL solution
   - `external_knowledge`: IDs of required external knowledge
   - `preprocess_sql`: SQL setup queries
   - `clean_up_sql`: SQL queries to reset database state
   - `test_cases`: Test cases to validate the predicted SQL
   - `category`: "Query" (SELECT-only) or "Management" (CRUD)
   - `high_level`: Boolean for high-level description
   - `conditions`: Indicates decimal/distinct conditions
   - `difficulty_tier`: Task difficulty (Simple, Moderate, Challenging)

**Data viewer**: Explore our data through data viewer in our website [livesqlbench.ai](https://livesqlbench.ai).

🔐 To avoid data leakage by auto-crawling, certain fields (e.g., `sol_sql`, `test_cases`, `external_knowledge`) are excluded from the public dataset `livesqlbench_data.jsonl`. For the full dataset, please email: **[📧 bird.bench25@gmail.com](mailto:bird.bench25@gmail.com)** with subject tag `[livesqlbench-base-lite GT&Test Cases]`, which will be sent automatically.




## 💨 Quick Eval

### Prepare the Dataset

Download the dataset containing DB's hkb, column meaning, schema and the `livesqlbench_data.jsonl` file:
```bash
cd livesqlbench
git clone https://huggingface.co/datasets/birdsql/livesqlbench-base-lite
```

Integrate the data file containing the annotated fields (obtained from the email) with the `livesqlbench_data.jsonl` file by running the following command:
```bash
python integrate_gt_data.py --gt_file <path_to_gt_file> 
```


### Environment Setup
To run the baseline code you need to install the following dependencies:
```bash
conda create -n livesqlbench python=3.10 -y
conda activate livesqlbench
pip install -r requirements.txt
```

### Generation
You also need to setup the model name (eg., **gpt-4o-2024-11-20**) with the API key in the `config.py` file. Then you can run the following command to generate the output:
```bash
# Generate the prompt
cd baseline/run
bash generate_prompt.sh

# LLM Inference, need to set the API key in config.py
bash run_baseline.sh
```
The output will be save in the [`./evaluation/outputs/final_output/`](./evaluation/outputs/final_output/)

### Evaluation
We use **docker** to provide a consistent environment for running the benchmark. To set up the environment, follow these steps:

1. First download the PostgreSQL database from [the Google Drive](https://drive.google.com/file/d/1KABce6czIqL9kMyIX7i-_A0CIQoDnmyW/view?usp=sharing).
2. Unzip the folder and save it in the [`./evaluation`](./evaluation) named with `postgre_table_dumps`
3. Build the docker compose
```bash
cd evaluation
docker compose up --build
```
4. Interact with the PostgreSQL database (Optional)
Use the `perform_query_on_postgresql_databases()` function in the `evaluation/src/db_utils.py` file to interact with the PostgreSQL database. `query` is the SQL query you want to run, and `db_name` is the name of the database you want to run the query on. The function will return the result of the query.
5. Run the evaluation script inside the `so_eval_env` container
```bash
docker compose exec so_eval_env bash
cd run
bash run_eval.sh 
```
The output will be save in the [`./evaluation/outputs/final_output/`](./evaluation/outputs/final_output/)
If you want the log file for each instance, you can set the `--logging` to `true` in the `run_eval.sh` script.


## 📊 Model Performance on LiveSQLBench-Base-Lite (2025-05-28)

| Rank | Model | Success Rate (%) | Avg. Cost (USD) / Task |
|------|-------|------------------|----------------------|
| 🥇 1 | o3-mini | 47.78 | 0.0233 |
| 🥈 2 | GPT-4.1 | 44.10 | 0.0336 |
| 🥉 3 | Claude Sonnet 4 | 42.59 | 0.0623 |
> More results can be found [here](https://livesqlbench.ai)

## 🔄 Upcoming Releases

- **🔄 LiveSQLBench-Base-Full:** 600 BI tasks, 200 management tasks, Document-based HKB
- **🔄 LiveSQLBench-Large-Lite:** Industrial-scale databases with 1340+ columns
- **🔄 LiveSQLBench-Large-Full:** Comprehensive large-scale datasets


### 📊 Feature Comparison

| Feature | LiveSQLBench-Base-Lite | LiveSQLBench-Base-Full | LiveSQLBench-Large-Full |
|---------|------------------------|------------------------|-------------------------|
| **User Tasks** | • 270 tasks<br>• Clear, direct queries with explicit DB/HKB connections<br>• Example1* | • 800 tasks <br>• Natural, colloquial queries with implicit DB/HKB connections<br>• Example2* | • 800 tasks<br>• Natural, colloquial queries with implicit DB/HKB connections<br>• Example2*, but with large DBs (industrial-scale DB)|
| **Database** | • 18 base databases<br>• ~127 columns per DB<br>• Simple 1:1 relationships<br>• Clean data (no nulls, consistent formats) | • 25 base databases<br>• ~127 columns per DB<br>• Complex relationships (1:1, 1:N, N:1, N:N)<br>• Real-world data quality (e.g., nulls, duplicates, inconsistent formats) | • 25 large databases<br>• ~1,340 columns per DB<br>• Complex relationships (1:1, 1:N, N:1, N:N)<br>• Real-world data quality (e.g., nulls, duplicates, inconsistent formats) |
| **Hierarchical Knowledge Base (HKB)** | • Structured HKB-JSON format only | • Dual format support:<br>1. Structured HKB-JSON<br>2. Unstructured HKB-Document | • Dual format support:<br>1. Structured HKB-JSON<br>2. Unstructured HKB-Document |

\* Example1 (more formal): *"For our archaeological site evaluation, I need to quantify the Digital Preservation Quality metrics across our collection. Please compute a comprehensive DPQ index for each archaeological location. Present the results in descending order of DPQ values, displaying only the site identification code, site designation, and calculated DPQ value (rounded to two decimal places) to facilitate prioritization of our digital preservation resources."*

\* Example2 (more colloquial): *"I need to assess digital preservation quality across our archaeological sites. Can you calculate a DPQ score for each location and show me the results ranked by quality? Just include the site code, designation, and DPQ value rounded to two decimals - I want to see which sites need attention first for our preservation planning."*


Want new dialects? Vote for new SQL dialects [🗳️ here](https://docs.google.com/forms/d/e/1FAIpQLSfEogmsA7LObI13KOoiojdnYfW28KEqvEVtC9hXaZJ8O9aCpQ/viewform?usp=header)!

## Created By:
BIRD Team & Google Cloud


## Changelog

<!-- summary -->

<details>
<summary>Changelog</summary>

All notable changes to this project will be documented in this file.

### 2025-06-06
- SQL evaluation postprocessing improvements:
  - Removed rounding in SQL postprocessing step
  - Added rounding of execution results to 2 decimal places
  - Modified comparison logic for ordered conditions:
    - Using list comparison when "order" is True in conditions
    - Using set comparison when "order" is False in conditions
</details>