# llm-deepseek-ya

[![PyPI](https://img.shields.io/pypi/v/llm-deepseek-ya.svg)](https://pypi.org/project/llm-deepseek-ya/0.1.0/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/delijati/llm-deepseek-ya/blob/main/LICENSE)

LLM access to DeepSeek's API

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).

```bash
llm install llm-deepseek-ya
```

## Usage

First, set an [API key](https://platform.deepseek.com/api_keys) for DeepSeek:

```bash
llm keys set deepseek
# Paste key here
```

Run `llm models` to list the models, and `llm models --options` to include a list of their options.

### Running Prompts

Run prompts like this:

```bash
llm -m deepseek-flash "Describe a futuristic city on Mars"
llm -m deepseek-v4-pro "Write a Python function to sort a list of numbers"
```

The legacy names `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are aliases for `deepseek-flash`.

### Thinking Mode

Both models think by default and the plugin shows the chain of thought reasoning before the final answer.

```bash
# Normal usage - will show reasoning by default
llm -m deepseek-flash "What is 537 * 943?"

# Hide reasoning when you only want the final answer
llm -m deepseek-flash "What is 537 * 943?" -o show_reasoning false
```

### Features

#### Prefill

The `prefill` option allows you to provide initial text for the model's response. This is useful for guiding the model's output.

Example:

```bash
llm -m deepseek-flash "What are some wild and crazy activities for a holiday party?" -o prefill "Here are some off-the-wall ideas to make your holiday party unforgettable [warning: these may not be suitable for work holiday parties]:"
```

You can also load prefill text from a file:

```bash
# Create a file with your prefill text
echo "Here are some unique holiday party ideas:" > prefill.txt

# Use the file path as the prefill value
llm -m deepseek-flash "What are some fun activities for a holiday party?" -o prefill prefill.txt
```

This is especially useful for longer prefill text that would be unwieldy on the command line.

#### JSON Response Format

The `response_format` option allows you to specify that the model should output its response in JSON format. To ensure the model outputs valid JSON, include the word "json" in the system or user prompt. Optionally, you can provide an example of the desired JSON format to guide the model.

Example:

```bash
llm -m deepseek-flash "What are some fun activities for a holiday party?" -o response_format json_object --system "json"
```

To guide the model further, you can provide an example JSON structure:

```bash
llm -m deepseek-flash "What are some way to tell if a holiday party is fun?" -o response_format json_object --system 'EXAMPLE JSON OUTPUT: {"event": "holiday_party_fun", "success_metric": ["..."]}'
```

#### JSON Schema Support

DeepSeek Chat models support JSON schema output (via LLM's `--schema` option). When you provide a schema, the plugin automatically enables JSON mode and includes the schema in the system message to guide the model's output.

**Important Note:** DeepSeek's API does not validate the output against the schema - it only uses JSON mode. The schema is provided to the model as guidance, so the model will attempt to follow it, but strict validation is not enforced.

Example:

```bash
llm -m deepseek-flash "Generate a user profile" --schema '{"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "number"}, "email": {"type": "string"}}, "required": ["name", "age"]}'
```

You can also use LLM's schema file support:

```bash
# Create a schema file
cat > user_schema.json << 'EOF'
{
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "number"},
    "email": {"type": "string"},
    "interests": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["name", "age"]
}
EOF

# Use the schema file
llm -m deepseek-flash "Generate a user profile for a software developer" --schema user_schema.json
```

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

```bash
cd llm-deepseek-ya
python3 -m venv venv
source venv/bin/activate
```
