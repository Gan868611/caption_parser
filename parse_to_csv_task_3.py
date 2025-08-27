#!/usr/bin/env python3
"""Parse caption data with Task 3 filtering and CSV output with caption combining logic"""

import re
import csv
import os
import random

# === CONFIGURATION ===
INPUT_FILES = {
    'gemini': "/home/cynapse/terence/database/blip/results/usroad_filelist_temp0_topk1_topp1_readable.txt",
    'openai': "/home/cynapse/terence/database/blip/results_openai/usroad_filelist_damage_temp0_topk1_topp1_readable.txt"
}

ITERATION_CONFIG = [
    ('gemini_non_damage', 'gemini'),
    ('openai_non_damage', 'openai'),
    ('gemini_and_openai_damage(openai)', 'openai'),
    ('gemini_and_openai_damage(gemini)', 'gemini')
]

OUTPUT_SUFFIX = "blip_caption_idca_csv"

DAMAGE_FILTERS = {
    'gemini_non_damage': ['None'],
    'openai_non_damage': ['None'],
    'gemini_and_openai_damage(openai)': ['Moderate', 'Severe', 'Minor'],
    'gemini_and_openai_damage(gemini)': ['Moderate', 'Severe', 'Minor'],
}

CSV_OUTDIR = '/home/cynapse/zhenyang/caption_parser/output_csv/'
VISIBILITY_THRESHOLD = 45
MAX_WORDS = 30
COMBINE_CAPTIONS = True
TRAIN_RATIO = 0.8
VAL_RATIO = 0.2

# Special split ratios for gemini_and_openai_damage iterations
DAMAGE_TRAIN_RATIO = 0.5
DAMAGE_VAL_RATIO = 0.2

# === COMBINATION OPTIONS ===
OUTPUT_INDIVIDUAL_CSV = True  # Set to False to skip individual train/val/test files
OUTPUT_COMBINED_CSV = True    # Set to True to create combined CSV files
COMBINE_ALL_ITERATIONS = True # Set to True to combine all iterations into single files

# === CSV FORMAT OPTIONS ===
CSV_IMG_KEY = 'image_path'
CSV_CAPTION_KEY = 'caption'
CSV_SEPARATOR = ','

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

def prepare_csv_data(data_split):
    """Prepare CSV data for a given data split"""
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

