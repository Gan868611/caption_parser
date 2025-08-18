#!/usr/bin/env python3

import json
import re
import csv
import os

# === CONFIGURATION ===
INPUT_FILE = "/home/cynapse/terence/database/blip/results/usroad_filelist_temp0_topk1_topp1_readable.txt"  # Change to your input file
OUTPUT_DIR = '/home/cynapse/terence/database/blip/results/blip_caption/'  # Change to your desired output directory
CSV_OUTDIR = '/home/cynapse/terence/database/blip/results/blip_caption/csv_check/'  # Change to your desired CSV output directory
VISIBILITY_THRESHOLD = 45
OUTPUT_SUFFIX = 'blip_caption_damage_gemini_and_openai_(gemini)'  # Suffix for output JSON files



def parse_to_json(filename):
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

def filter_task_3(entry_dict):
    """
    Filter Task 3 to only include entries with 'Damage = Minor', 'Damage = Moderate', or 'Damage = Severe'
    Returns True if valid, False if should be ignored
    """
    if 'Task 3' not in entry_dict:
        return False
    
    task3_content = entry_dict['Task 3']
    for line in task3_content:
        if line.startswith('Damage = '):
            damage_value = line.split('Damage = ')[1].strip()
            # if any(x.lower() in damage_value.lower() for x in ['None']):
            if any(x.lower() in damage_value.lower() for x in ['Moderate', 'Severe', 'Minor']):
                return True
    
    return False

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
    all_results = parse_to_json(input_file)
    
    # Initialize CSV data list
    csv_data = []
    
    print(f"\n\n=== FILTERING BY TASK 5, 6, 7, AND 8 ===")

    with open('/home/cynapse/zhenyang/caption_parser/gemini_and_openai_damage_list.txt', "r") as f:
        content = f.read()
    
    # Filter entries based on Task 5, 6, 7, and 8 checks
    filtered_results = []
    for i, entry_dict in enumerate(all_results, 1):
        task5_pass = check_task5_vehicle_yes(entry_dict)
        task6_pass = check_task6_visibility_N_plus(entry_dict)
        task7_pass = check_task7_visibility_day(entry_dict)
        task8_pass = check_task8_multiple_no(entry_dict)
        task3_pass = filter_task_3(entry_dict)





        
        

        # Print console output
        print(f"Entry {i}: {entry_dict['image']}")
        print(f"  Task 5 (Vehicle: Yes): {'✅ PASS' if task5_pass else '❌ FAIL'}")
        print(f"  Task 6 (Visibility >= {VISIBILITY_THRESHOLD}): {'✅ PASS' if task6_pass else '❌ FAIL'}")
        print(f"  Task 7 (Time = day): {'✅ PASS' if task7_pass else '❌ FAIL'}")
        print(f"  Task 8 (Multiple = no): {'✅ PASS' if task8_pass else '❌ FAIL'}")
        
        # Determine overall result
        overall_pass = task5_pass and task6_pass and task7_pass and task8_pass and task3_pass

        if entry_dict['image'] not in content:
            overall_pass = False
            print(f"  🎉 OVERALL: PASSED - Entry included")
        
        # Get damage level from Task 3
        damage_level = 'N/A'
        vehicle_type = 'N/A'
        if 'Task 3' in entry_dict:
            for line in entry_dict['Task 3']:
                if line.startswith('Damage = '):
                    damage_level = line.split('Damage = ')[1].strip()
                elif line.startswith('Type:'):
                    vehicle_type = line.split(':')[1].strip()

        # Add to CSV data
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
            # with open("gemini_and_openai_damage.txt", "a") as f:
            #     f.write(str(entry_dict['image']) + "\n")
            filtered_results.append(entry_dict)
            print(f"  🎉 OVERALL: PASSED - Entry included")
        else:
            print(f"  ❌ OVERALL: FAILED - Entry ignored")
        print()
    
    print(f"\n=== SUMMARY ===")
    print(f"Total entries parsed: {len(all_results)}")
    print(f"Entries passing all filters: {len(filtered_results)}")
    
    print(f"\n=== FILTERED RESULTS ===")
    for i, result in enumerate(filtered_results, 1):
        task_count = len([k for k in result.keys() if k.startswith('Task')])
        print(f"Entry {i}: {result['image']} - {task_count} tasks")

    # Set output directory as a variable
    output_dir = OUTPUT_DIR  # Change this to your desired output directory

    # Build output filename
    input_base = input_file.split('/')[-1].split('.')[0]
    output_filename = f"{input_base}_{OUTPUT_SUFFIX}.json"
    output_path = f"{output_dir}/{output_filename}"

    # Build output list
    output_list = []
    for entry in filtered_results:
        captions = []
        # Add Task 1 only and ignore Task 2 first
        # for task in ['Task 1', 'Task 2']:
        for task in ['Task 1']:
            if task in entry:
                captions.extend(entry[task])

        # Check Task 3 for damage
        damage_level = None
        if 'Task 3' in entry:
            for line in entry['Task 3']:
                if line.startswith('Damage = '):
                    value = line.split('Damage = ')[1].strip()
                    if 'Minor' in value:
                        damage_level = 'Minor'
                        break
                    elif 'Moderate' in value:
                        damage_level = 'Moderate'
                        break
                    elif 'Severe' in value:
                        damage_level = 'Severe'
                        break
        # If damage is present, append summary and Task 4 content
        if damage_level:
            # captions.append(f'There is {damage_level.lower()} damage on the vehicle')
            if 'Task 4' in entry:
                for line in entry['Task 4']:
                    if line.strip() and line.strip().upper() != 'NA':
                        captions.append(line.strip())

        output_list.append({
            'image': entry['image'],
            'caption': captions
        })

    # Write to JSON file
    with open(output_path, 'w') as f:
        json.dump(output_list, f, indent=2)
    print(f"\nOutput written to {output_path}")

    # Write CSV file
    csv_output_path = os.path.join(CSV_OUTDIR, f"{input_base}_{OUTPUT_SUFFIX}.csv")
    with open(csv_output_path, 'w', newline='') as f:
        fieldnames = ['Image', 'Task 3 (Damage)', 'Task 5 (Vehicle)', 'Task 6 (Visibility)', 
                     'Task 7 (Time)', 'Task 8 (Multiple)', 'Overall Result']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    print(f"Task check results written to {csv_output_path}")

    return filtered_results

if __name__ == "__main__":
    main()
