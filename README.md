# Retcon

Fix up your shitty commit messages.

## Usage

```
python src/retcon/main.py [options]
```

### Options

- `--repo PATH`: Path to the Git repository (default: current directory)
- `--model MODEL`: OpenAI model to use (default: gpt-4o-mini)
- `--max-conversation-tokens N`: Maximum conversation tokens (default: 50000)
- `--max-diff-tokens N`: Maximum number of tokens for the diff (default: 4000)

### Example

```
python src/retcon/main.py --repo /path/to/your/repo --model gpt-4 --max-diff-tokens 5000
```

## Warning

This script rewrites your Git history. Use with caution, especially on shared repositories. It's recommended to run this on a separate branch or a clone of your repository first.
