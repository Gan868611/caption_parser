#!/usr/bin/env python3

import json
import re
import csv
import os

# === CONFIGURATION ===
INPUT_FILE = '/home/cynapse/zhenyang/caption_parser/caption_input_txt/example_prompt_output_long'  # Change to your input file
OUTPUT_DIR = './output_json'  # Change to your desired output directory
VISIBILITY_THRESHOLD = 45

def parse_to_dict(filename):
    results = []
    
    with open(filename, 'r') as file:
        content = file.read()
    
    # Split by empty lines to separate different entries
    entries = content.strip().split('\n\n')
    
    for entry_idx, entry in enumerate(entries, 1):
        if not entry.strip():
            continue
            
        lines = entry.strip().split('\n')
        if not lines:
            continue
            
        # Extract image filename from first line
        first_line = lines[0]
        if ':' not in first_line or not (first_line.endswith('.png:') or first_line.endswith('.jpg:')):
            continue
            
        image_path = first_line.split(':')[0].strip()
        
        # Create entry dictionary
        entry_dict = {
            "image": image_path
        }
        
        # Parse tasks
        current_task = None
        current_content = []
        
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('Task '):
                # Save previous task
                if current_task:
                    entry_dict[current_task] = current_content
                # Start new task
                current_task = line
                current_content = []
            elif line:
                # Remove [xxx] tags from the line
                cleaned_line = re.sub(r'\[.*?\]\s*', '', line).strip()
                current_content.append(cleaned_line)
        
        # Save last task
        if current_task:
            entry_dict[current_task] = current_content
        
        results.append(entry_dict)
        
        # Print the dictionary for this entry
        # print(f"\n=== Entry {entry_idx}: {image_path} ===")
        # print(json.dumps(entry_dict, indent=2))
    
    return results

def check_task5_vehicle_yes(entry_dict):
    """
    Check if Task 5 contains 'Vehicle: Yes'
    Returns True if valid, False if should be ignored
    """
    if 'Task 5' not in entry_dict:
        return False
    
    task5_content = entry_dict['Task 5']
    for line in task5_content:
        if line.strip() == 'Vehicle: Yes':
            return True
    
    return False

def check_task6_visibility_N_plus(entry_dict):
    """
    Check if Task 6 contains 'Visibility = X' where X >= 45
    Returns True if valid, False if should be ignored
    """
    if 'Task 6' not in entry_dict:
        return False
    
    task6_content = entry_dict['Task 6']
    for line in task6_content:
        line_stripped = line.strip()
        if line_stripped.startswith("Visibility = "):
            try:
                visibility_value = int(line_stripped.split("= ")[1])
                if visibility_value >= VISIBILITY_THRESHOLD:
                    return True
            except (ValueError, IndexError):
                continue
    
    return False

def check_task7_visibility_day(entry_dict):
    """
    Check if Task 7 contains 'Time = day'
    Returns True if valid, False if should be ignored
    """
    if 'Task 7' not in entry_dict:
        return False
    
    task7_content = entry_dict['Task 7']
    for line in task7_content:
        if line.strip() == 'Time = day':
            return True
    
    return False

def check_task8_multiple_no(entry_dict):
    """
    Check if Task 8 contains 'Multiple = no'
    Returns True if valid, False if should be ignored
    """
    if 'Task 8' not in entry_dict:
        return False
    
    task8_content = entry_dict['Task 8']
    for line in task8_content:
        if line.strip() == 'Multiple = no':
            return True
    
    return False

def main():
    input_file = INPUT_FILE
    
    print(f"Parsing {input_file} using space separation...")
    all_results = parse_to_dict(input_file)
    
    # Initialize CSV data list
    csv_data = []
    
    print(f"\n\n=== FILTERING BY TASK 5, 6, 7, AND 8 ===")
    
    # Filter entries based on Task 5, 6, 7, and 8 checks
    filtered_results = []
    for i, entry_dict in enumerate(all_results, 1):
        task5_pass = check_task5_vehicle_yes(entry_dict)
        task6_pass = check_task6_visibility_N_plus(entry_dict)
        task7_pass = check_task7_visibility_day(entry_dict)
        task8_pass = check_task8_multiple_no(entry_dict)
        
        # Print console output
        print(f"Entry {i}: {entry_dict['image']}")
        print(f"  Task 5 (Vehicle: Yes): {'✅ PASS' if task5_pass else '❌ FAIL'}")
        print(f"  Task 6 (Visibility >= {VISIBILITY_THRESHOLD}): {'✅ PASS' if task6_pass else '❌ FAIL'}")
        print(f"  Task 7 (Time = day): {'✅ PASS' if task7_pass else '❌ FAIL'}")
        print(f"  Task 8 (Multiple = no): {'✅ PASS' if task8_pass else '❌ FAIL'}")
        
        # Determine overall result
        overall_pass = task5_pass and task6_pass and task7_pass and task8_pass
   
        if overall_pass:
            filtered_results.append(entry_dict)
            print(f"  🎉 OVERALL: PASSED - Entry included")
        else:
            print(f"  ❌ OVERALL: FAILED - Entry ignored")
        print()
    
    print(f"\n=== SUMMARY ===")
    print(f"Total entries parsed: {len(all_results)}")
    print(f"Entries passing all filters: {len(filtered_results)}")

    # Set output directory as a variable
    output_dir = OUTPUT_DIR  # Change this to your desired output directory

    # Build output filename
    input_base = input_file.split('/')[-1].split('.')[0]
    output_filename = f"{input_base}_task_5.json"
    output_path = f"{output_dir}/{output_filename}"

    # Build output 
    output_list = []
    for entry in filtered_results:
        entry_data = {
            'image': entry['image']
        }
        # Add Task 5
        if 'Task 5' in entry:
            for info in entry['Task 5']:
                # Split by : and handle potential whitespace
                parts = [part.strip() for part in info.split(':')]
                if len(parts) == 2:  # Only process if we have both key and value
                    key = parts[0]
                    value = parts[1]
                    entry_data[key] = value
        
        output_list.append(entry_data)

    # Write to JSON file
    with open(output_path, 'w') as f:
        json.dump(output_list, f, indent=2)
    print(f"\nOutput written to {output_path}")

    return filtered_results

if __name__ == "__main__":
    main()
