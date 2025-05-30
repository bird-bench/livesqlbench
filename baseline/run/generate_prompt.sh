data_path="../../livesqlbench-base-lite/livesqlbench_data.jsonl"
assistant_prompt_path="../prompts/assistant.jsonl"
python ../src/prompt_generator.py \
    --data_path $data_path \
    --prompt_path $assistant_prompt_path \
    --prompt_type "assistant" \
    --data_path_base "../../livesqlbench-base-lite"