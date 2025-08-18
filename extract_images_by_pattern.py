#!/usr/bin/env python3

"""
Image Extraction Utility

This script extracts images from a source directory based on patterns in a text file.
It copies matching images to a specified output directory while preserving filenames.

Features:
- Reads image paths from a text file (expects entries ending in .png:)
- Copies matched images to a target directory
- Preserves original filenames
- Reports successful copies and missing files
- Creates output directory if it doesn't exist

Usage:
    python3 extract_images_by_pattern.py

Configuration:
    BASE_DIR: Source directory containing the original images
    INPUT_FILE: Text file containing image paths (one per line, ending in .png:)
    OUTPUT_DIR: Destination directory for copied images

Example input file format:
    path/to/image1.png:
    path/to/image2.png:
    ...
"""

import os
import shutil

# === CONFIGURATION ===
BASE_DIR = '/home/cynapse/terence/database/'  # Base directory containing source images
INPUT_FILE = 'false_alarm.txt'  # File containing list of images to copy
OUTPUT_DIR = './fasle_alarm_usroad_severe'  # Directory where images will be copied

def main():
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Counter for statistics
    copied_count = 0
    missing_count = 0

    print(f"Starting image extraction from {INPUT_FILE} to {OUTPUT_DIR}")
    
    with open(INPUT_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line.endswith('.png:'):
                rel_path = line.split(':')[0]
                src_path = os.path.join(BASE_DIR, rel_path)
                dst_path = os.path.join(OUTPUT_DIR, os.path.basename(rel_path))
                
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                    print(f'Copied: {os.path.basename(src_path)}')
                    copied_count += 1
                else:
                    print(f'Missing: {os.path.basename(src_path)}')
                    missing_count += 1

    # Print summary
    print("\nExtraction Summary:")
    print(f"Images copied: {copied_count}")
    print(f"Images missing: {missing_count}")
    print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    main()
