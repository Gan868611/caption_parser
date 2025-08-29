 #!/bin/bash

#!/bin/bash

# ========================
# Configurable Variables
# ========================
IMAGE_PATH="/usroad/ALPR MD-210 NB Livingston Rd/ALPR MD-210 NB Livingston Rd 5-19-2025 10.25.59 EDT - 5-19-2025 11.25.59 EDT_frame0187_det252_0265px_vehicle_0p856.png"
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
