import llm
from llm.default_plugins.openai_models import Chat
from pathlib import Path
import json
import time
import httpx
import os
from typing import Optional
from pydantic import Field

# Constants for cache timeout and API base URL
CACHE_TIMEOUT = 3600
DEEPSEEK_API_BASE = "https://api.deepseek.com/beta"  # For inference
DEEPSEEK_MODELS_URL = "https://api.deepseek.com/models"  # For listing models


def get_deepseek_models():
    """Fetch and cache DeepSeek models."""
    key = llm.get_key("", "deepseek", "LLM_DEEPSEEK_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else None
    return fetch_cached_json(
        url=DEEPSEEK_MODELS_URL,
        path=llm.user_dir() / "deepseek_models.json",
        cache_timeout=CACHE_TIMEOUT,
        headers=headers,
    )["data"]


def get_model_ids_with_aliases(models):
    """Extract model IDs and create empty aliases list."""
    return [(model["id"], []) for model in models]


class DeepSeekChat(Chat):
    needs_key = "deepseek"
    key_env_var = "LLM_DEEPSEEK_KEY"

    def __init__(self, model_id, **kwargs):
        kwargs.setdefault("supports_schema", True)
        super().__init__(model_id, **kwargs)
        self.api_base = DEEPSEEK_API_BASE

    def __str__(self):
        return f"DeepSeek Chat: {self.model_id}"

    class Options(Chat.Options):
        prefill: Optional[str] = Field(
            description="Initial text for the model's response (beta feature). Uses DeepSeek's Chat Prefix Completion.",
            default=None,
        )
        response_format: Optional[str] = Field(
            description="Format of the response (e.g., 'json_object').", default=None
        )
        show_reasoning: Optional[bool] = Field(
            description="Show the chain of thought reasoning for the DeepSeek Reasoner model.",
            default=True,
        )

    def execute(self, prompt, stream, response, conversation, key=None):
        messages = self._build_messages(conversation, prompt)
        response._prompt_json = {"messages": messages}
        kwargs = self.build_kwargs(prompt, stream)

        max_tokens = kwargs.pop("max_tokens", 8192)

        # Enable JSON mode if schema is provided or response_format is set
        if prompt.schema or prompt.options.response_format:
            kwargs["response_format"] = {"type": "json_object"}

            # If schema is provided, add it to the system message as guidance
            # Note: DeepSeek doesn't validate against the schema, but the model can follow it
            if prompt.schema:
                schema_instruction = f"\n\nYou must respond with valid JSON matching this schema:\n{json.dumps(prompt.schema, indent=2)}"
                # Add schema to system message or create one if it doesn't exist
                if messages and messages[0].get("role") == "system":
                    messages[0]["content"] += schema_instruction
                else:
                    messages.insert(
                        0,
                        {
                            "role": "system",
                            "content": f"You are a helpful assistant.{schema_instruction}",
                        },
                    )

        # Remove options that aren't supported by the OpenAI client
        kwargs.pop("prefill", None)
        kwargs.pop("show_reasoning", None)
        show_reasoning = prompt.options.show_reasoning

        client = self.get_client(key)

        try:
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=stream,
                max_tokens=max_tokens,
                **kwargs,
            )

            if stream:
                for chunk in completion:
                    # Stream both reasoning content and regular content directly
                    content = chunk.choices[0].delta.content
                    reasoning_content = getattr(
                        chunk.choices[0].delta, "reasoning_content", None
                    )

                    if reasoning_content is not None and show_reasoning:
                        yield reasoning_content

                    if content is not None:
                        yield content
            else:
                # For non-streaming response
                content = completion.choices[0].message.content
                # If we have reasoning content and want to show it
                if show_reasoning and hasattr(
                    completion.choices[0].message, "reasoning_content"
                ):
                    reasoning = completion.choices[0].message.reasoning_content
                    if reasoning:
                        yield reasoning
                        yield "\n\n"
                # Then output the regular content
                yield content

            response.response_json = {"content": "".join(response._chunks)}

            # Store reasoning_content in response if available
            if not stream and hasattr(
                completion.choices[0].message, "reasoning_content"
            ):
                response.response_json["reasoning_content"] = completion.choices[
                    0
                ].message.reasoning_content

        except httpx.HTTPError as e:
            raise llm.ModelError(f"DeepSeek API error: {str(e)}")

    def _build_messages(self, conversation, prompt):
        """Build the messages list for the API call."""
        messages = []
        if conversation:
            for prev_response in conversation.responses:
                messages.append(
                    {"role": "user", "content": prev_response.prompt.prompt}
                )
                messages.append({"role": "assistant", "content": prev_response.text()})

        # Add system message if provided
        if prompt.system:
            messages.append({"role": "system", "content": prompt.system})

        messages.append({"role": "user", "content": prompt.prompt})

        if prompt.options.prefill:
            prefill_content = prompt.options.prefill
            # Check if prefill value is a file path
            if os.path.exists(prefill_content) and os.path.isfile(prefill_content):
                try:
                    with open(prefill_content, "r") as file:
                        prefill_content = file.read()
                except Exception as e:
                    print(
                        f"Warning: Could not read prefill file '{prompt.options.prefill}': {e}"
                    )

            messages.append(
                {"role": "assistant", "content": prefill_content, "prefix": True}
            )

        return messages


class DownloadError(Exception):
    pass


def fetch_cached_json(url, path, cache_timeout, headers=None):
    """Fetch JSON data from a URL and cache it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file() and time.time() - path.stat().st_mtime < cache_timeout:
        with open(path, "r") as file:
            return json.load(file)

    try:
        response = httpx.get(url, headers=headers, follow_redirects=True)
        response.raise_for_status()
        with open(path, "w") as file:
            json.dump(response.json(), file)
        return response.json()
    except httpx.HTTPError:
        if path.is_file():
            with open(path, "r") as file:
                return json.load(file)
        else:
            raise DownloadError(
                f"Failed to download data and no cache is available at {path}"
            )


@llm.hookimpl
def register_models(register):
    key = llm.get_key("", "deepseek", "LLM_DEEPSEEK_KEY")
    if not key:
        return
    try:
        models = get_deepseek_models()
        models_with_aliases = get_model_ids_with_aliases(models)

        # Register all Chat models
        for model_id, aliases in models_with_aliases:
            register(
                DeepSeekChat(
                    model_id=f"deepseek/{model_id}",
                    model_name=model_id,
                ),
                aliases=[model_id],
            )
    except DownloadError as e:
        print(f"Error fetching DeepSeek models: {e}")


@llm.hookimpl
def register_commands(cli):
    @cli.command()
    def deepseek_models():
        """List available DeepSeek models."""
        key = llm.get_key("", "deepseek", "LLM_DEEPSEEK_KEY")
        if not key:
            print("DeepSeek API key not set. Use 'llm keys set deepseek' to set it.")
            return
        try:
            models = get_deepseek_models()
            models_with_aliases = get_model_ids_with_aliases(models)

            # Display all Chat models
            for model_id, aliases in models_with_aliases:
                print(f"DeepSeek Chat: deepseek/{model_id}")
                print(f"  Aliases: {model_id}")
                print()
        except DownloadError as e:
            print(f"Error fetching DeepSeek models: {e}")
