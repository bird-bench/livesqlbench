# You need to modify the JSONL location or use the HuggingFace dataset in the evaluation.py file
jsonl_file="../outputs/final_output/gpt-4o-2024-11-20_assistant_final_output.jsonl"
python3 /app/src/evaluation.py --jsonl_file "$jsonl_file"
