#!/bin/bash

# Wrapper to run src/coding_rule_reviewer.py easily.
# Usage:
#   ./run_coding_rule.sh [-l language1,language2] <folder> <rules_file>
#   ./run_coding_rule.sh [-l language1,language2] --diff-url <url> <rules_file>
#
# If a --diff-url (or other crawler args) is provided and no <folder> is given,
# this script will invoke src/gitlib_diff_crawler.py, capture the created review
# directory, then run src/coding_rule_reviewer.py against that directory.
# Note: if no <folder> is provided and no crawler args are given, the script
# will use WORKSPACE_PATH from .env as the folder.

LANGUAGE="english,japanese"
FOLDER=""
RULES_FILE=""
CRAWLER_ARGS=()

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -l|--language)
      LANGUAGE="$2"
      shift; shift
      ;;
    -h|--help)
      echo "Usage: $0 [-l language1,language2] [--diff-url <url>] <folder> <rules_file>"
      echo "If <folder> is omitted, the script will use WORKSPACE_PATH from .env when available."
      exit 0
      ;;
    --diff-url|-d|--comments-url|-c)
      # forward diff/comment options and their values to the crawler
      CRAWLER_ARGS+=("$1")
      if [[ -n "$2" && "$2" != --* ]]; then
        CRAWLER_ARGS+=("$2")
        shift
      fi
      shift
      ;;
    *)
      if [[ "$1" == --* ]]; then
        # Forward any other --options (with optional value) to the crawler
        CRAWLER_ARGS+=("$1")
        if [[ -n "$2" && "$2" != --* ]]; then
          CRAWLER_ARGS+=("$2")
          shift
        fi
        shift
      else
        if [[ -z "$FOLDER" ]]; then
          # If crawler args were provided, the single positional argument
          # should be treated as the rules file (usage: --diff-url <url> <rules_file>).
          if [[ ${#CRAWLER_ARGS[@]} -gt 0 ]]; then
            RULES_FILE="$1"
          else
            FOLDER="$1"
          fi
        elif [[ -z "$RULES_FILE" ]]; then
          RULES_FILE="$1"
        else
          echo "Unknown extra argument: $1"
          exit 1
        fi
        shift
      fi
      ;;
  esac
done

# Ensure script runs from repo root
cd "$(dirname "$0")" || exit

# Load .env if present so we can use WORKSPACE_PATH as default folder
if [ -f ".env" ]; then
  # export variables defined in .env
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ -z "$RULES_FILE" ]]; then
  echo "Usage: $0 [-l language1,language2] [--diff-url <url>] <folder> <rules_file>"
  echo "Folder defaults to WORKSPACE_PATH from .env when omitted."
  exit 1
fi

# If no folder provided and no crawler args, use WORKSPACE_PATH from .env
if [[ -z "$FOLDER" && ${#CRAWLER_ARGS[@]} -eq 0 ]]; then
  if [[ -n "$WORKSPACE_PATH" ]]; then
    FOLDER="$WORKSPACE_PATH"
    echo "No folder provided — using WORKSPACE_PATH from .env: $FOLDER"
  else
    echo "No folder provided and WORKSPACE_PATH not set in .env"
    echo "Usage: $0 [-l language1,language2] [--diff-url <url>] <folder> <rules_file>"
    exit 1
  fi
fi

# If crawler args were provided (e.g., --diff-url) and folder not supplied,
# run the gitlab diff crawler to obtain a folder that contains diff.txt
if [[ ${#CRAWLER_ARGS[@]} -gt 0 && -z "$FOLDER" ]]; then
  if [ -f "../myenv/bin/activate" ]; then
    source "../myenv/bin/activate"
    PYTHON_EXEC="../myenv/bin/python"
  else
    PYTHON_EXEC="python"
  fi

  echo "Running GitLab diff crawler..."
  output=$($PYTHON_EXEC src/gitlib_diff_crawler.py "${CRAWLER_ARGS[@]}")
  echo "$output"

  # Try to extract the directory path from crawler output.
  # Support messages like:
  #   "Saved changed code to /path/to/outdir/diff.txt"
  #   "Successfully saved diffs to /path/to/outdir/diff.txt"
  review_dir=$(echo "$output" | grep -E "Saved changed code to|Successfully saved" | head -n1 | sed -E 's/.*(Saved changed code to|Successfully saved .* to) (.*)\/(comments|diff)\.txt.*/\2/')

  if [ -n "$review_dir" ]; then
    echo "Review directory found: $review_dir"
    FOLDER="$review_dir"
  else
    echo "Could not determine the review directory from gitlib_diff_crawler.py output."
    echo "Please check the crawler's output for errors."
    exit 1
  fi
fi

# Ensure we have a python executor (if not already set by crawler block)
if [ -z "$PYTHON_EXEC" ]; then
  if [ -f "../myenv/bin/activate" ]; then
    source "../myenv/bin/activate"
    PYTHON_EXEC="../myenv/bin/python"
  else
    PYTHON_EXEC="python"
  fi
fi

echo "Running coding rule reviewer on folder: $FOLDER"
echo "Rules file: $RULES_FILE"
$PYTHON_EXEC src/coding_rule_reviewer.py "$FOLDER" "$RULES_FILE" -l "$LANGUAGE"

exit 0