def main():
    print("=== TAG FILTERING CONFIGURATION ===")
    for tag, include in INCLUDE_TAGS.items():
        status = "✅ KEEP content" if include else "❌ REMOVE content"
        print(f"  {tag}: {status}")
    print(f"\nINCLUDE_ALL_TAGS: {INCLUDE_ALL_TAGS}")
    print("="*50)
    
    print("\n=== OUTPUT CONFIGURATION ===")
    print(f"Output individual CSV files: {OUTPUT_INDIVIDUAL_CSV}")
    print(f"Output combined CSV files: {OUTPUT_COMBINED_CSV}")
    print(f"Combine all iterations: {COMBINE_ALL_ITERATIONS}")
    print("="*50 + "\n")

    gemini_and_openai_damage_list = set()
    openai_damage_data = {}  # Store openai damage data for combination
    
    # Storage for combining all iterations
    all_combined_data = {
        'train': [],
        'test': [],
        'val': []
    }
    
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
        
        filtered_results = []
        
        print("=== FILTERING BY TASK 5, 6, 7, AND 8 ===")

        for entry_dict in all_results:
            task5_pass = check_task5_vehicle_yes(entry_dict)
            task6_pass = check_task6_visibility_N_plus(entry_dict)
            task7_pass = check_task7_visibility_day(entry_dict)
            task8_pass = check_task8_multiple_no(entry_dict)
            task3_pass = filter_task_3(entry_dict, current_damage_filter)
            
            overall_pass = all([task5_pass, task6_pass, task7_pass, task8_pass, task3_pass])

            if iteration_name == 'gemini_and_openai_damage(gemini)' and input_file_key == 'gemini':
                if entry_dict['image'] not in gemini_and_openai_damage_list:
                    overall_pass = False
            
            if overall_pass:
                if iteration_name == 'gemini_and_openai_damage(openai)' and input_file_key == 'openai':
                    gemini_and_openai_damage_list.add(entry_dict['image'])
                filtered_results.append(entry_dict)
        
        print(f"=== SUMMARY FOR {iteration_name.upper()} ===")
        print(f"Total entries: {len(all_results)} | Passing: {len(filtered_results)}")
        
        # Handle special case for gemini_and_openai_damage combination
        if iteration_name == 'gemini_and_openai_damage(openai)' and input_file_key == 'openai':
            # Store openai damage data for later combination with gemini
            openai_damage_data = {
                'filtered_results': filtered_results,
                'input_base': INPUT_FILES[input_file_key].split('/')[-1].split('.')[0],
                'iteration_name': iteration_name
            }
            print(f"\nStored OpenAI damage data for combination with Gemini data")
            print(f"Completed iteration: {iteration_name}")
            print(f"{'='*60}\n")
            continue
        
        elif iteration_name == 'gemini_and_openai_damage(gemini)' and input_file_key == 'gemini':
            # Combine gemini data with stored openai data
            if openai_damage_data:
                print("\n=== COMBINING GEMINI AND OPENAI DAMAGE DATA ===")
                
                # Create a mapping of openai images to their data
                openai_image_map = {item['image']: item for item in openai_damage_data['filtered_results']}
                
                # Combine captions for matching images
                combined_results = []
                for gemini_item in filtered_results:
                    image_name = gemini_item['image']
                    if image_name in openai_image_map:
                        # Combine captions from both sources
                        combined_item = gemini_item.copy()
                        
                        # Combine Task 1 captions
                        if 'Task 1' in gemini_item and 'Task 1' in openai_image_map[image_name]:
                            combined_captions = gemini_item['Task 1'] + openai_image_map[image_name]['Task 1']
                            combined_item['Task 1'] = combined_captions
                        
                        combined_results.append(combined_item)
                
                print(f"Combined {len(combined_results)} matching images from Gemini and OpenAI")
                filtered_results = combined_results
                
                # Use combined naming for output
                input_base = f"combined_{openai_damage_data['input_base']}_gemini"
                output_suffix = f"{OUTPUT_SUFFIX}_combined_damage"
            else:
                print("⚠️ No OpenAI damage data found for combination")
                input_base = INPUT_FILES[input_file_key].split('/')[-1].split('.')[0]
                output_suffix = f"{OUTPUT_SUFFIX}_{iteration_name}"
        else:
            # Normal processing for other iterations
            input_base = INPUT_FILES[input_file_key].split('/')[-1].split('.')[0]
            output_suffix = f"{OUTPUT_SUFFIX}_{iteration_name}"
        
        # Determine split ratios based on iteration type
        if 'gemini_and_openai_damage' in iteration_name:
            current_train_ratio = DAMAGE_TRAIN_RATIO
            current_val_ratio = DAMAGE_VAL_RATIO
            print(f"Using damage-specific split ratios: Train={current_train_ratio}, Val={current_val_ratio}")
        else:
            current_train_ratio = TRAIN_RATIO
            current_val_ratio = VAL_RATIO
            print(f"Using standard split ratios: Train={current_train_ratio}, Val={current_val_ratio}")
        
        # Split data into train, test, val
        train_data, test_data, val_data = split_data(filtered_results, current_train_ratio, current_val_ratio)
        
        # Generate CSV data for each split
        train_csv = prepare_csv_data(train_data)
        test_csv = prepare_csv_data(test_data)
        val_csv = prepare_csv_data(val_data)
        
        os.makedirs(CSV_OUTDIR, exist_ok=True)
        
        # Prepare split data
        splits = [
            ('train', train_csv),
            ('test', test_csv),
            ('val', val_csv)
        ]
        
        # Add data to combined storage if combining all iterations
        if COMBINE_ALL_ITERATIONS:
            all_combined_data['train'].extend(train_csv)
            all_combined_data['test'].extend(test_csv)
            all_combined_data['val'].extend(val_csv)
        
        # Write individual CSV files if enabled
        if OUTPUT_INDIVIDUAL_CSV:
            for split_name, csv_data in splits:
                csv_output_path = os.path.join(CSV_OUTDIR, f"{input_base}_{output_suffix}_{split_name}.csv")
                
                with open(csv_output_path, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = [CSV_IMG_KEY, CSV_CAPTION_KEY]
                    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=CSV_SEPARATOR)
                    writer.writeheader()
                    writer.writerows(csv_data)
                
                print(f"{split_name.upper()} CSV: {csv_output_path} ({len(csv_data)} entries)")
        
        # Write combined CSV file for this iteration if enabled
        if OUTPUT_COMBINED_CSV:
            combined_csv_data = train_csv + test_csv + val_csv
            combined_output_path = os.path.join(CSV_OUTDIR, f"{input_base}_{output_suffix}_combined.csv")
            
            with open(combined_output_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [CSV_IMG_KEY, CSV_CAPTION_KEY]
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=CSV_SEPARATOR)
                writer.writeheader()
                writer.writerows(combined_csv_data)
            
            print(f"COMBINED CSV: {combined_output_path} ({len(combined_csv_data)} entries)")
        
        # Print split statistics
        print(f"\n=== SPLIT STATISTICS FOR {iteration_name.upper()} ===")
        print(f"Train: {len(train_data)} images ({len(train_csv)} caption entries)")
        print(f"Test: {len(test_data)} images ({len(test_csv)} caption entries)")
        print(f"Val: {len(val_data)} images ({len(val_csv)} caption entries)")
        
        train_pct = len(train_data) / len(filtered_results) * 100 if filtered_results else 0
        test_pct = len(test_data) / len(filtered_results) * 100 if filtered_results else 0
        val_pct = len(val_data) / len(filtered_results) * 100 if filtered_results else 0
        print(f"Actual percentages - Train: {train_pct:.1f}%, Test: {test_pct:.1f}%, Val: {val_pct:.1f}%")
        
        if 'gemini_and_openai_damage' in iteration_name:
            print(f"Target ratios were - Train: {current_train_ratio*100:.1f}%, Test: {(1-current_train_ratio-current_val_ratio)*100:.1f}%, Val: {current_val_ratio*100:.1f}%")
        
        print(f"\nCompleted iteration: {iteration_name}")
        print(f"{'='*60}\n")
    
    # Write combined files across all iterations if enabled
    if COMBINE_ALL_ITERATIONS and (OUTPUT_INDIVIDUAL_CSV or OUTPUT_COMBINED_CSV):
        print(f"{'='*60}")
        print("WRITING COMBINED FILES ACROSS ALL ITERATIONS")
        print(f"{'='*60}\n")
        
        # Write individual split files combining all iterations
        if OUTPUT_INDIVIDUAL_CSV:
            for split_name in ['train', 'test', 'val']:
                all_iterations_path = os.path.join(CSV_OUTDIR, f"all_iterations_{OUTPUT_SUFFIX}_{split_name}.csv")
                split_data = all_combined_data[split_name]
                
                with open(all_iterations_path, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = [CSV_IMG_KEY, CSV_CAPTION_KEY]
                    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=CSV_SEPARATOR)
                    writer.writeheader()
                    writer.writerows(split_data)
                
                print(f"ALL ITERATIONS {split_name.upper()}: {all_iterations_path} ({len(split_data)} entries)")
        
        # Write single combined file with all iterations and all splits
        if OUTPUT_COMBINED_CSV:
            all_data = all_combined_data['train'] + all_combined_data['test'] + all_combined_data['val']
            all_combined_path = os.path.join(CSV_OUTDIR, f"all_iterations_{OUTPUT_SUFFIX}_all_combined.csv")
            
            with open(all_combined_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [CSV_IMG_KEY, CSV_CAPTION_KEY]
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=CSV_SEPARATOR)
                writer.writeheader()
                writer.writerows(all_data)
            
            print(f"ALL ITERATIONS COMBINED: {all_combined_path} ({len(all_data)} entries)")
        
        # Print final statistics
        print(f"\n=== FINAL COMBINED STATISTICS ===")
        print(f"Train: {len(all_combined_data['train'])} caption entries")
        print(f"Test: {len(all_combined_data['test'])} caption entries") 
        print(f"Val: {len(all_combined_data['val'])} caption entries")
        print(f"Total: {len(all_combined_data['train']) + len(all_combined_data['test']) + len(all_combined_data['val'])} caption entries")

if __name__ == "__main__":
    main()