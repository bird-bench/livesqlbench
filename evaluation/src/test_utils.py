import re 
from datetime import date, datetime
from db_utils import perform_query_on_postgresql_databases, execute_queries
import psycopg2
import json
from decimal import Decimal, ROUND_HALF_UP
import logging


def process_decimals(results, decimal_places):
    """
    Round any Decimal or float in the result set to `decimal_places`.
    """
    quantizer = Decimal(1).scaleb(-decimal_places)
    rounded = []
    for row in results:
        new_row = []
        for item in row:
            if isinstance(item, Decimal):
                new_row.append(item.quantize(quantizer, rounding=ROUND_HALF_UP))
            elif isinstance(item, float):
                new_row.append(round(item, decimal_places))
            else:
                new_row.append(item)
        rounded.append(tuple(new_row))
    return rounded



def remove_round_functions(sql_string):
    """
    Remove all ROUND() function calls from a SQL string, including nested ones.
    This regex properly handles nested functions with commas.
    """
    
    def find_matching_paren(text, start_pos):
        """Find the position of the matching closing parenthesis."""
        paren_count = 0
        for i in range(start_pos, len(text)):
            if text[i] == '(':
                paren_count += 1
            elif text[i] == ')':
                paren_count -= 1
                if paren_count == 0:
                    return i
        return -1
    
    def find_first_arg_end(text, start_pos):
        """Find the end of the first argument, accounting for nested parentheses."""
        paren_count = 0
        for i in range(start_pos, len(text)):
            if text[i] == '(':
                paren_count += 1
            elif text[i] == ')':
                if paren_count == 0:
                    return i  # End of ROUND function
                paren_count -= 1
            elif text[i] == ',' and paren_count == 0:
                return i  # End of first argument
        return len(text)
    
    result = sql_string
    
    while True:
        # Find ROUND function (case insensitive)
        pattern = re.compile(r'ROUND\s*\(', re.IGNORECASE)
        match = pattern.search(result)
        
        if not match:
            break
            
        start_pos = match.start()
        open_paren_pos = match.end() - 1
        
        # Find the end of the first argument
        first_arg_end = find_first_arg_end(result, open_paren_pos + 1)
        
        # Find the matching closing parenthesis
        close_paren_pos = find_matching_paren(result, open_paren_pos)
        
        if close_paren_pos == -1:
            break  # Malformed SQL, can't find closing paren
        
        # Extract the first argument
        first_arg = result[open_paren_pos + 1:first_arg_end].strip()
        
        # Replace ROUND(...) with just the first argument
        result = result[:start_pos] + first_arg + result[close_paren_pos + 1:]
    
    return result

def remove_round_functions_regex(sql_string):
    pattern = r'ROUND\s*\(([^,()]*(?:\([^()]*\)[^,()]*)*?)(?:,[^)]*)?\)'
    while True:
        new_result = re.sub(pattern, r'\1', sql_string, flags=re.IGNORECASE)
        if new_result == sql_string:  # No more changes made
            break
        sql_string = new_result
    return sql_string

def remove_round(sql_list):
    """
    Remove ROUND function calls while preserving the inner expression.
    For example: 
    - ROUND(column, 2) -> column
    - ROUND(ROUND(price, 2), 1) -> ROUND(price, 2) -> price (handles nested ROUNDs)
    """
    cleaned = []
    for sql in sql_list:
        result = sql
        result = remove_round_functions(result)
        cleaned.append(result)
        if "ROUND" in result:
            logging.warning(f"ROUND found in {result}")
    return cleaned


def process_decimals_recursive(item, decimal_places):
    """
    Recursively process decimals in any data structure (list, dict, tuple).
    Returns a new structure with all decimals rounded to specified places.
    """
    quantizer = Decimal(1).scaleb(-decimal_places)
    
    if isinstance(item, Decimal):
        return item.quantize(quantizer, rounding=ROUND_HALF_UP)
    elif isinstance(item, float):
        return round(item, decimal_places)
    elif isinstance(item, (list, tuple)):
        return type(item)(process_decimals_recursive(x, decimal_places) for x in item)
    elif isinstance(item, dict):
        return {k: process_decimals_recursive(v, decimal_places) for k, v in item.items()}
    else:
        return item

