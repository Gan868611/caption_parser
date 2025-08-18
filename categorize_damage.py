import re

# === CONFIGURATION ===
INPUT_FILE = '/home/cynapse/terence/database/blip/results_openai/usroad_filelist_damage_temp0_topk1_topp1_readable.txt'  # Change to your input file
OUTDIR = '/home/cynapse/terence/database/blip/results_openai/image_check'  # Change to your desired output directory (even if non exist dir)
IMAGE_BASE_DIR = '/home/cynapse/terence/database/blip/'  # Change to your image base directory
VISIBILITY = 45
INCLUDE_NONE_DAMAGE = True  # Set to True to include None damage level, False to exclude itin/env python3

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
                # cleaned_line = re.sub(r'\[.*?\]\s*', '', line).strip()
                current_content.append(line)
        
        # Save last task
        if current_task:
            entry_dict[current_task] = current_content
        
        results.append(entry_dict)
        
        # Print the dictionary for this entry
        # print(f"\n=== Entry {entry_idx}: {image_path} ===")
        # print(json.dumps(entry_dict, indent=2))
    
    return results

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
                if visibility_value >= VISIBILITY:
                    return True
            except (ValueError, IndexError):
                continue
    return False

def check_task7_visibility_day(entry_dict):
    if 'Task 7' not in entry_dict:
        return False
    task7_content = entry_dict['Task 7']
    for line in task7_content:
        if line.strip() == 'Time = day':
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
    none_damage_list = []

    for entry in parsed_entries:
        image_path = entry.get('image')
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
                    elif 'None' in value and INCLUDE_NONE_DAMAGE:
                        damage_level = 'None'
                        break
        if damage_level == 'Minor':
            minor_damage_list.append(image_path)
        elif damage_level == 'Moderate':
            moderate_damage_list.append(image_path)
        elif damage_level == 'Severe':
            severe_damage_list.append(image_path)
        elif damage_level == 'None' and INCLUDE_NONE_DAMAGE:
            none_damage_list.append(image_path)

    return minor_damage_list, moderate_damage_list, severe_damage_list, none_damage_list

def main():
    import textwrap
    from PIL import Image, ImageDraw, ImageFont
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

    # print(filtered_entries)

    minor, moderate, severe, none = categorize_damage(filtered_entries)

    import subprocess
    import os

    # Create main output folder
    os.makedirs(OUTDIR, exist_ok=True)

    damage_map = {
        'Minor': minor,
        'Moderate': moderate,
        'Severe': severe,
    }
    if INCLUDE_NONE_DAMAGE:
        damage_map['None'] = none

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
        relative_filepath = [img for img in images]
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

        # Write the list of relative image paths for this damage level
        relative_filelist_path = os.path.join(OUTDIR, first_layer, f'{first_layer}_filelist_damage.txt')
        print(f'Writing relative image file list to {relative_filelist_path}')
        with open(relative_filelist_path, 'a') as f:
            for img in images:
                f.write(img + '\n')

        # Write Task 1 content as .txt file next to each image
        # try:
        from tqdm import tqdm
        # except Exception:
        #     # If tqdm is not installed, provide a no-op fallback so the loop still runs
        #     def tqdm(iterable, **kwargs):
        #         return iterable

        for img in tqdm(images, desc=f"Processing {level} images"):
            task1_lines = img_to_task1.get(img)
            if not task1_lines:
                continue
            img_filename = os.path.basename(img)
            img_name, img_ext = os.path.splitext(img_filename)
            original_img_path = os.path.join(outdir_level, img_filename)
            caption_img_path = os.path.join(outdir_level, f"{img_name}_caption{img_ext}")
            try:
                image = Image.open(original_img_path)
            except Exception as e:
                print(f'Error opening image {original_img_path}: {e}')
                continue
            # Use a default font
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 20)
            except:
                font = ImageFont.load_default()

            # Prepare each line in parentheses and wrap to fit image width
            max_text_width = image.width - 40
            wrapped_lines = []
            for line in task1_lines:
                # Only include lines that contain [Damage]
                if '[Damage]' in line:
                    line = f'{line}'
                    # Wrap line to fit image width
                    # Estimate max chars by dividing width by font size (rough)
                    est_max_chars = max(20, max_text_width // 12)
                    for wrapped in textwrap.wrap(line, width=est_max_chars):
                        wrapped_lines.append(wrapped)            # Calculate height for all wrapped lines
            line_heights = [ImageDraw.Draw(image).textbbox((0,0), l, font=font)[3] for l in wrapped_lines]
            total_height = sum(line_heights) + 4 * len(wrapped_lines)

            # Create new image with extra space at the bottom
            new_height = image.height + total_height + 20
            new_img = Image.new(image.mode, (image.width, new_height), (255,255,255))
            new_img.paste(image, (0,0))
            draw = ImageDraw.Draw(new_img)

            # Draw each wrapped line, left-aligned, below the image with more padding
            y = image.height + 10
            left_margin = 20
            for i, line in enumerate(wrapped_lines):
                bbox = draw.textbbox((left_margin, y), line, font=font)
                draw.rectangle([(0, y-4), (image.width, y + line_heights[i] + 8)], fill=(0,0,0,230))
                draw.text((left_margin, y), line, font=font, fill=(255,255,255))
                y += line_heights[i] + 4

            new_img.save(caption_img_path)

    print(f'Minor damage count: {len(minor)}')
    print(f'Moderate damage count: {len(moderate)}')
    print(f'Severe damage count: {len(severe)}')
    if INCLUDE_NONE_DAMAGE:
        print(f'None damage count: {len(none)}')

if __name__ == "__main__":
    main()
