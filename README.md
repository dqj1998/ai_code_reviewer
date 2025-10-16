# AI Code Review Tool

## About

This tool automates the process of code review using AI. It fetches merge request data from GitLab, including unresoved comments and diffs, and then generates an AI-based review of the code changes.

## Installation

1. **Create a Python virtual environment:**

    ```bash
    python3 -m venv myenv
    ```

2. **Activate the virtual environment:**

    ```bash
    source myenv/bin/activate
    ```

3. **Install the required dependencies:**

    ```bash
    pip install -r src/requirements.txt
    ```

## Usage

The main script to run the code review process is `run_review.sh`.

### Prerequisites

Before running the script, you need to create a `.env` file in the `ai_tool` directory. You can do this by copying the `.env-example` file:

```bash
cp .env-example .env
```

Then, open the `.env` file and fill in the required values for your GitLab instance and Azure OpenAI credentials.

* A GitLab personal access token with `api` scope.
And other configs.

### Running the Review

To run the tool, execute the `run_review.sh` script with the necessary arguments:

```bash
./run_review.sh --comments-url <your_comments_url> --diff-url <your_diff_url>
```

### Optional Arguments

* `--language`: Specify the languages for the AI review. The default is `english,japanese`.

    ```bash
    ./run_review.sh --language "english,japanese,chinese" --comments-url <your_comments_url> --diff-url <your_diff_url>
    ```

### Output

The script will create a new directory in the `workspace` folder with the current timestamp. This directory will contain:

* `comments.txt`: The unresolved comments fetched from the merge request.
* `diff.txt`: The diff of the merge request.
* `result.md`: The AI-generated code review.
