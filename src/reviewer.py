
import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv

from azure_ai_caller import init_ai_caller, generate_response
from ai_prompts import init_prompt_map

def read_file_content(file_path):
    """Reads the content of a file and returns it as a string."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

async def main():
    """Main function to review code changes."""
    parser = argparse.ArgumentParser(description='Review code changes using AI.')
    parser.add_argument('review_path', help='Path to the directory containing comments.txt and diff.txt.')
    parser.add_argument('-l', '--language', help='Comma-separated list of languages for the AI response (e.g., japanese,english,chinese).', default='english')
    args = parser.parse_args()

    try:
        comments_path = os.path.join(args.review_path, 'comments.txt')
        diff_path = os.path.join(args.review_path, 'diff.txt')
        rules_path = os.path.join(os.path.dirname(__file__), 'rules.md')
        comments_content = read_file_content(comments_path)
        diff_content = read_file_content(diff_path)
        rules_content = read_file_content(rules_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Initialize the AI caller
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
    init_ai_caller()
    prompts = init_prompt_map()
    code_review_prompt_template = prompts.get("code_review_prompt")

    if not code_review_prompt_template:
        print("Error: 'code_review_prompt' not found in ai_prompts.yaml")
        sys.exit(1)

    # Create the prompt for the AI
    messages = []
    for message in code_review_prompt_template:
        # Replace placeholders in the content
        formatted_content = message['content'].format(comments=comments_content, diff=diff_content, rules=rules_content)
        if message['role'] == 'system':
            formatted_content += f"\n\nYour answer should be in the following languages, in this order: {args.language}."
        messages.append({
            "role": message['role'],
            "content": formatted_content
        })

    # Generate the AI response
    try:
        review_result = await generate_response(messages)
        output_path = os.path.join(args.review_path, 'result.md')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(review_result)
        print(f"AI review result saved to {output_path}")
    except Exception as e:
        print(f"An error occurred while generating the AI response: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
