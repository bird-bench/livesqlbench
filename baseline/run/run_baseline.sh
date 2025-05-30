set -e
set -x

prompt_path="../prompts/assistant.jsonl"
output_dir="../../evaluation/outputs"
model="gpt-4o-2024-11-20"
inter_output_path="${output_dir}/inter_output/${model}_assistant_inter_output.jsonl"
mkdir -p "${output_dir}/inter_output"
python ../src/call_api.py --prompt_path $prompt_path --output_path $inter_output_path --model_name $model

final_output_path="${output_dir}/final_output/${model}_assistant_final_output.jsonl"
mkdir -p "${output_dir}/final_output"
python ../src/post_process.py --input_path $inter_output_path --output_path $final_output_path