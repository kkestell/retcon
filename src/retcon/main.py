import os
import subprocess
import argparse

import unidecode
from openai import OpenAI
import tiktoken


def num_tokens_from_string(string, model="gpt-4o-mini"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))


def num_tokens_from_messages(messages, model="gpt-4o-mini"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens = 0
    for message in messages:
        num_tokens += 4
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += -1
    num_tokens += 2
    return num_tokens


def get_commit_hashes():
    result = subprocess.run(['git', 'rev-list', '--reverse', 'HEAD'], capture_output=True, text=True)
    return result.stdout.split()


def change_commit_message(commit_hash, new_message):
    new_message_escaped = new_message.replace('"', '\\"').replace('\n', '\\n')
    command = [
        'git', 'filter-repo', '--force', '--commit-callback',
        f'if commit.original_id == b"{commit_hash}": commit.message = b"{new_message_escaped}"'
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def generate_prompt(commit_hash, model, max_diff_tokens):
    result_files = subprocess.run(['git', 'show', '--name-only', '--pretty=format:', commit_hash], capture_output=True,
                                  text=True, errors='replace')
    changed_files = result_files.stdout.strip()

    result_diff = subprocess.run(['git', 'show', commit_hash], capture_output=True, text=True, errors='replace')
    full_diff = result_diff.stdout

    diff = ""
    for line in full_diff.split('\n'):
        if num_tokens_from_string(diff + line, model) > max_diff_tokens:
            break
        diff += line + '\n'

    prompt = f"""Here are the changed files:
{changed_files}

Here is the diff:
{diff}

Based on this information, generate an appropriate commit message."""

    return prompt


def generate_new_commit_message(client, messages, prompt, model, max_conversation_tokens):
    messages.append({"role": "user", "content": prompt})

    while num_tokens_from_messages(messages, model) > max_conversation_tokens:
        if len(messages) > 1:
            messages.pop(1)
        else:
            break

    chat_completion = client.chat.completions.create(
        messages=messages,
        model=model,
        temperature=0
    )

    new_message = chat_completion.choices[0].message.content
    new_message = unidecode.unidecode(new_message)
    new_message = new_message.replace('```', '')
    new_message = new_message.strip()

    messages.append({"role": "assistant", "content": new_message})

    return new_message


def main():
    parser = argparse.ArgumentParser(description="Generate commit messages for a Git repository.")
    parser.add_argument("--repo", default=".", help="Path to the Git repository (default: current directory)")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use (default: gpt-4o-mini)")
    parser.add_argument("--max-conversation-tokens", type=int, default=50000, help="Maximum conversation tokens (default: 50000)")
    parser.add_argument("--max-diff-tokens", type=int, default=4000, help="Maximum number of tokens for the diff (default: 4000)")
    args = parser.parse_args()

    os.chdir(args.repo)
    commit_hashes = get_commit_hashes()

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    messages = [
        {
            "role": "system",
            "content": """You are an expert software developer tasked with writing clear and informative git commit messages.
* You will be provided with information about multiple commits in sequence.
* You use your knowledge of previous commits to improve the quality and consistency of your commit messages.
* You always avoid filler words, puffery, and adjective-heavy language.
* You are concise and to the point.
* Please do not feel the need to write excessively wordy commit messages. Be concise and to the point.
* If there are multiple changes, separate their descriptions with a semicolon.
* Describe the what of the change, not the why (you don't know) or the how (it's in the diff).

Banned words:
* Enhance
* Ensures
* Maintain
* Additionally
* Streamline
* Functionality

Given a list of changed files and a diff, generate a concise yet descriptive commit message that summarizes the changes made.
"""
        }
    ]

    for i in range(len(commit_hashes)):
        try:
            commit_hashes = get_commit_hashes()
            prompt = generate_prompt(commit_hashes[i], args.model, args.max_diff_tokens)
            new_message = generate_new_commit_message(client, messages, prompt, args.model, args.max_conversation_tokens)
            print(new_message)
            print("-" * 80)
            change_commit_message(commit_hashes[i], new_message)
        except Exception as e:
            print(e)
            import traceback
            traceback.print_exc()
            print("-" * 80)


if __name__ == '__main__':
    main()
