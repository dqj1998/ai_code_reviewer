#!/usr/bin/env python3
import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from typing import Optional

from azure_ai_caller import init_ai_caller, generate_response
from ai_prompts import init_prompt_map

def read_text_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

async def run_review(folder: str, rules_path: str, languages: str = "english") -> None:
    """
    Read diff.txt from folder and rules from rules_path, call AI to check
    whether the diff matches each coding rule, and write aggregated results
    to coding_rule_result.md inside the folder.
    """
    diff_path = os.path.join(folder, "diff.txt")
    if not os.path.exists(diff_path):
        print(f"Error: diff file not found at {diff_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(rules_path):
        print(f"Error: rules file not found at {rules_path}", file=sys.stderr)
        sys.exit(1)

    diff_content = read_text_file(diff_path)
    rules_content = read_text_file(rules_path)

    # Parse rules: one rule per line; ignore empty lines and lines that start with '#'
    rules = []
    for raw in rules_content.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lstrip().startswith('#'):
            continue
        rules.append(line)

    # Initialize AI caller (load env from repo .env by convention)
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
    init_ai_caller()
    prompts = init_prompt_map()

    # Prefer a dedicated coding_rule_prompt in ai_prompts.yaml, fall back to code_review_prompt.
    coding_rule_template = prompts.get("coding_rule_prompt")

    if not coding_rule_template:
        print("Error: no coding_rule_prompt or code_review_prompt found in prompts.", file=sys.stderr)
        sys.exit(1)

    aggregated_results = []

    # Loop through each rule and call AI with that single rule and the full diff
    print(f"Checking {len(rules)} rules...")
    for rule in rules:
        print(f"Checking rule: {rule}")
        messages = []
        # Fill the template for this single rule
        for message in coding_rule_template:
            content = message.get("content", "").format(comments="", diff=diff_content, rules=rule)
            if message.get("role") == "system":
                content += f"\n\nYour answer should be in the following languages, in this order: {languages}."
            messages.append({"role": message.get("role", "user"), "content": content})

        try:
            print(f"==========\n Calling AI...{messages} ==========\n")
            response = await generate_response(messages)
        except Exception as e:
            print(f"AI call failed for rule '{rule}': {e}", file=sys.stderr)
            sys.exit(1)

        # Skip responses that contain "no issues found" (case-insensitive) or are empty
        if response is not None:
            resp_trim = response.strip()
            if resp_trim and "no issues found" not in resp_trim.lower():
                header = f"### Rule: {rule}\n\n"
                aggregated_results.append(header + response)

    output_path = os.path.join(folder, "coding_rule_result.md")
    try:
        if aggregated_results:
            final = "\n\n".join(aggregated_results)
        else:
            final = "No issues found."
        with open(output_path, 'w', encoding='utf-8') as out:
            out.write(final)
    except Exception as e:
        print(f"Failed to write result file: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Result written to {output_path}")

def parse_args(argv: Optional[list] = None):
    parser = argparse.ArgumentParser(description="Check diff against coding rules using AI.")
    parser.add_argument("folder", help="Folder that contains diff.txt")
    parser.add_argument("rules_file", help="Path to the file that contains coding rules")
    parser.add_argument("-l", "--language", help="Comma-separated list of languages for the AI response (e.g., japanese,english,chinese).", default="english")
    return parser.parse_args(argv)

def main():
    args = parse_args()
    asyncio.run(run_review(args.folder, args.rules_file, args.language))

if __name__ == "__main__":
    main()