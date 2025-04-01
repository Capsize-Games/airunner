#!/bin/bash
# filepath: /home/joe/Projects/airunner/src/airunner/gui/resources/icons/feather/copy_icons.sh

# Create dark directory if it doesn't exist
mkdir -p ./dark

# Process all SVG files in the light directory
for svg_file in ./light/*.svg; do
    if [ ! -f "$svg_file" ]; then
        echo "No SVG files found in ./light/ directory!"
        exit 1
    fi
    
    filename=$(basename "$svg_file")
    echo "Processing $filename..."
    
    # Replace all stroke colors with white and preserve fill="none"
    sed -e 's/stroke="[^"]*"/stroke="#ffffff"/g' \
        -e 's/stroke:.*?;/stroke:#ffffff;/g' \
        -e 's/fill="[^"]*"/fill="#ffffff"/g' \
        -e 's/fill:.*?;/fill:#ffffff;/g' \
        -e 's/fill="#ffffff"/fill="none"/g' \
        -e 's/fill:#ffffff;/fill:none;/g' \
        "$svg_file" > "./dark/$filename"
    
    # Check if the conversion produced a valid file of non-zero size
    if [ -s "./dark/$filename" ]; then
        echo "✓ Created ./dark/$filename"
    else
        echo "✗ Failed to create ./dark/$filename"
        exit 1
    fi
done

echo "All Feather icons have been converted for dark theme."