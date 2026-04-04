# Task: Write PostgreSQL to Solve the User Query

Working on a relational database `{db_name}`, and solve the user's query:

You are given:
- `documents/db_env.sh`: the environment variables used for connecting to the database
- `documents/db_guidelines.md`: how to interact with PostgreSQL database
- `documents/README_TASK.md`: (this document) documented task requirements
- `documents/user_query.md`: documented user query
- `db_assets/{db_name}_column_meaning_base.json`: the database column meaning
- `db_assets/{db_name}_kb.jsonl`: the knowledge base related to the database
- `db_assets/{db_name}_schema.txt`: database schema + sample rows

## Goal
Produce executable and correct SQL that solves the user's query.

You may use bash commands, file operations, and python code to help you understand the user query and explore the database. Finally you should write the answer SQL in `pred.json` as described below.

## Output format (MANDATORY)
Write a file in `/app/pred.json` with **exactly** this JSON:

```json
{{
  "instance_id": "{instance_id}",
  "predicted_sql": ["<SQL1>", "<SQL2>", "..."]
}}
```


## Rules

- Always explore the working directory and check the files before you write the `pred.json`. The files may contain useful information that can help you understand the user query and write the SQL.

- `predicted_sql` must always be a JSON list (even if there is only one SQL).

- Put SQL strings only. No markdown fences or comments.

- Before you write the predicted SQL and finish, make sure to test the SQL in the database environment. Detailed instructions on how to do that are in `db_guidelines.md`. You can also use bash commands and python code to help you test the SQL.

- Besides testing, interact with the database can also help you understand the query and database layout. You are encouraged to use bash commands and python code to do that.

## Constraints

- Maximum query timeout: 600 seconds
- Output format: pred.json
- You must execute your answer SQL on the database to valiate

Now working on this query:

## Query
```
{user_query}
```