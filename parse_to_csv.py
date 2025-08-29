#!/usr/bin/env python3
"""Parse caption data and output to CSV format with multiple entries per image"""

import json
import re
import csv
import os
import random

# === CONFIGURATION ===
INPUT_FILES = [
    # "/home/cynapse/terence/database/blip/results/tqvcd_filelist_temp0_topk1_topp1_readable.txt",
    # "/home/cynapse/terence/database/blip/results/usroad_filelist_temp0_topk1_topp1_readable.txt",
    "/home/cynapse/terence/database/blip/results/stanford_filelist_temp0_topk1_topp1_readable.txt",
    "/home/cynapse/terence/database/blip/results/kaggle_filelist_temp0_topk1_topp1_readable.txt"
]
OUTPUT_DIR = '/home/cynapse/zhenyang/caption_parser/output_csv/'
# OUTPUT_DIR = '/home/cynapse/terence/open_clip/data'
VISIBILITY_THRESHOLD = 50
OUTPUT_SUFFIX = 'combined_blip_caption_csv'
MAX_WORDS = 30
COMBINE_CAPTIONS = True
TRAIN_RATIO = 0.8
VAL_RATIO = 0.2

# === CSV FORMAT OPTIONS ===
CSV_IMG_KEY = 'image_path'
CSV_CAPTION_KEY = 'caption'
CSV_SEPARATOR = ','  # Use ',' for CSV or '\t' for TSV

# === TAG FILTERING ===
INCLUDE_TAGS = {
    '[Subject]': False, 
    '[Camera]': False, 
    '[Info]': True, 
    '[Accessories]': True,
    '[Graphics]': False, 
    '[Damage]': True, 
    '[Condition]': True, 
    '[Others]': False
}
INCLUDE_ALL_TAGS = False
INCLUDE_TASK_4 = False
DEBUG_TAG_FILTERING = False

def filter_tags(line):
    """Filter content based on tag configuration - only keeps content from enabled tags"""
    if not line:
        return line.strip()
    
    if INCLUDE_ALL_TAGS:
        return re.sub(r'\[.*?\]\s*', '', line).strip()
    
    tags = re.findall(r'\[.*?\]', line)
    if not tags:
        return line.strip()
    
    if DEBUG_TAG_FILTERING:
        print(f"Original: {line} | Tags: {tags}")
    
    has_enabled_tag = any(tag in INCLUDE_TAGS and INCLUDE_TAGS[tag] for tag in tags)
    if not has_enabled_tag:
        return ''
    
    result_parts = []
    parts = re.split(r'(\[.*?\])', line)
    
    for i, part in enumerate(parts):
        if part.startswith('[') and part.endswith(']'):
            tag = part
            if tag in INCLUDE_TAGS and INCLUDE_TAGS[tag]:
                if i + 1 < len(parts):
                    content = parts[i + 1].strip()
                    if content:
                        result_parts.append(content)
    
    result = ' '.join(result_parts).strip()
    
    if DEBUG_TAG_FILTERING:
        print(f"Filtered result: {result}")
    
    return result

def parse_to_json(filename):
    """Parse input file and return structured data"""
    results = []
    
    with open(filename, 'r') as file:
        content = file.read()
    
    entries = content.strip().split('\n\n')
    
    for entry in entries:
        if not entry.strip():
            continue
            
        lines = entry.strip().split('\n')
        if not lines or ':' not in lines[0]:
            continue
            
        image_path = lines[0].split(':')[0].strip()
        entry_dict = {"image": image_path}
        
        current_task = None
        current_content = []
        
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('Task '):
                if current_task:
                    entry_dict[current_task] = current_content
                current_task = line
                current_content = []
            elif line:
                cleaned_line = filter_tags(line)
                if cleaned_line:
                    current_content.append(cleaned_line)
        
        if current_task:
            entry_dict[current_task] = current_content
        
        results.append(entry_dict)
    
    return results

def check_task5_vehicle_yes(entry_dict):
    """Check if Task 5 contains 'Vehicle: Yes'"""
    if 'Task 5' not in entry_dict:
        return False
    return any(line.strip() == 'Vehicle: Yes' for line in entry_dict['Task 5'])

def check_task6_visibility_N_plus(entry_dict):
    """Check if Task 6 visibility >= threshold"""
    if 'Task 6' not in entry_dict:
        return False
    for line in entry_dict['Task 6']:
        if line.strip().startswith("Visibility = "):
            try:
                visibility_value = int(line.strip().split("= ")[1])
                return visibility_value >= VISIBILITY_THRESHOLD
            except (ValueError, IndexError):
                continue
    return False

def check_task7_visibility_day(entry_dict):
    """Check if Task 7 contains 'Time = day'"""
    if 'Task 7' not in entry_dict:
        return False
    return any(line.strip() == 'Time = day' for line in entry_dict['Task 7'])

def check_task8_multiple_no(entry_dict):
    """Check if Task 8 contains 'Multiple = no'"""
    if 'Task 8' not in entry_dict:
        return False
    return any(line.strip() == 'Multiple = no' for line in entry_dict['Task 8'])

