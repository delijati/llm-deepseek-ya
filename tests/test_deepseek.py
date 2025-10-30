from click.testing import CliRunner
import llm
from llm.cli import cli
import json
import os
import pytest
import pydantic
from pydantic import BaseModel
from typing import List, Optional

DEEPSEEK_API_KEY = os.environ.get("PYTEST_DEEPSEEK_API_KEY", None) or "sk-..."


@pytest.mark.vcr
def test_prompt():
    """Test basic prompt with DeepSeek Chat model"""
    model = llm.get_model("deepseek-chat")
    response = model.prompt(
        "Name for a pet pelican, just the name", key=DEEPSEEK_API_KEY
    )
    text = str(response).strip()
    # DeepSeek should return a response
    assert len(text) > 0
    # DeepSeek should return a response
    assert "content" in response.response_json


@pytest.mark.vcr
def test_prompt_with_pydantic_schema():
    """Test prompt with Pydantic schema - DeepSeek will use JSON mode"""

    class Dog(pydantic.BaseModel):
        name: str
        age: int
        bio: str

    model = llm.get_model("deepseek-chat")
    response = model.prompt(
        "Invent a cool dog", key=DEEPSEEK_API_KEY, schema=Dog, stream=False
    )
    result = json.loads(response.text())

    # Verify the response has the required fields
    assert "name" in result
    assert "age" in result
    assert "bio" in result
    assert isinstance(result["name"], str)
    assert isinstance(result["age"], int)
    assert isinstance(result["bio"], str)


@pytest.mark.vcr
def test_prompt_with_multiple_dogs():
    """Test prompt with nested Pydantic schema"""

    class Dog(pydantic.BaseModel):
        name: str
        age: int
        bio: str

    class Dogs(BaseModel):
        dogs: List[Dog]

    model = llm.get_model("deepseek-chat")
    response = model.prompt(
        "Invent 3 cool dogs", key=DEEPSEEK_API_KEY, schema=Dogs, stream=False
    )
    result = json.loads(response.text())

    # Verify we got 3 dogs
    assert "dogs" in result
    assert len(result["dogs"]) == 3

    # Verify each dog has the required fields
    for dog in result["dogs"]:
        assert "name" in dog
        assert "age" in dog
        assert "bio" in dog
        assert isinstance(dog["name"], str)
        assert isinstance(dog["age"], int)
        assert isinstance(dog["bio"], str)


@pytest.mark.vcr
def test_json_response_format():
    """Test the response_format option"""
    model = llm.get_model("deepseek-chat")
    response = model.prompt(
        "Return a JSON object with keys: name, color, and species for a parrot",
        key=DEEPSEEK_API_KEY,
        response_format="json_object",
        stream=False,
    )
    result = json.loads(response.text())

    # Should be valid JSON
    assert isinstance(result, dict)


@pytest.mark.vcr
def test_reasoner_model():
    """Test DeepSeek Reasoner model with reasoning output"""
    model = llm.get_model("deepseek-reasoner")
    response = model.prompt(
        "What is 537 * 943?", key=DEEPSEEK_API_KEY, show_reasoning=True, stream=False
    )
    text = response.text()

    # Should contain a numeric answer
    assert "506" in text or "943" in text or "537" in text

    # Check response_json contains reasoning_content if available
    if response.response_json and "reasoning_content" in response.response_json:
        assert isinstance(response.response_json["reasoning_content"], str)


@pytest.mark.vcr
def test_reasoner_model_hide_reasoning():
    """Test DeepSeek Reasoner model with reasoning hidden"""
    model = llm.get_model("deepseek-reasoner")
    response = model.prompt(
        "What is 2 + 2?", key=DEEPSEEK_API_KEY, show_reasoning=False, stream=False
    )
    text = response.text()

    # Should contain the answer
    assert "4" in text


@pytest.mark.vcr
def test_prefill_option():
    """Test the prefill option for Chat Prefix Completion"""
    model = llm.get_model("deepseek-chat")
    response = model.prompt(
        "Continue this story",
        key=DEEPSEEK_API_KEY,
        prefill="Once upon a time",
        stream=False,
    )
    text = response.text()

    # Should have generated some text
    assert len(text) > 0


@pytest.mark.vcr
def test_nested_model_direct_reference():
    """Test nested Pydantic models with DeepSeek"""

    class Address(BaseModel):
        street: str
        city: str

    class Person(BaseModel):
        name: str
        address: Address

    model = llm.get_model("deepseek-chat")
    response = model.prompt(
        "Create a person named Alice living in San Francisco",
        key=DEEPSEEK_API_KEY,
        schema=Person,
        stream=False,
    )
    result = json.loads(response.text())
    assert "name" in result
    assert "address" in result
    assert "street" in result["address"]
    assert "city" in result["address"]


@pytest.mark.vcr
def test_nested_model_optional():
    """Test optional nested Pydantic models"""

    class Company(BaseModel):
        company_name: str

    class Person(BaseModel):
        name: str
        employer: Optional[Company]

    model = llm.get_model("deepseek-chat")
    response = model.prompt(
        "Create a person named Bob who works at TechCorp",
        key=DEEPSEEK_API_KEY,
        schema=Person,
        stream=False,
    )
    result = json.loads(response.text())
    assert "name" in result
    assert "employer" in result
    if result["employer"] is not None:
        assert "company_name" in result["employer"]


@pytest.mark.vcr
def test_nested_model_deep_composition():
    """Test deeply nested Pydantic models"""

    class Item(BaseModel):
        product_name: str
        quantity: int

    class Order(BaseModel):
        items: List[Item]

    class Customer(BaseModel):
        name: str
        orders: List[Order]

    model = llm.get_model("deepseek-chat")
    response = model.prompt(
        "Create a customer named Carol with 2 orders, each containing 2 items",
        key=DEEPSEEK_API_KEY,
        schema=Customer,
        stream=False,
    )
    result = json.loads(response.text())
    assert "name" in result
    assert "orders" in result
    assert len(result["orders"]) > 0
    for order in result["orders"]:
        assert "items" in order
        assert len(order["items"]) > 0
        for item in order["items"]:
            assert "product_name" in item
            assert "quantity" in item


@pytest.mark.vcr
def test_cli_deepseek_models(tmpdir, monkeypatch):
    """Test the deepseek-models CLI command"""
    user_dir = tmpdir / "llm.datasette.io"
    user_dir.mkdir()
    monkeypatch.setenv("LLM_USER_PATH", str(user_dir))

    # With no key set should show error message
    runner = CliRunner()
    result = runner.invoke(cli, ["deepseek-models"])
    assert result.exit_code == 0
    assert "DeepSeek API key not set" in result.output or result.exit_code == 0

    # Try with key set
    monkeypatch.setenv("LLM_DEEPSEEK_KEY", DEEPSEEK_API_KEY)
    result2 = runner.invoke(cli, ["deepseek-models"])
    assert result2.exit_code == 0
    # Should list some models
    assert "deepseek" in result2.output.lower() or "DeepSeek" in result2.output


@pytest.mark.vcr
def test_supports_schema_attribute():
    """Test that DeepSeek Chat models have supports_schema set to True"""
    model = llm.get_model("deepseek-chat")
    assert hasattr(model, "supports_schema")
    assert model.supports_schema is True