def preprocess_results(results, decimal_places=2):
    """
    Process the result set:
    - Replace dates with normalized string: YYYY-MM-DD
    - Convert tuples to lists for JSON serializability
    - Convert any unhashable types (dicts, lists) to their string representation for comparison
    - Process decimals recursively in all nested structures
    """
    processed = []
    for result in results:
        processed_result = []
        for item in result:
            if isinstance(item, (date, datetime)):
                processed_result.append(item.strftime('%Y-%m-%d'))
            else:
                # Process decimals recursively first
                processed_item = process_decimals_recursive(item, decimal_places)
                if isinstance(processed_item, (dict, list)):
                    # Convert unhashable types to their string representation with sorted keys
                    processed_result.append(json.dumps(processed_item, sort_keys=True))
                else:
                    processed_result.append(processed_item)
        processed.append(tuple(processed_result))
    return processed


def remove_distinct(sql_list):
    """
    Remove all occurrences of the DISTINCT keyword (in any case form)
    from a single list of SQL query strings. This is a brute-force
    approach without using regular expressions.

    Parameters:
    -----------
    sql_list : list of str
        A list of SQL queries (strings).

    Returns:
    --------
    list of str
        A new list of SQL queries with all 'DISTINCT' keywords removed.
    """

    cleaned_queries = []
    for query in sql_list:
        tokens = query.split(" ")
        filtered_tokens = []
        for token in tokens:
            # Check if this token is 'distinct' (case-insensitive)
            if token.lower() != 'distinct':
                filtered_tokens.append(token)
        cleaned_query = ' '.join(filtered_tokens)
        cleaned_queries.append(cleaned_query)

    return cleaned_queries

def check_sql_function_usage(sqls, required_keywords):
    """
    Check if the list of predicted SQL queries uses all of the specified keywords or functions.
    Returns 1 if all required keywords appear; otherwise returns 0.

    Args:
        sqls (list[str]): The list of predicted SQL queries.
        required_keywords (list[str]): The list of required keywords or functions.

    Returns:
        int: 1 if all required keywords appear, 0 if at least one is missing.
    """
    # Return 0 immediately if sqls is empty or None
    if not sqls:
        return 0

    # Combine all SQL queries into one string and convert to lowercase
    combined_sql = " ".join(sql.lower() for sql in sqls)

    # Check if all required keywords appear in combined_sql
    for kw in required_keywords:
        if kw.lower() not in combined_sql:
            return 0

    return 1

def ex_base(pred_sqls, sol_sqls, db_name, conn, conditions=None):
    """
    Compare result-sets of two lists of SQL queries:
    - Strip comments, DISTINCT, and ORDER BY
    - Execute
    - Normalize dates and optionally round decimals
    - Check equality (either ordered or unordered based on conditions)
    Return 1 on match, else 0.
    """
    if not pred_sqls or not sol_sqls:
        return 0

    # execute
    predicted_res, pred_err, pred_to = execute_queries(pred_sqls, db_name, conn, None, "")
    ground_res, gt_err, gt_to      = execute_queries(sol_sqls,  db_name, conn, None, "")
    if any([pred_err, pred_to, gt_err, gt_to]):
        return 0

    predicted_res = preprocess_results(predicted_res)
    ground_res    = preprocess_results(ground_res)
    if not predicted_res or not ground_res:
        return 0
    
    # Check if we should compare with order
    if conditions is not None and conditions.get("order", False):
        # Compare as lists to preserve order
        return 1 if predicted_res == ground_res else 0
    else:
        # Default: compare as sets (order doesn't matter)
        return 1 if set(predicted_res) == set(ground_res) else 0
    

