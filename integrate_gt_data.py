#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load data from a JSONL file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():  # Skip empty lines
                data.append(json.loads(line))
    return data

def save_jsonl(data: List[Dict[str, Any]], file_path: str) -> None:
    """Save data to a JSONL file."""
    # Create a backup of the original file
    backup_path = str(Path(file_path).with_suffix('.jsonl.bak'))
    Path(file_path).rename(backup_path)
    logger.info(f"Created backup of original file at {backup_path}")
    
    # Write the new data
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def integrate_data(public_data: List[Dict[str, Any]], gt_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Integrate ground truth data with public data based on instance_id."""
    # Create lookup dictionary for ground truth data
    gt_lookup = {item['instance_id']: item for item in gt_data}
    
    # Integrate data
    integrated_data = []
    for item in public_data:
        instance_id = item['instance_id']
        if instance_id in gt_lookup:
            # Merge the ground truth fields
            gt_item = gt_lookup[instance_id]
            integrated_item = item.copy()
            # Add the protected fields from ground truth
            for field in ['sol_sql', 'test_cases', 'external_knowledge']:
                if field in gt_item:
                    integrated_item[field] = gt_item[field]
            integrated_data.append(integrated_item)
        else:
            logger.warning(f"Instance {instance_id} not found in ground truth data")
            integrated_data.append(item)
    
    return integrated_data

def main():
    parser = argparse.ArgumentParser(description='Integrate ground truth data with public dataset')
    parser.add_argument('--gt_file', required=True, help='Path to the ground truth data file')
    parser.add_argument('--public_file', default='livesqlbench-base-lite/livesqlbench_data.jsonl', 
                      help='Path to the public dataset file (default: livesqlbench_data.jsonl)')
    
    args = parser.parse_args()
    
    # Validate input files exist
    if not Path(args.gt_file).exists():
        raise FileNotFoundError(f"Ground truth file not found: {args.gt_file}")
    if not Path(args.public_file).exists():
        raise FileNotFoundError(f"Public dataset file not found: {args.public_file}")
    
    # Load data
    logger.info(f"Loading public dataset from {args.public_file}")
    public_data = load_jsonl(args.public_file)
    logger.info(f"Loading ground truth data from {args.gt_file}")
    gt_data = load_jsonl(args.gt_file)
    
    # Integrate data
    logger.info("Integrating datasets...")
    integrated_data = integrate_data(public_data, gt_data)
    
    # Save integrated data back to the original file
    logger.info(f"Writing integrated data back to {args.public_file}")
    save_jsonl(integrated_data, args.public_file)
    
    logger.info("Integration complete!")
    logger.info(f"Processed {len(public_data)} instances from public dataset")
    logger.info(f"Found {len(gt_data)} instances in ground truth data")
    logger.info(f"Updated {len(integrated_data)} instances in the dataset")

if __name__ == '__main__':
    main()
