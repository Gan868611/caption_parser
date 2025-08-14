#!/usr/bin/env python3

import re
from parse_to_dict import parse_to_dict

# === CONFIGURATION ===
INPUT_FILE = '/home/cynapse/terence/database/results_readable2/usroad_filelist_t15_p90_k0_readable.txt'  # Change to your input file
OUTDIR = './'  # Change to your desired output directory (even if non exist dir)
IMAGE_BASE_DIR = '/home/cynapse/terence/database/'  # Change to your image base directory

def check_task5_vehicle_yes(entry_dict):
    if 'Task 5' not in entry_dict:
        return False
    task5_content = entry_dict['Task 5']
    for line in task5_content:
        if line.strip() == 'Vehicle: Yes':
            return True
    return False

def check_task6_visibility_45_plus(entry_dict):
    if 'Task 6' not in entry_dict:
        return False
    task6_content = entry_dict['Task 6']
    for line in task6_content:
        line_stripped = line.strip()
        if line_stripped.startswith("Visibility = "):
            try:
                visibility_value = int(line_stripped.split("= ")[1])
                if visibility_value >= 45:
                    return True
            except (ValueError, IndexError):
                continue
    return False

def check_task7_visibility_day(entry_dict):
    if 'Task 7' not in entry_dict:
        return False
    task7_content = entry_dict['Task 7']
    for line in task7_content:
        if line.strip() == 'Visibility = day':
            return True
    return False

def check_task8_multiple_no(entry_dict):
    if 'Task 8' not in entry_dict:
        return False
    task8_content = entry_dict['Task 8']
    for line in task8_content:
        if line.strip() == 'Multiple = no':
            return True
    return False

def categorize_damage(parsed_entries):
    minor_damage_list = []
    moderate_damage_list = []
    severe_damage_list = []

    for entry in parsed_entries:
        image_path = entry.get('image')
        damage_level = None
        if 'Task 3' in entry:
            for line in entry['Task 3']:
                match = re.match(r'Damage = (Minor|Moderate|Severe)', line)
                if match:
                    damage_level = match.group(1)
                    break
        if damage_level == 'Minor':
            minor_damage_list.append(image_path)
        elif damage_level == 'Moderate':
            moderate_damage_list.append(image_path)
        elif damage_level == 'Severe':
            severe_damage_list.append(image_path)

    return minor_damage_list, moderate_damage_list, severe_damage_list

def main():
    entries = parse_to_dict(INPUT_FILE)

    # Filter entries based on Task 5, 6, 7, and 8 checks
    filtered_entries = []
    for entry_dict in entries:
        task5_pass = check_task5_vehicle_yes(entry_dict)
        task6_pass = check_task6_visibility_45_plus(entry_dict)
        task7_pass = check_task7_visibility_day(entry_dict)
        task8_pass = check_task8_multiple_no(entry_dict)
        if task5_pass and task6_pass and task7_pass and task8_pass:
            filtered_entries.append(entry_dict)

    minor, moderate, severe = categorize_damage(filtered_entries)

    import subprocess
    import os

    # Create main output folder
    os.makedirs(OUTDIR, exist_ok=True)

    damage_map = {
        'Minor': minor,
        'Moderate': moderate,
        'Severe': severe
    }

    for level, images in damage_map.items():
        if not images:
            print(f'No images for {level} damage.')
            continue
        # Get the first path layer from the first image path
        first_layer = images[0].split('/')[0] if '/' in images[0] else 'unknown'
        outdir_level = os.path.join(OUTDIR, first_layer, level)
        os.makedirs(outdir_level, exist_ok=True)
        # Build a map from image path to Task 1 content
        img_to_task1 = {}
        for entry in filtered_entries:
            img = entry.get('image')
            if img in images and 'Task 1' in entry:
                img_to_task1[img] = entry['Task 1']
        src_files = [os.path.join(IMAGE_BASE_DIR, img) for img in images]
        temp_list_path = f'rsync_image_list_{level}.txt'
        with open(temp_list_path, 'w') as f:
            for src in src_files:
                f.write(src + '\n')
        rsync_cmd = [
            'rsync',
            '-av',
            '--no-relative',
            '--copy-links',
            '--files-from=' + temp_list_path,
            '/',  # root for absolute paths
            outdir_level
        ]
        print(f'Running rsync to copy {level} images...')
        print('Rsync command:', ' '.join(rsync_cmd))
        subprocess.run(rsync_cmd)
        print(f'{level} image copy complete.')

        # Write Task 1 content as .txt file next to each image
        for img in images:
            task1_lines = img_to_task1.get(img)
            if task1_lines:
                img_filename = os.path.basename(img)
                txt_path = os.path.join(outdir_level, img_filename + '.txt')
                with open(txt_path, 'w') as txtf:
                    txtf.write('\n'.join(task1_lines))

    print(f'Minor damage count: {len(minor)}')
    print(f'Moderate damage count: {len(moderate)}')
    print(f'Severe damage count: {len(severe)}')

if __name__ == "__main__":
    main()
