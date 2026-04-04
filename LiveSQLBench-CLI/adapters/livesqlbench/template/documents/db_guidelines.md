# PostgreSQL Database Interaction Guide

This guide explains how to connect to the PostgreSQL server and execute SQL statements directly using `psql`.

---

## 1. Server Configuration

The PostgreSQL server is available with the following connection settings:

* **Host:** `postgresql`
* **Port:** `5432`
* **User:** `root`
* **Password:** `123123`
* **Database:** specify explicitly when connecting

Commonly, you are initialized with all these environment variables set (except for database). So you can connect the PostgreSQL server only specifying the database name.

---

## 2. Connecting to a Database

### Option A — One-time command

```bash
PGPASSWORD=123123 psql -h postgresql -p 5432 -U root -d <database_name>
```

Example:

```bash
PGPASSWORD=123123 psql -h postgresql -p 5432 -U root -d my_database
```

---

### Option B — Export environment variables (recommended for multiple commands)

```bash
export PGHOST=postgresql
export PGPORT=5432
export PGUSER=root
export PGPASSWORD=123123
```

Then connect with:

```bash
psql -d <database_name>
```

---

## 3. Basic SQL Execution

### Interactive mode

After connecting:

```sql
SELECT version();
SELECT current_database();
SELECT current_user;
```

Execute any SQL:

```sql
SELECT * FROM table_name LIMIT 10;
```

Exit:

```sql
\q
```

---

### Execute a single SQL statement from bash

```bash
psql -d <database_name> -c "SELECT * FROM table_name LIMIT 10;"
```

If not using environment variables:

```bash
PGPASSWORD=123123 psql -h postgresql -p 5432 -U root -d <database_name> -c "SELECT * FROM table_name LIMIT 10;"
```

---

### Execute a SQL file

```bash
psql -d <database_name> -f script.sql
```

---

## 4. Schema Exploration

Inside `psql`:

### List schemas

```sql
\dn
```

### List tables

```sql
\dt
```

### List tables in a specific schema

```sql
\dt schema_name.*
```

### Describe a table

```sql
\d table_name
```

### Detailed table information

```sql
\d+ table_name
```

---

## 5. Useful Inspection Queries

### Show current schema search path

```sql
SHOW search_path;
```

### Check connection info

```sql
\conninfo
```

### Preview rows safely

```sql
SELECT * FROM table_name LIMIT 20;
```

---

## 6. Handling Timeouts

If a query runs too long, PostgreSQL may cancel it depending on server configuration.

You must set a timeout manually for your session to control this behavior. For example, to set a 60-second timeout:

```sql
SET statement_timeout = '60s';
```

If you takes too much time in your task (say, more than 600s), you will be terminated by the system and this task will be marked as failed. Please make sure to avoid long-running queries and set a reasonable timeout.

---

## 7. Troubleshooting

### “Could not connect to server”

* Confirm PostgreSQL is running
* Confirm port is `5432`
* Ensure host is `postgresql`
* Reset environment variables in the db_env.sh

### Authentication failed

* Confirm `PGPASSWORD` is correct
* Confirm user is `root`

### No tables visible

* Check schema:

  ```sql
  \dn
  SHOW search_path;
  ```

---

## 8. Quick Verification Checklist

If something behaves unexpectedly:

```bash
psql --version
```

```bash
PGPASSWORD=123123 psql -h postgresql -p 5432 -U root -d <database_name> -c "SELECT 1;"
```

If that works, the connection is correctly configured.