def performance_compare_by_qep(old_sqls, sol_sqls, db_name, conn):
    """
    Compare total plan cost of old_sqls vs. sol_sqls in one connection,
    by using transactions + ROLLBACK to ensure each group sees the same initial state.
    
    Returns 1 if sol_sqls total plan cost is lower, otherwise 0.
    
    Notes:
      - If old_sqls/sol_sqls contain schema changes or data modifications,
        we rely on transaction rollback to discard those changes before measuring the other side.
      - EXPLAIN does not execute the query; it only returns the plan and cost estimate.
      - This approach ensures both sets see the same starting state for cost comparison.
    """

    if not old_sqls or not sol_sqls:
        print("Either old_sqls or sol_sqls is empty. Returning 0.")
        return 0
    print(f"Old SQLs are {old_sqls}")
    print(f"New SQLs are {sol_sqls}")

    def measure_sqls_cost(sql_list):
        """
        Measure the sum of 'Total Cost' for each DML statement in sql_list 
        via EXPLAIN (FORMAT JSON). Non-DML statements are just executed, but not included in the total cost.
        """
        total_cost = 0.0
        for sql in sql_list:
            upper_sql = sql.strip().upper()
            # We only measure DML cost for SELECT/INSERT/UPDATE/DELETE
            if not (upper_sql.startswith("SELECT") or
                    upper_sql.startswith("INSERT") or
                    upper_sql.startswith("UPDATE") or
                    upper_sql.startswith("DELETE")):
                print(f"[measure_sqls_cost] Skip EXPLAIN for non-DML: {sql}")
                try:
                    perform_query_on_postgresql_databases(sql, db_name, conn=conn)
                except Exception as exc:
                    print(f"[measure_sqls_cost] Error executing non-DML '{sql}': {exc}")
                continue

            explain_sql = f"EXPLAIN (FORMAT JSON) {sql}"
            try:
                result_rows, _ = perform_query_on_postgresql_databases(explain_sql, db_name, conn=conn)
                if not result_rows:
                    print(f"[measure_sqls_cost] No result returned for EXPLAIN: {sql}")
                    continue

                explain_json = result_rows[0][0]
                if isinstance(explain_json, str):
                    explain_json = json.loads(explain_json)

                if isinstance(explain_json, list) and len(explain_json) > 0:
                    plan_info = explain_json[0].get("Plan", {})
                    total_cost_part = plan_info.get("Total Cost", 0.0)
                else:
                    print(f"[measure_sqls_cost] Unexpected EXPLAIN JSON format for {sql}, skip cost.")
                    total_cost_part = 0.0

                total_cost += float(total_cost_part)

            except psycopg2.Error as e:
                print(f"[measure_sqls_cost] psycopg2 Error on SQL '{sql}': {e}")
            except Exception as e:
                print(f"[measure_sqls_cost] Unexpected error on SQL '{sql}': {e}")

        return total_cost

    # Measure cost for old_sqls
    try:
        perform_query_on_postgresql_databases("BEGIN", db_name, conn=conn)
        old_total_cost = measure_sqls_cost(old_sqls)
        print(f"Old SQLs total plan cost: {old_total_cost}")
    finally:
        perform_query_on_postgresql_databases("ROLLBACK", db_name, conn=conn)

    # Measure cost for sol_sqls
    try:
        perform_query_on_postgresql_databases("BEGIN", db_name, conn=conn)
        sol_total_cost = measure_sqls_cost(sol_sqls)
        print(f"Solution SQLs total plan cost: {sol_total_cost}")
    finally:
        perform_query_on_postgresql_databases("ROLLBACK", db_name, conn=conn)

    # Compare final costs
    print(f"[performance_compare_by_qep] Compare old({old_total_cost}) vs. sol({sol_total_cost})")
    return 1 if sol_total_cost < old_total_cost else 0

 
def remove_comments(sql_list): 
    """
    Remove all SQL comments from each query string in the list.
    - Block comments: /* ... */
    - Line comments: -- ... (to end of line)
    Also collapses multiple blank lines into one, and strips leading/trailing whitespace.
    """
    cleaned = []
    for sql in sql_list:
        # remove block comments
        no_block = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        # remove line comments, keep newline
        no_line  = re.sub(r'--.*?(\r\n|\r|\n)', r'\1', no_block)
        # collapse extra blank lines
        no_blank = re.sub(r'\n\s*\n+', '\n', no_line)
        cleaned.append(no_blank.strip())
    return cleaned


def test_case_default(pred_sqls, sol_sqls, db_name, conn, conditions):
    """
    Default test_case: pytest-style assertion.
    """
    # clean queries
    pred_sqls = remove_comments(pred_sqls)
    sol_sqls  = remove_comments(sol_sqls)
    pred_sqls = remove_distinct(pred_sqls)
    pred_sqls = remove_round(pred_sqls)
    sol_sqls  = remove_distinct(sol_sqls)
    sol_sqls  = remove_round(sol_sqls)

    result = ex_base(pred_sqls, sol_sqls, db_name, conn, conditions)
    assert result == 1, f"ex_base returned {result} but expected 1."
    return result


# NOTE: function name should be `test_case`, not `test_case_default`
TEST_CASE_DEFAULT="""
def test_case(pred_sqls, sol_sqls, db_name, conn, conditions):
    # clean queries
    pred_sqls = remove_comments(pred_sqls)
    sol_sqls  = remove_comments(sol_sqls)
    pred_sqls = remove_distinct(pred_sqls)
    pred_sqls = remove_round(pred_sqls)
    sol_sqls  = remove_distinct(sol_sqls)
    sol_sqls  = remove_round(sol_sqls)
    result = ex_base(pred_sqls, sol_sqls, db_name, conn, conditions)
    assert result == 1, f"ex_base returned {result} but expected 1."
    return result
"""

