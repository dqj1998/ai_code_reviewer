import os
import gitlab
import datetime
import argparse
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables
gitlab_private_token = os.getenv("GITLAB_PRIVATE_TOKEN")
workspace_path = os.getenv("WORKSPACE_PATH")
gitlab_url = os.getenv("GITLAB_URL")

# Validate required environment variables
if not gitlab_private_token:
    print("Error: GITLAB_PRIVATE_TOKEN environment variable is not set.")
    print("Please set it in your .env file or environment.")
    exit(1)

if not workspace_path:
    print("Error: WORKSPACE_PATH environment variable is not set.")
    print("Please set it in your .env file or environment.")
    exit(1)

if not gitlab_url:
    print("Error: GITLAB_URL environment variable is not set.")
    print("Please set it in your .env file or environment.")
    print("Example: GITLAB_URL=https://devops.genesis-bk.com/gitlab")
    exit(1)

# Parse command-line arguments
parser = argparse.ArgumentParser(description='GitLab MR All Comments Crawler')
parser.add_argument('-u', '--url', dest='mr_url', type=str, required=True, help='The URL of the merge request')
args = parser.parse_args()
mr_url = args.mr_url

# Extract project path and MR IID from URL
url_prefix = f"{gitlab_url}/"
if not mr_url.startswith(url_prefix):
    print(f"Error: MR URL must start with {url_prefix}")
    print(f"Provided URL: {mr_url}")
    exit(1)

path_and_iid = mr_url[len(url_prefix):]
match = re.match(r'(.+)/-/merge_requests/(\d+)', path_and_iid)
if not match:
    print("Invalid Merge Request URL format.")
    exit(1)

project_path, merge_request_iid = match.groups()

# Authenticate with GitLab
gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token)

try:
    # Get the project
    project = gl.projects.get(project_path)

    # Get the merge request
    mr = project.mergerequests.get(merge_request_iid)

    # Get all discussion threads for the merge request
    discussions = mr.discussions.list(all=True)

    if discussions:
        # Create a directory with the format review_<timestamp>
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        review_dir = os.path.join(workspace_path, f"review_{timestamp}")
        os.makedirs(review_dir, exist_ok=True)

        # Save all comments to all_comments.txt
        comments_file_path = os.path.join(review_dir, "all_comments.txt")
        
        total_comments = 0
        resolved_count = 0
        unresolved_count = 0
        
        with open(comments_file_path, "w", encoding='utf-8') as f:
            f.write(f"Merge Request: {mr.title}\n")
            f.write(f"URL: {mr_url}\n")
            f.write(f"Author: {mr.author['name']}\n")
            f.write(f"Created at: {mr.created_at}\n")
            f.write("=" * 80 + "\n\n")
            
            for d in discussions:
                discussion = mr.discussions.get(d.id)
                
                # Determine if the discussion is resolved
                is_resolved = False
                is_resolvable = False
                
                if discussion.attributes.get('individual_note') is False:
                    for note in discussion.attributes['notes']:
                        if note.get('resolvable'):
                            is_resolvable = True
                            if note.get('resolved'):
                                is_resolved = True
                            break
                
                # Track resolved/unresolved status
                if is_resolvable:
                    if is_resolved:
                        resolved_count += 1
                    else:
                        unresolved_count += 1
                
                # Get the first note in the discussion for context
                first_note = discussion.attributes['notes'][0]
                
                # Write discussion header
                f.write("=" * 80 + "\n")
                f.write(f"Discussion ID: {discussion.id}\n")
                
                if is_resolvable:
                    status = "RESOLVED" if is_resolved else "UNRESOLVED"
                    f.write(f"Status: {status}\n")
                else:
                    f.write(f"Status: NON-RESOLVABLE (General Comment)\n")
                
                # If it's a DiffNote, include file and line information
                if first_note.get('type') == 'DiffNote':
                    position = first_note.get('position')
                    if position:
                        file_path = position.get('new_path')
                        line_range = position.get('line_range')
                        
                        f.write(f"File: {file_path}\n")
                        if line_range:
                            start_line = line_range['start']['new_line']
                            end_line = line_range['end']['new_line']
                            f.write(f"Lines: {start_line}-{end_line}\n")
                            
                            try:
                                file_content = project.files.get(file_path=file_path, ref=mr.sha).decode().splitlines()
                                f.write("Code:\n")
                                for i in range(start_line - 1, end_line):
                                    if i < len(file_content):
                                        f.write(f"  {file_content[i]}\n")
                            except gitlab.exceptions.GitlabError as e:
                                f.write("Could not retrieve code snippet.\n")
                            except Exception as e:
                                f.write(f"Error retrieving code: {e}\n")
                
                f.write("-" * 80 + "\n")
                
                # Write all notes in the discussion
                for idx, note in enumerate(discussion.attributes['notes'], 1):
                    total_comments += 1
                    f.write(f"Comment #{idx}:\n")
                    f.write(f"  Author: {note['author']['name']}\n")
                    f.write(f"  Created at: {note['created_at']}\n")
                    if note.get('updated_at') and note['updated_at'] != note['created_at']:
                        f.write(f"  Updated at: {note['updated_at']}\n")
                    f.write(f"  Body:\n")
                    # Indent the comment body for better readability
                    for line in note['body'].split('\n'):
                        f.write(f"    {line}\n")
                    f.write("\n")
                
                f.write("\n")
            
            # Write summary at the end
            f.write("=" * 80 + "\n")
            f.write("SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total discussions: {len(discussions)}\n")
            f.write(f"Total comments: {total_comments}\n")
            f.write(f"Resolved discussions: {resolved_count}\n")
            f.write(f"Unresolved discussions: {unresolved_count}\n")
            f.write(f"General comments: {len(discussions) - resolved_count - unresolved_count}\n")
        
        print(f"Successfully saved all comments to {comments_file_path}")
        print(f"Total discussions: {len(discussions)}")
        print(f"Total comments: {total_comments}")
        print(f"Resolved: {resolved_count}, Unresolved: {unresolved_count}")
    else:
        print("No comments found in this merge request.")

except gitlab.exceptions.GitlabError as e:
    print(f"An error occurred: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
