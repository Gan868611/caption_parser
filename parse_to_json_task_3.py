#!/usr/bin/env python3
"""Parse caption data with intelligent content filtering based on [xxxx] tags"""

import json
import re
import csv
import os

# === CONFIGURATION ===
INPUT_FILES = {
    'gemini': "/home/cynapse/terence/database/blip/results/usroad_filelist_temp0_topk1_topp1_readable.txt",
    'openai': "/home/cynapse/terence/database/blip/results_openai/usroad_filelist_damage_temp0_topk1_topp1_readable.txt"
}

ITERATION_CONFIG = [
    ('gemini_non_damage', 'gemini'),
    ('openai_non_damage', 'openai'),
    ('gemini_and_openai_damage', 'openai'),
    ('gemini_and_openai_damage', 'gemini')
]

OUTPUT_SUFFIX = "blip_caption_idca"


DAMAGE_FILTERS = {
    'gemini_non_damage': ['None'],
    'openai_non_damage': ['None'],
    'gemini_and_openai_damage': ['Moderate', 'Severe', 'Minor'],
    'gemini_and_openai_damage': ['Moderate', 'Severe', 'Minor'],
}

OUTPUT_DIR = '/home/cynapse/zhenyang/caption_parser/output_json/'
CSV_OUTDIR = '/home/cynapse/zhenyang/caption_parser/output_csv/'
VISIBILITY_THRESHOLD = 45

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

def filter_tags(line):
    """Filter content based on tag configuration"""
    if not line:
        return line.strip()
    
    if INCLUDE_ALL_TAGS:
        return re.sub(r'\[.*?\]\s*', '', line).strip()
    
    tags = re.findall(r'\[.*?\]', line)
    if not tags:
        return line.strip()
    
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
    
    return ' '.join(result_parts).strip()

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

def filter_task_3(entry_dict, damage_filter):
    """Filter Task 3 based on damage values"""
    if 'Task 3' not in entry_dict:
        return False
    
    task3_content = entry_dict['Task 3']
    for line in task3_content:
        if line.startswith('Damage = '):
            damage_value = line.split('Damage = ')[1].strip()
            if any(x.lower() in damage_value.lower() for x in damage_filter):
                return True
    return False

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
    for tag, include in INCLUDE_TAGS.items():
        status = "✅ KEEP content" if include else "❌ REMOVE content"
        print(f"  {tag}: {status}")
    print(f"\nINCLUDE_ALL_TAGS: {INCLUDE_ALL_TAGS}")
    print("="*50 + "\n")

    gemini_and_openai_damage_list = set()
    openai_output_path = None
    
    # Process each iteration
    for iteration_name, input_file_key in ITERATION_CONFIG:
        print(f"{'='*60}")
        print(f"ITERATION {iteration_name.upper()}")
        print(f"Input file: {INPUT_FILES[input_file_key]}")
        print(f"Damage filter: {DAMAGE_FILTERS[iteration_name]}")
        print(f"{'='*60}\n")
        
        current_damage_filter = DAMAGE_FILTERS[iteration_name]
        
        print(f"Parsing {INPUT_FILES[input_file_key]}...")
        all_results = parse_to_json(INPUT_FILES[input_file_key])
        
        csv_data = []
        filtered_results = []
        
        print("=== FILTERING BY TASK 5, 6, 7, AND 8 ===")

        for entry_dict in all_results:
            task5_pass = check_task5_vehicle_yes(entry_dict)
            task6_pass = check_task6_visibility_N_plus(entry_dict)
            task7_pass = check_task7_visibility_day(entry_dict)
            task8_pass = check_task8_multiple_no(entry_dict)
            task3_pass = filter_task_3(entry_dict, current_damage_filter)
            
            overall_pass = all([task5_pass, task6_pass, task7_pass, task8_pass, task3_pass])

            if iteration_name == 'gemini_and_openai_damage' and input_file_key == 'gemini':
                if entry_dict['image'] not in gemini_and_openai_damage_list:
                    overall_pass = False

            # if entry_dict['image'] not in content:
            #     overall_pass = False
            
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
                if iteration_name == 'gemini_and_openai_damage' and input_file_key == 'openai':
                    gemini_and_openai_damage_list.add(entry_dict['image'])
                filtered_results.append(entry_dict)
        
        print(f"=== SUMMARY FOR {iteration_name.upper()} ===")
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
                        if any(level in value for level in ['Minor', 'Moderate', 'Severe', 'None']):
                            damage_level = next(level for level in ['Minor', 'Moderate', 'Severe', 'None'] if level in value)
                            break
            
            if damage_level and 'Task 4' in entry and INCLUDE_TASK_4:
                for line in entry['Task 4']:
                    if line.strip() and line.strip().upper() != 'NA':
                        captions.append(line.strip())

            output_list.append({
                'image': entry['image'],
                'caption': captions
            })

        # Write outputs for this iteration
        input_base = INPUT_FILES[input_file_key].split('/')[-1].split('.')[0]
        output_suffix = f"{OUTPUT_SUFFIX}_{iteration_name}"
        output_path = f"{OUTPUT_DIR}/{input_base}_{output_suffix}.json"
        csv_output_path = os.path.join(CSV_OUTDIR, f"{input_base}_{iteration_name}_task_checks.csv")

        if iteration_name == 'gemini_and_openai_damage' and input_file_key == 'openai':
            openai_output_path = output_path

        if iteration_name == 'gemini_and_openai_damage' and input_file_key == 'gemini':
            # Append captions to existing JSON file for matching images
            output_path = openai_output_path
            
            # Load existing JSON file if it exists
            existing_data = []
            if os.path.exists(output_path):
                with open(output_path, 'r') as f:
                    existing_data = json.load(f)
            
            # Create a mapping of existing images to their data
            existing_image_map = {item['image']: item for item in existing_data}
            
            # Append captions for matching images
            for output_item in output_list:
                image_name = output_item['image']
                if image_name in existing_image_map:
                    # Append new captions to existing ones
                    existing_image_map[image_name]['caption'].extend(output_item['caption'])
                else:
                    # Add new entry if image doesn't exist
                    existing_data.append(output_item)
            
            # Write the updated data back to the existing file
            with open(output_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
            print(f"Updated existing JSON file: {output_path}")
        else:
            # Normal JSON output for other iterations
            with open(output_path, 'w') as f:
                json.dump(output_list, f, indent=2)
            print(f"JSON output: {output_path}")
        
        with open(csv_output_path, 'w', newline='') as f:
            fieldnames = ['Image', 'Task 3 (Damage)', 'Task 5 (Vehicle)', 'Task 6 (Visibility)', 'Task 7 (Time)', 'Task 8 (Multiple)', 'Overall Result']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        print(f"CSV output: {csv_output_path}")
        
        print(f"\nCompleted iteration: {iteration_name}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
