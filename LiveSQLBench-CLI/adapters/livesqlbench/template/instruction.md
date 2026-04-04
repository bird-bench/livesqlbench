# LiveSQLBench Task for Harbor

## Objective
Generate a SQL query to answer the following question about a relational database.

## Task

### Query
```
{{QUERY}}
```

### Database
- **Name**: `{{DATABASE}}`
- **Description**: {{DATABASE_DESCRIPTION}}

## Expected Output

You must generate a SQL query and save it to `/app/pred.json` in the following format:

```json
{
  "instance_id": "solar_panel_xxx",
  "predicted_sql": ["SELECT ... FROM ... WHERE ..."]
}
```

**Important**: Your output MUST be a single JSON object containing:
- `instance_id`: the current task instance id
- `predicted_sql`: a non-empty list where the first item is your SQL string

## Evaluation

Your SQL query will be executed against the database and compared with the solution query. Your answer is correct if:
1. The query executes successfully (no syntax errors)
2. The result set matches the expected solution (same rows, order doesn't matter)

## Constraints

- Maximum query timeout: 60 seconds
- Maximum result size: 10,000 rows
- You have read-only access to the database
