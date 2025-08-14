#!/usr/bin/env python3
import json
import re

def parse_vehicle_data(filename):
    results = []
    
    with open(filename, 'r') as file:
        content = file.read()
    
    # Split by image entries (lines ending with .png: or .jpg:)
    entries = re.split(r'\n(?=\S+\.(?:png|jpg):)', content)
    
    for entry in entries:
        if not entry.strip():
            continue
            
        lines = entry.strip().split('\n')
        if not lines:
            continue
            
        # Extract image filename
        first_line = lines[0]
        if ':' not in first_line:
            continue
            
        image_path = first_line.split(':')[0].strip()
        
        # Parse tasks
        tasks = {}
        current_task = None
        current_content = []
        
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('Task '):
                # Save previous task
                if current_task:
                    tasks[current_task] = current_content
                # Start new task
                current_task = line
                current_content = []
            elif line:
                current_content.append(line)
        
        # Save last task
        if current_task:
            tasks[current_task] = current_content
        
        # Apply filters
        # 1. Task 8 need to be "no"
        task8_content = ' '.join(tasks.get('Task 8', []))
        if 'Multiple = no' not in task8_content:
            continue
            
        # 2. Task 7 needs to be "day"
        task7_content = ' '.join(tasks.get('Task 7', []))
        if 'Visibility = day' not in task7_content:
            continue
            
        # 3. Task 6 needs to be >=45
        task6_content = ' '.join(tasks.get('Task 6', []))
        visibility_match = re.search(r'Visibility = (\d+)', task6_content)
        if not visibility_match or int(visibility_match.group(1)) < 45:
            continue
            
        # 4. Task 5 vehicle needs to be "yes"
        task5_content = ' '.join(tasks.get('Task 5', []))
        if 'Vehicle: Yes' not in task5_content:
            continue
        
        # Build captions list
        captions = []
        
        # 5. Append all lines in Task 1 with [] removed
        task1_lines = tasks.get('Task 1', [])
        for line in task1_lines:
            # Remove [] tags
            cleaned_line = re.sub(r'\[.*?\]\s*', '', line).strip()
            if cleaned_line:
                captions.append(cleaned_line)
        
        # 6. Append all lines in Task 2 with [] removed
        task2_lines = tasks.get('Task 2', [])
        for line in task2_lines:
            # Remove [] tags
            cleaned_line = re.sub(r'\[.*?\]\s*', '', line).strip()
            if cleaned_line:
                captions.append(cleaned_line)
        
        # 7. Append Task 3 damage level with proper format
        task3_content = ' '.join(tasks.get('Task 3', []))
        damage_match = re.search(r'Damage = (\w+)', task3_content)
        if damage_match:
            damage_level = damage_match.group(1).lower()
            if damage_level == 'none':
                captions.append("There is no damage in the vehicle")
            else:
                captions.append(f"There is {damage_level} damage in the vehicle")
        
        # 8. Append all lines in Task 4 if not NA
        task4_lines = tasks.get('Task 4', [])
        for line in task4_lines:
            if line.strip() and line.strip() != 'NA':
                captions.append(line.strip())
        
        # Add to results
        if captions:  # Only add if we have captions
            results.append({
                "image": image_path,
                "caption": captions
            })
    
    return results

def main():
    input_file = 'example_prompt_output_short'
    output_file = 'filtered_vehicle_data.json'
    
    print(f"Parsing {input_file}...")
    results = parse_vehicle_data(input_file)
    
    print(f"Found {len(results)} entries that match all criteria")
    
    # Write to JSON file
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {output_file}")
    
    # Print first entry as example
    if results:
        print("\nFirst entry example:")
        print(json.dumps(results[0], indent=2))

if __name__ == "__main__":
    main()
