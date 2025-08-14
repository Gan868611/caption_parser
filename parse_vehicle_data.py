#!/usr/bin/env python3
import json
import re

def parse_prompt_output(file_path):
    """Parse the prompt output file and extract vehicle data with captions"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content by image entries (lines ending with .png: or .jpg:)
    image_entries = re.split(r'\n(?=kaggle/[^:]+\.(?:png|jpg):)', content.strip())
    
    results = []
    
    for entry in image_entries:
        if not entry.strip():
            continue
            
        lines = entry.strip().split('\n')
        if not lines:
            continue
            
        # Extract image name from first line
        first_line = lines[0]
        if ':' in first_line:
            image_name = first_line.split(':')[0].strip()
        else:
            continue
            
        # Find Task 5 section
        task5_found = False
        vehicle_yes = False
        
        for i, line in enumerate(lines):
            if line.strip() == "Task 5":
                task5_found = True
                # Check next few lines for "Vehicle: Yes"
                for j in range(i+1, min(i+10, len(lines))):
                    if lines[j].strip().startswith("Vehicle:"):
                        if "Yes" in lines[j]:
                            vehicle_yes = True
                        break
                break
        
        # Only process entries with Vehicle: Yes
        if not (task5_found and vehicle_yes):
            continue
            
        # Extract Task 4 captions (damage descriptions)
        captions = []
        task4_found = False
        
        for i, line in enumerate(lines):
            if line.strip() == "Task 4":
                task4_found = True
                # Collect lines until next task or end
                for j in range(i+1, len(lines)):
                    caption_line = lines[j].strip()
                    if caption_line.startswith("Task ") or not caption_line:
                        if caption_line.startswith("Task "):
                            break
                        elif not caption_line:
                            continue
                    elif caption_line != "NA":
                        captions.append(caption_line)
                break
        
        # If no Task 4 captions, try to extract from Task 2
        if not captions:
            task2_found = False
            for i, line in enumerate(lines):
                if line.strip() == "Task 2":
                    task2_found = True
                    # Collect lines until next task
                    for j in range(i+1, len(lines)):
                        caption_line = lines[j].strip()
                        if caption_line.startswith("Task ") or not caption_line:
                            if caption_line.startswith("Task "):
                                break
                            elif not caption_line:
                                continue
                        else:
                            # Extract descriptive text from Task 2 format
                            if caption_line.startswith('[') and ']' in caption_line:
                                desc_part = caption_line.split(']', -1)[-1].strip()
                                if desc_part and len(desc_part) > 10:  # Only meaningful descriptions
                                    captions.append(desc_part)
                    break
        
        # If still no captions, try Task 1
        if not captions:
            for i, line in enumerate(lines):
                if line.strip() == "Task 1":
                    # Collect lines until next task
                    for j in range(i+1, len(lines)):
                        caption_line = lines[j].strip()
                        if caption_line.startswith("Task ") or not caption_line:
                            if caption_line.startswith("Task "):
                                break
                            elif not caption_line:
                                continue
                        else:
                            # Extract descriptive text from Task 1 format
                            if caption_line.startswith('[') and ']' in caption_line:
                                desc_part = caption_line.split(']', 1)[-1].strip()
                                if desc_part and len(desc_part) > 5:  # Only meaningful descriptions
                                    captions.append(desc_part)
                    break
        
        # Ensure we have some captions
        if not captions:
            captions = ["Vehicle image with damage assessment data available."]
        
        # Limit to 5 captions maximum to match the example format
        captions = captions[:5]
        
        results.append({
            "image": image_name,
            "caption": captions
        })
    
    return results

def main():
    input_file = "/home/cynapse/zhenyang/caption_parser/example_prompt_output"
    output_file = "/home/cynapse/zhenyang/caption_parser/parsed_vehicle_annotations.json"
    
    print("Parsing vehicle data from prompt output...")
    vehicle_data = parse_prompt_output(input_file)
    
    print(f"Found {len(vehicle_data)} vehicle entries with 'Vehicle: Yes'")
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(vehicle_data, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {output_file}")
    
    # Show first few entries as preview
    print("\nFirst 3 entries preview:")
    for i, entry in enumerate(vehicle_data[:3]):
        print(f"\nEntry {i+1}:")
        print(f"Image: {entry['image']}")
        print(f"Captions: {len(entry['caption'])} items")
        for j, caption in enumerate(entry['caption'][:2]):  # Show first 2 captions
            print(f"  {j+1}: {caption}")

if __name__ == "__main__":
    main()
