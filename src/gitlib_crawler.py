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

# Parse command-line arguments
parser = argparse.ArgumentParser(description='GitLab MR Unresolved Threads Crawler')
parser.add_argument('-c', '--comments-url', dest='mr_url', type=str, help='The URL of the merge request for comments')
parser.add_argument('-d', '--diff-url', dest='diff_url', type=str, help='The URL of the merge request for diffs')
args = parser.parse_args()
mr_url = args.mr_url
diff_url = args.diff_url

if not mr_url and not diff_url:
    print("Error: At least one URL (--comments-url or --diff-url) must be provided.")
    parser.print_help()
    exit(1)

# --- Comment Processing ---
if mr_url:
    # Extract project path and MR IID from comment URL
    url_prefix = f"{gitlab_url}/"
    if not mr_url.startswith(url_prefix):
        print(f"MR URL for comments must start with {url_prefix}")
        exit(1)

    path_and_iid = mr_url[len(url_prefix):]
    match = re.match(r'(.+)/-/merge_requests/(\d+)', path_and_iid)
    if not match:
        print("Invalid Merge Request URL format for comments.")
        exit(1)

    project_path, merge_request_iid = match.groups()

# Authenticate with GitLab
gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token)

try:
    if mr_url:
        # Get the project
        project = gl.projects.get(project_path)

        # Get the merge request
        mr = project.mergerequests.get(merge_request_iid)

        # Get all discussion threads for the merge request
        discussions = mr.discussions.list(all=True)

        # Filter for unresolved threads
        unresolved_threads = []
        for d in discussions:
            discussion = mr.discussions.get(d.id)
            is_unresolved = False
            if discussion.attributes.get('individual_note') is False:
                for note in discussion.attributes['notes']:
                    if note.get('resolvable') and not note.get('resolved'):
                        is_unresolved = True
                        break
            if is_unresolved:
                unresolved_threads.append(discussion)

        if unresolved_threads:
            # Create a directory with the format review_<timestamp>
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            review_dir = os.path.join(workspace_path, f"review_{timestamp}")
            os.makedirs(review_dir, exist_ok=True)

            # Save the unresolved threads to comments.txt
            comments_file_path = os.path.join(review_dir, "comments.txt")
            with open(comments_file_path, "w") as f:
                for discussion in unresolved_threads:
                    # Find the first note in the discussion to get context if it's a DiffNote
                    first_note = discussion.attributes['notes'][0]
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
                                        f.write(f"  {file_content[i]}\n")
                                except gitlab.exceptions.GitlabError as e:
                                    f.write("Could not retrieve code snippet.\n")
                        f.write("-" * 20 + "\n")

                    for note in discussion.attributes['notes']:
                        # Write each note's body to the file
                        f.write(f"Author: {note['author']['name']}\n")
                        f.write(f"Comment: {note['body']}\n")
                        f.write(f"Created at: {note['created_at']}\n")
                        f.write("-" * 20 + "\n")
            
            print(f"Successfully saved unresolved threads to {comments_file_path}")
        else:
            print("No unresolved threads found.")
    else:
        # This block is to ensure review_dir is created when only diff_url is provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        review_dir = os.path.join(workspace_path, f"review_{timestamp}")
        os.makedirs(review_dir, exist_ok=True)


    # --- Diff Processing ---
    if diff_url:
        # Extract project path and MR IID from diff URL
        diff_path_and_iid = diff_url[len(url_prefix):]
        diff_match = re.match(r'(.+)/-/merge_requests/(\d+)/diffs', diff_path_and_iid)
        if not diff_match:
            print("Invalid Merge Request URL format for diffs.")
            exit(1)

        diff_project_path, diff_merge_request_iid = diff_match.groups()

        try:
            # Get the project and merge request for the diff
            diff_project = gl.projects.get(diff_project_path)
            diff_mr = diff_project.mergerequests.get(diff_merge_request_iid)
            
            # Get the diffs
            diff_list = diff_mr.diffs.list()
            
            if diff_list:
                # Get the latest diff object to access its 'diffs' attribute
                latest_diff = diff_mr.diffs.get(diff_list[0].id)

                # Use the same review_dir as for comments
                if not 'review_dir' in locals():
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    review_dir = os.path.join(workspace_path, f"review_{timestamp}")
                    os.makedirs(review_dir, exist_ok=True)

                diff_file_path = os.path.join(review_dir, "diff.txt")
                with open(diff_file_path, "w") as f:
                    for diff in latest_diff.diffs:
                        f.write(f"File: {diff['new_path']}\n")
                        f.write("Changes:\n")
                        f.write(diff['diff'])
                        f.write("\n" + "-" * 20 + "\n")
                
                print(f"Successfully saved diffs to {diff_file_path}")
            else:
                print("No diffs found for the provided URL.")

        except gitlab.exceptions.GitlabError as e:
            print(f"An error occurred while processing diffs: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing diffs: {e}")

except gitlab.exceptions.GitlabError as e:
    print(f"An error occurred: {e}")

except Exception as e:
    print(f"An unexpected error occurred: {e}")
