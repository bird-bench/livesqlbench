import argparse
import json
import re
import sys

from tqdm import tqdm
VERBOSE = False


def parse_sql(response: str) -> str:
    """Extracts the SQL query from the CoT model's response."""
    if "`" in response:
        # First try to find SQL between triple backticks
        sql_match = re.search(r'```postgresql(.*?)```', response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()

        # Then try to find SQL between triple backticks
        sql_match = re.search(r'```sql(.*?)```', response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        
        # Then try to find SQL between ```  ```
        sql_match = re.search(r'```(.*?)```', response, re.DOTALL)
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
    else:
        # Finally, try to find a SELECT statement
        sql_match = re.search(r'(SELECT\s+.*?;)', response, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
    # If no SQL found, return empty string
    return response


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
    total_sql_count = 0
    empty_sql_list = []

    with open(input_file, "r", encoding="utf-8") as infile, open(
        output_file, "w", encoding="utf-8"
    ) as outfile:
        for line_number, line in tqdm(enumerate(infile, 1)):
            # print(line_number)
            # Parse the line as JSON
            try:
                data = json.loads(line.strip())
                response = data.get("response", "")

                # Extract SQL statements
                # print(">>>>")
                # print("response: ", response)
                # print(">>>>")
                sql_list = extract_sql_from_response(response)
                if sql_list == [""]:
                    empty_sql_list.append(line_number)
                if VERBOSE:
                    print(
                        f"Extracted {len(sql_list)} SQL statements from line {line_number}"
                    )
                # Add the list to the data
                data["pred_sqls"] = sql_list
                total_sql_count += len(sql_list)
                # Write the updated data
                outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
            except json.JSONDecodeError:
                print(
                    f"Skipping invalid JSON line {line_number}: {line.strip()}",
                    file=sys.stderr,
                )
    print(f"Total SQL count: {total_sql_count}")
    if len(empty_sql_list) > 0:   
        print(f"❌ Total empty SQL count: {len(empty_sql_list)}")
        print(f"❌ Empty SQL list: {empty_sql_list}")
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
