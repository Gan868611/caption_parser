#!/bin/bash

#!/bin/bash

# ========================
# Configurable Variables
# ========================
IMAGE_PATH="usroad/ALPR MD-210 NB Livingston Rd/ALPR MD-210 NB Livingston Rd 5-18-2025 12.25.59 EDT - 5-18-2025 13.25.59 EDT_frame0547_det514_1162px_vehicle_0p770.png"
IMAGE_BASE_DIR="/home/cynapse/terence/database/blip/"
OUTPUT_DIR="/home/cynapse/zhenyang/caption_parser/"

# ========================
# Example Usage
# ========================


# Combine base dir and image path
# ========================
FULL_IMAGE_PATH="$IMAGE_BASE_DIR/$IMAGE_PATH"

# Ensure output dir exists
mkdir -p "$OUTPUT_DIR"

# Copy the file
cp "$FULL_IMAGE_PATH" "$OUTPUT_DIR/"

# Feedback
echo "Copied:"
echo "  From: $FULL_IMAGE_PATH"
echo "  To:   $OUTPUT_DIR"
