#!/usr/bin/env python3
"""Convert JSON file with image-caption pairs to CSV format"""

import json
import csv
import os
import argparse

# === CONFIGURATION ===
DEFAULT_INPUT_JSON = '/home/cynapse/zhenyang/caption_parser/val_KagUSstan30_all.json'
DEFAULT_OUTPUT_DIR = '/home/cynapse/zhenyang/caption_parser/output_csv/'

def convert_json_to_csv(json_file_path, csv_file_path):
    """Convert JSON file to CSV with image_path and caption headers"""
    
    # Read JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Prepare CSV data
    csv_data = []
    for image_id, item in enumerate(data):
        image_path = item['image']
        captions = item['caption']
        
        # Create multiple entries for each caption with same image_id
        for caption in captions:
            csv_data.append({
                'image_id': image_id,
                'image_path': image_path,
                'caption': caption
            })
    
    # Write CSV file
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['image_id', 'image_path', 'caption']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    print(f"Converted {len(data)} images with {len(csv_data)} total caption entries to {csv_file_path}")

def main():
    parser = argparse.ArgumentParser(description='Convert JSON file with image-caption pairs to CSV format')
    parser.add_argument('input_json', nargs='?', default=DEFAULT_INPUT_JSON, help=f'Path to input JSON file (default: {DEFAULT_INPUT_JSON})')
    parser.add_argument('-o', '--output-dir', default=DEFAULT_OUTPUT_DIR, help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_json):
        print(f"Error: Input file {args.input_json} not found")
        return
    
    # Generate output filename based on input filename
    input_basename = os.path.basename(args.input_json)
    output_filename = os.path.splitext(input_basename)[0] + '.csv'
    csv_file = os.path.join(args.output_dir, output_filename)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Convert JSON to CSV
    convert_json_to_csv(args.input_json, csv_file)

if __name__ == "__main__":
    main()