#!/bin/bash

# This script runs the full code review process.
# It first runs the gitlib_crawler.py to get comments and diffs from GitLab,
# then runs the reviewer.py to get an AI-generated review.

# Default language parameter
LANGUAGE="english,japanese"
CRAWLER_ARGS=()

# Parse command-line arguments to separate crawler args from the language arg
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -l|--language)
      LANGUAGE="$2"
      shift # past argument
      shift # past value
      ;;
    *)    # unknown option
      CRAWLER_ARGS+=("$1") # save it in an array for later
      shift # past argument
      ;;
  esac
done

# Ensure the script is run from the `ai_review_tool` directory.
cd "$(dirname "$0")" || exit

# Check if at least one URL is provided
if [ ${#CRAWLER_ARGS[@]} -eq 0 ]; then
  echo "Usage: $0 [--language <lang1,lang2,...>] --comments-url <comments_url> --diff-url <diff_url>"
  exit 1
fi

# Activate python environment if it exists
if [ -f "../myenv/bin/activate" ]; then
    source "../myenv/bin/activate"
    PYTHON_EXEC="../myenv/bin/python"
else
    PYTHON_EXEC="python"
fi

# Run the gitlib_crawler.py and capture the output
# The arguments passed to this script (e.g., --comments-url) are forwarded to the crawler.
echo "Running GitLab crawler..."
output=$($PYTHON_EXEC src/gitlib_crawler.py "${CRAWLER_ARGS[@]}")

# Echo the output from the crawler for debugging or information
echo "$output"

# Extract the review directory path from the crawler's output.
# It looks for lines containing "Successfully saved" and extracts the directory path.
review_dir=$(echo "$output" | grep "Successfully saved" | head -n 1 | sed -E 's/Successfully saved .* to (.*)\/(comments|diff)\.txt/\1/')

if [ -n "$review_dir" ]; then
  echo "Review directory found: $review_dir"
  # Run the reviewer.py with the extracted directory path.
  echo "Running AI reviewer..."
  $PYTHON_EXEC src/reviewer.py "$review_dir" --language "$LANGUAGE"
  echo "Review process completed. Results are in $review_dir/result.md"
else
  echo "Could not determine the review directory from the gitlib_crawler.py output."
  echo "Please check the crawler's output for errors."
  exit 1
fi
