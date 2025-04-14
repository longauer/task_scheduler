#!/bin/bash

# Initialize a variable to store the total line count
total_lines=0

# Find all .py files recursively, excluding directories that start with a dot
# Process each file in the same shell without using a pipe
while IFS= read -r file; do
    # Print the file path
    echo "Found file: $file"
    
    # Get the line count for the current file and add it to the total
    file_lines=$(wc -l < "$file")
    total_lines=$((total_lines + file_lines))
done < <(find . -type f -name "*.py" -not -path '*/.*')

# Output the total line count
echo "Total lines of Python code: $total_lines"
