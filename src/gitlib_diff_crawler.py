import os
import re
import argparse
import datetime
import gitlab
from dotenv import load_dotenv

load_dotenv()

gitlab_private_token = os.getenv("GITLAB_PRIVATE_TOKEN")
workspace_path = os.getenv("WORKSPACE_PATH")
gitlab_url = os.getenv("GITLAB_URL")


def main():
    parser = argparse.ArgumentParser(description='Fetch only changed code from GitLab MR diffs')
    parser.add_argument('-d', '--diff-url', dest='diff_url', type=str, required=True, help='The URL of the merge request diffs')
    args = parser.parse_args()
    diff_url = args.diff_url

    url_prefix = f"{gitlab_url}/" if gitlab_url else None
    if not url_prefix or not diff_url.startswith(url_prefix):
        print(f"Diff URL must start with {url_prefix}")
        return

    path_and_iid = diff_url[len(url_prefix):]
    m = re.match(r'(.+)/-/merge_requests/(\d+)/diffs', path_and_iid)
    if not m:
        print("Invalid Merge Request URL format for diffs.")
        return

    project_path, merge_request_iid = m.groups()

    gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_private_token)

    try:
        project = gl.projects.get(project_path)
        mr = project.mergerequests.get(merge_request_iid)

        diff_list = mr.diffs.list()
        if not diff_list:
            print("No diffs found for the provided URL.")
            return

        latest_diff = mr.diffs.get(diff_list[0].id)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(workspace_path or '.', f"coding_rule_{timestamp}")
        os.makedirs(out_dir, exist_ok=True)

        diff_file_path = os.path.join(out_dir, "diff.txt")
        with open(diff_file_path, "w") as out:
            for diff in latest_diff.diffs:
                new_path = diff.get('new_path') or diff.get('old_path') or '<unknown>'
                out.write(f"File: {new_path}\n")
                out.write("Changed lines:\n")
                diff_text = diff.get('diff') or ''
                for line in diff_text.splitlines():
                    # Skip diff metadata lines
                    if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                        continue
                    # Collect added or removed code lines only
                    if line.startswith('+') or line.startswith('-'):
                        out.write(f"{line}\n")
                out.write("\n" + "-" * 40 + "\n")

        print(f"Saved changed code to {diff_file_path}")

    except gitlab.exceptions.GitlabError as e:
        print(f"GitLab API error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()