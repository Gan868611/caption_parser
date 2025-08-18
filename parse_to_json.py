#!/usr/bin/env python3
"""Parse caption data with intelligent content filtering based on [xxxx] tags"""

import json
import re
import csv
import os

# === CONFIGURATION ===
INPUT_FILE = "/home/cynapse/terence/database/blip/results/stanford_filelist_temp0_topk1_topp1_readable.txt"
OUTPUT_DIR = '/home/cynapse/terence/database/blip/results/blip_caption/'
CSV_OUTDIR = '/home/cynapse/terence/database/blip/results/blip_caption/csv_check/'
# OUTPUT_DIR = '/home/cynapse/zhenyang/caption_parser/output_json/'
# CSV_OUTDIR = '/home/cynapse/zhenyang/caption_parser/output_csv/'
VISIBILITY_THRESHOLD = 50
OUTPUT_SUFFIX = 'blip_caption_(Info_only)'

# === TAG FILTERING ===
INCLUDE_TAGS = {
    '[Subject]': False, 
    '[Camera]': False, 
    '[Info]': True, 
    '[Accessories]': False,
    '[Graphics]': False, 
    '[Damage]': False, 
    '[Condition]': False, 
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

def main():
    print("=== TAG FILTERING CONFIGURATION ===")
    print("Content filtering based on tags (tags are always removed from output):")
    for tag, include in INCLUDE_TAGS.items():
        status = "✅ KEEP content" if include else "❌ REMOVE content"
        print(f"  {tag}: {status}")
    
    print(f"\nINCLUDE_ALL_TAGS: {INCLUDE_ALL_TAGS}")
    print("\n" + "="*50 + "\n")
    
    print(f"Parsing {INPUT_FILE}...")
    all_results = parse_to_json(INPUT_FILE)
    
    csv_data = []
    filtered_results = []
    
    print(f"\n=== FILTERING BY TASK 5, 6, 7, AND 8 ===")
    
    for i, entry_dict in enumerate(all_results, 1):
        task5_pass = check_task5_vehicle_yes(entry_dict)
        task6_pass = check_task6_visibility_N_plus(entry_dict)
        task7_pass = check_task7_visibility_day(entry_dict)
        task8_pass = check_task8_multiple_no(entry_dict)
        
        overall_pass = all([task5_pass, task6_pass, task7_pass, task8_pass])
        
        damage_level = 'N/A'
        if 'Task 3' in entry_dict:
            for line in entry_dict['Task 3']:
                if line.startswith('Damage = '):
                    damage_level = line.split('Damage = ')[1].strip()
                    break

        csv_data.append({
            'Image': entry_dict['image'],
            'Task 3 (Damage)': damage_level,
            'Task 5 (Vehicle)': 'PASS' if task5_pass else 'FAIL',
            'Task 6 (Visibility)': 'PASS' if task6_pass else 'FAIL',
            'Task 7 (Time)': 'PASS' if task7_pass else 'FAIL',
            'Task 8 (Multiple)': 'PASS' if task8_pass else 'FAIL',
            'Overall Result': 'PASS' if overall_pass else 'FAIL'
        })
        
        if overall_pass:
            filtered_results.append(entry_dict)
    
    print(f"=== SUMMARY ===")
    print(f"Total entries: {len(all_results)} | Passing: {len(filtered_results)}")
    
    # Build output
    output_list = []
    for entry in filtered_results:
        captions = []
        if 'Task 1' in entry:
            captions.extend(entry['Task 1'])
        
        damage_level = None
        if 'Task 3' in entry:
            for line in entry['Task 3']:
                if line.startswith('Damage = '):
                    value = line.split('Damage = ')[1].strip()
                    if any(level in value for level in ['Minor', 'Moderate', 'Severe']):
                        damage_level = next(level for level in ['Minor', 'Moderate', 'Severe'] if level in value)
                        break
        

        if damage_level and 'Task 4' in entry and INCLUDE_TASK_4:
            for line in entry['Task 4']:
                if line.strip() and line.strip().upper() != 'NA':
                    captions.append(line.strip())

        output_list.append({
            'image': entry['image'],
            'caption': captions
        })

    # Write outputs
    input_base = INPUT_FILE.split('/')[-1].split('.')[0]
    output_path = f"{OUTPUT_DIR}/{input_base}_{OUTPUT_SUFFIX}.json"
    csv_output_path = os.path.join(CSV_OUTDIR, f"{input_base}_task_checks.csv")
    
    with open(output_path, 'w') as f:
        json.dump(output_list, f, indent=2)
    print(f"JSON output: {output_path}")
    
    with open(csv_output_path, 'w', newline='') as f:
        fieldnames = ['Image', 'Task 3 (Damage)', 'Task 5 (Vehicle)', 'Task 6 (Visibility)', 'Task 7 (Time)', 'Task 8 (Multiple)', 'Overall Result']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    print(f"CSV output: {csv_output_path}")

    return filtered_results

if __name__ == "__main__":
    main()
