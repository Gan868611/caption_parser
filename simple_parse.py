#!/usr/bin/env python3
import json
import re
import os
import sys

def parse_simple_data(filename):
    results = []
    
    with open(filename, 'r') as file:
        content = file.read()
    
    # Split by empty lines to separate different images
    entries = content.strip().split('\n\n')
    
    for entry in entries:
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
        print(f"Processing: {image_path}")
        
        # Check if Task 8 contains "Multiple = no" - if not, skip this entry
        has_multiple_no = False
        for line in lines:
            if line.strip() == "Multiple = no":
                has_multiple_no = True
                break
        
        print(f"  Task 8 (Multiple = no): {has_multiple_no}")
        if not has_multiple_no:
            continue
        
        # Check if Task 7 contains "Visibility = day" - if not, skip this entry
        has_visibility_day = False
        for line in lines:
            if line.strip() == "Visibility = day":
                has_visibility_day = True
                break
        
        print(f"  Task 7 (Visibility = day): {has_visibility_day}")
        if not has_visibility_day:
            continue
        
        # Check if Task 6 contains "Visibility = X" where X >= 45 - if not, skip this entry
        has_visibility_45_plus = False
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("Visibility = ") and line_stripped != "Visibility = day":
                try:
                    visibility_value = int(line_stripped.split("= ")[1])
                    if visibility_value >= 45:
                        has_visibility_45_plus = True
                        break
                except (ValueError, IndexError):
                    continue
        
        print(f"  Task 6 (Visibility >= 45): {has_visibility_45_plus}")
        if not has_visibility_45_plus:
            continue
        
        # Check if Task 5 contains "Vehicle: Yes" - if not, skip this entry
        has_vehicle_yes = False
        for line in lines:
            if line.strip() == "Vehicle: Yes":
                has_vehicle_yes = True
                break
        
        print(f"  Task 5 (Vehicle: Yes): {has_vehicle_yes}")
        if not has_vehicle_yes:
            continue
        
        # Check if Task 3 contains "Damage = None" - if so, we'll skip Task 4 lines later
        has_damage_none = False
        damage_level = None
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("Damage = "):
                damage_value = line_stripped.split("= ")[1]
                if damage_value == "None":
                    has_damage_none = True
                else:
                    damage_level = damage_value.lower()
                break
        
        print(f"  Task 3 (Damage = None): {has_damage_none}")
        
        print(f"  ✅ Entry passes all filters")
        
        # Collect all content lines, ignoring "Task X" headers
        captions = []
        in_task_4 = False
        in_task_5_or_later = False
        
        for line in lines[1:]:
            line = line.strip()
            
            # Track if we're in Task 4 or Task 5+ (5, 6, 7, 8)
            if line == "Task 4":
                in_task_4 = True
                in_task_5_or_later = False
                continue
            elif line in ["Task 5", "Task 6", "Task 7", "Task 8"]:
                in_task_4 = False
                in_task_5_or_later = True
                continue
            elif line.startswith("Task "):
                in_task_4 = False
                in_task_5_or_later = False
                continue
            
            # Skip empty lines and "Task X" headers
            if line:
                # If we're in Task 4 and damage is None, skip these lines
                if in_task_4 and has_damage_none:
                    continue
                
                # If we're in Task 5, 6, 7, or 8, skip these lines
                if in_task_5_or_later:
                    continue
                    
                # Remove [xxx] tags from the line
                cleaned_line = re.sub(r'\[.*?\]\s*', '', line).strip()
                
                # Transform "Damage = xxx" into "There is xxx damage on the vehicle"
                if cleaned_line.startswith("Damage = ") and damage_level:
                    cleaned_line = f"There is {damage_level} damage on the vehicle"
                elif cleaned_line.startswith("Damage = ") and has_damage_none:
                    continue  # Skip "Damage = None" lines entirely
                
                if cleaned_line:  # Only add non-empty lines after cleaning
                    captions.append(cleaned_line)
        
        # Add to results if we have captions
        if captions:
            results.append({
                "image": image_path,
                "caption": captions
            })
    
    return results

def main():
    # User-configurable settings
    input_file = '/home/cynapse/terence/database/results_readable/youtube_filelist_t15_p90_k0_readable.txt'  # Change this to your input file
    output_dir = './'  # Change this to your desired output directory
    
    # Generate output filename based on input file
    input_basename = os.path.splitext(os.path.basename(input_file))[0]
    output_filename = f"{input_basename}_annotation.json"
    output_file = os.path.join(output_dir, output_filename)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Parsing {input_file}...")
    results = parse_simple_data(input_file)
    
    print(f"Found {len(results)} entries")
    
    # Debug: print which entries were found
    for i, result in enumerate(results, 1):
        print(f"Entry {i}: {result['image']} - Captions: {len(result['caption'])}")
    
    # Write to JSON file
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {output_file}")
    
    # Print summary
    for i, result in enumerate(results, 1):
        print(f"\nEntry {i}: {result['image']}")
        print(f"  Captions: {len(result['caption'])}")

if __name__ == "__main__":
    main()
