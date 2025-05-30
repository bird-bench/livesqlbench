import argparse
import json
import re
import sys


def parse_sql(response: str) -> str:
    """Extracts the SQL query from the CoT model's response."""
    # First try to find SQL between triple backticks
    sql_match = re.search(r'```postgresql\n(.*?)\n```', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Try to find without ```postgresql
    sql_match = re.search(r'(.*?)```', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Then try to find SQL between single backticks
    sql_match = re.search(r'`(.*?)`', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    # Finally, try to find a SELECT statement
    sql_match = re.search(r'(SELECT\s+.*?;)', response, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    
    # If no SQL found, return empty string
    return ""


def extract_sql_from_response(response_string):
    """
    Extract all SQL code blocks wrapped with ```sql and ``` from the response string.
    Returns a list of SQL statements.
    """
    # sql_pattern = re.compile(
    #     r"(?:```postgresql)?\s*(.*?)```",   # Handle the case where the response is not wrapped in ```postgresql
    #     re.IGNORECASE | re.DOTALL,
    # )
    # # Find all matches
    # sql_statements = sql_pattern.findall(response_string)
    # # Strip whitespace from each statement
    # sql_statements = [stmt.strip() for stmt in sql_statements]
    sql_statements = [parse_sql(response_string)]

    return sql_statements


def process_file(input_file, output_file):
    """
    Process a JSONL file to extract SQL statements from responses.
    """
    with open(input_file, "r", encoding="utf-8") as infile, open(
        output_file, "w", encoding="utf-8"
    ) as outfile:
        for line_number, line in enumerate(infile, 1):
            # Parse the line as JSON
            try:
                data = json.loads(line.strip())
                response = data.get("response", "")

                # Extract SQL statements
                sql_list = extract_sql_from_response(response)
                print(
                    f"Extracted {len(sql_list)} SQL statements from line {line_number}"
                )
                # Add the list to the data
                data["pred_sqls"] = sql_list

                # Write the updated data
                outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
            except json.JSONDecodeError:
                print(
                    f"Skipping invalid JSON line {line_number}: {line.strip()}",
                    file=sys.stderr,
                )


def main():
    parser = argparse.ArgumentParser(
        description="Extract SQL statements from LLM responses."
    )
    parser.add_argument(
        "--input_path", type=str, required=True, help="Path to the input JSONL file."
    )
    parser.add_argument(
        "--output_path", type=str, required=True, help="Path to the output JSONL file."
    )
    args = parser.parse_args()

    process_file(args.input_path, args.output_path)


if __name__ == "__main__":
    main()
