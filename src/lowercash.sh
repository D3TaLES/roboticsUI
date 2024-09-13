#!/bin/bash
export BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd $BASE_DIR

# Rename files by first renaming to a temporary file, then to the lowercase version
for file in *; do
  lowercase_file=$(echo "$file" | tr '[:upper:]' '[:lower:]')

  if [[ "$file" != "$lowercase_file" ]]; then
    # Rename to a temporary name first
    mv "$file" "${file}.tmp"
    # Rename to the lowercase version
    mv "${file}.tmp" "$lowercase_file"
  fi
done

cd ../
