#!/usr/bin/env python3
import argparse
import os
import pandas as pd
import json
from pathlib import Path
from backend.data_processors.data_processor import load_data, validate_equipment_data
from backend.valuation_engine.claude_valuation import process_equipment_list

def parse_args():
    parser = argparse.ArgumentParser(description='Batch process equipment valuations')
    parser.add_argument('--input', '-i', required=True, help='Input CSV or Excel file with equipment list')
    parser.add_argument('--output', '-o', required=True, help='Output directory for valuation results')
    parser.add_argument('--limit', '-l', type=int, help='Limit processing to N items', default=None)
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist")
        return 1
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    print(f"Loading data from {args.input}...")
    df = load_data(args.input)
    validated_df = validate_equipment_data(df)
    
    print(f"Processing {args.limit if args.limit else 'all'} equipment items...")
    results = process_equipment_list(validated_df, max_items=args.limit)
    
    print(f"Writing results to {args.output}...")
    
    # Save individual JSON files for each equipment item
    for unit_id, result in results.items():
        # Clean unit_id to be used as a filename
        safe_id = str(unit_id).replace('/', '-').replace('\\', '-')
        output_file = os.path.join(args.output, f"{safe_id}.json")
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
    
    # Save a combined results file
    combined_file = os.path.join(args.output, "combined_results.json")
    with open(combined_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Successfully processed {len(results)} equipment items")
    print(f"Results saved to {args.output}")
    
    return 0

if __name__ == "__main__":
    exit(main())