def generate_combined_captions(captions, max_words=20):
    """Combine captions using the specified strategy"""
    if len(captions) <= 1:
        return captions
    
    shuffled_captions = list(captions)
    random.shuffle(shuffled_captions)
    
    total_words = sum(len(caption.split()) for caption in captions)
    target_caption_count = max(1, total_words // max_words + 1)
    
    # Ensure we don't create more groups than we have captions
    target_caption_count = min(target_caption_count, len(captions))
    
    # Distribute captions evenly across target count
    captions_per_group = len(shuffled_captions) // target_caption_count
    remainder = len(shuffled_captions) % target_caption_count
    
    combined_captions = []
    start_idx = 0
    
    for i in range(target_caption_count):
        # Add extra caption to first 'remainder' groups for even distribution
        current_captions = captions_per_group + (1 if i < remainder else 0)
        end_idx = start_idx + current_captions
        
        group_captions = shuffled_captions[start_idx:end_idx]
        combined_captions.append(", ".join(group_captions))
        start_idx = end_idx
    
    # If we have remaining captions, add them to the last group
    if start_idx < len(shuffled_captions):
        remaining_captions = shuffled_captions[start_idx:]
        if combined_captions:
            combined_captions[-1] += ", " + ", ".join(remaining_captions)
        else:
            combined_captions.append(", ".join(remaining_captions))
    
    return combined_captions

def split_data(data, train_ratio, val_ratio):
    """Split data into train, test, and val sets"""
    # Shuffle data for random distribution
    shuffled_data = list(data)
    random.shuffle(shuffled_data)
    
    total_count = len(shuffled_data)
    train_count = int(total_count * train_ratio)
    
    # Split into train and test (remaining)
    train_data = shuffled_data[:train_count]
    test_data = shuffled_data[train_count:]
    
    # Split val from test data
    val_count = int(len(test_data) * val_ratio)
    val_data = test_data[:val_count]
    
    return train_data, test_data, val_data

def main():
    print("=== TAG FILTERING CONFIGURATION ===")
    print("Content filtering based on tags (tags are always removed from output):")
    for tag, include in INCLUDE_TAGS.items():
        status = "✅ KEEP content" if include else "❌ REMOVE content"
        print(f"  {tag}: {status}")
    
    print(f"\nINCLUDE_ALL_TAGS: {INCLUDE_ALL_TAGS}")
    print("\n" + "="*50 + "\n")
    
    all_results = []
    
    # Process each input file
    for input_file in INPUT_FILES:
        print(f"Parsing {input_file}...")
        if os.path.exists(input_file):
            file_results = parse_to_json(input_file)
            all_results.extend(file_results)
            print(f"  Added {len(file_results)} entries")
        else:
            print(f"  ⚠️  File not found, skipping")
    
    filtered_results = []
    
    print(f"\n=== FILTERING BY TASK 5, 6, 7, AND 8 ===")
    
    for i, entry_dict in enumerate(all_results, 1):
        task5_pass = check_task5_vehicle_yes(entry_dict)
        task6_pass = check_task6_visibility_N_plus(entry_dict)
        task7_pass = check_task7_visibility_day(entry_dict)
        task8_pass = check_task8_multiple_no(entry_dict)
        
        overall_pass = all([task5_pass, task6_pass, task7_pass, task8_pass])
        
        if overall_pass:
            filtered_results.append(entry_dict)
    
    print(f"=== SUMMARY ===")
    print(f"Total entries: {len(all_results)} | Passing: {len(filtered_results)}")
    
    # Split data into train, test, val
    train_data, test_data, val_data = split_data(filtered_results, TRAIN_RATIO, VAL_RATIO)
    
    # Prepare CSV data for each split
    def prepare_csv_data(data_split):
        csv_data = []
        for entry in data_split:
            image_path = entry['image']
            
            # Get damage level for Task 4 filtering
            damage_level = 'N/A'
            if 'Task 3' in entry:
                for line in entry['Task 3']:
                    if line.startswith('Damage = '):
                        damage_level = line.split('Damage = ')[1].strip()
                        break
            
            # Collect all captions
            captions = []
            if 'Task 1' in entry:
                captions.extend(entry['Task 1'])
            
            # Add Task 4 captions if damage level is present and INCLUDE_TASK_4 is True
            if damage_level != 'N/A' and 'Task 4' in entry and INCLUDE_TASK_4:
                for line in entry['Task 4']:
                    if line.strip() and line.strip().upper() != 'NA':
                        captions.append(line.strip())
            
            # Apply caption combining strategy if enabled
            if COMBINE_CAPTIONS and captions:
                captions = generate_combined_captions(captions, MAX_WORDS)
            
            # Create multiple CSV rows for each caption
            for caption in captions:
                csv_data.append({
                    CSV_IMG_KEY: image_path,
                    CSV_CAPTION_KEY: caption
                })
        return csv_data
    
    # Generate CSV data for each split
    train_csv = prepare_csv_data(train_data)
    test_csv = prepare_csv_data(test_data)
    val_csv = prepare_csv_data(val_data)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Write separate CSV files for each split
    splits = [
        ('train', train_csv),
        ('test', test_csv),
        ('val', val_csv)
    ]
    
    for split_name, csv_data in splits:
        csv_output_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_SUFFIX}_{split_name}.csv")
        
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [CSV_IMG_KEY, CSV_CAPTION_KEY]
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=CSV_SEPARATOR)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"{split_name.upper()} CSV: {csv_output_path} ({len(csv_data)} entries)")
    
    # Print split statistics
    print(f"\n=== SPLIT STATISTICS ===")
    print(f"Train: {len(train_data)} images ({len(train_csv)} caption entries)")
    print(f"Test: {len(test_data)} images ({len(test_csv)} caption entries)")
    print(f"Val: {len(val_data)} images ({len(val_csv)} caption entries)")
    
    train_pct = len(train_data) / len(filtered_results) * 100
    test_pct = len(test_data) / len(filtered_results) * 100
    val_pct = len(val_data) / len(filtered_results) * 100
    print(f"Percentages - Train: {train_pct:.1f}%, Test: {test_pct:.1f}%, Val: {val_pct:.1f}%")
    
    return train_csv, test_csv, val_csv

if __name__ == "__main__":
    main()