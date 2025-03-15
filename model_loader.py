"""
Model loader for AI Assistant.
Provides interfaces to load and use different AI models.
"""
import os
import json
from typing import Dict, List, Any, Optional, Union
import importlib

class ModelInterface:
    """Base interface for AI models"""
    def __init__(self, model_config: Dict[str, Any] = None):
        self.model_config = model_config or {}
        self.model = None
        self.tokenizer = None

    def load(self) -> bool:
        """Load the model"""
        raise NotImplementedError("Subclasses must implement load()")

    def generate(self, prompt: str, max_length: int = 1000) -> str:
        """Generate text based on prompt"""
        raise NotImplementedError("Subclasses must implement generate()")


class DummyModel(ModelInterface):
    """Dummy model for testing without actual AI model dependencies"""
    def __init__(self, model_config: Dict[str, Any] = None):
        super().__init__(model_config)
        self.responses = {
            "hello": "Hello! How can I help you today?",
            "help": "I can help you access information from your files and databases.",
            "default": "I'm processing your request. In a full implementation, this would use a real language model."
        }

    def load(self) -> bool:
        """Load the dummy model"""
        print("Dummy model loaded")
        return True

    def generate(self, prompt: str, max_length: int = 1000) -> str:
        """Generate a response based on keyword matching"""
        prompt_lower = prompt.lower()

        for key, response in self.responses.items():
            if key in prompt_lower:
                return response

        return self.responses["default"]


class TransformersModel(ModelInterface):
    """Interface for Hugging Face Transformers models"""
    def __init__(self, model_config: Dict[str, Any] = None):
        super().__init__(model_config)

        self.model_name = model_config.get('model_name', 'gpt2')
        self.device = model_config.get('device', 'cpu')
        self.token_limit = model_config.get('token_limit', 1024)

    def load(self) -> bool:
        """Load transformer model"""
        try:
            # Only import if we're actually using transformers
            # This allows the app to run without these dependencies
            # if using the DummyModel or other model types
            try:
                transformers_spec = importlib.util.find_spec("transformers")
                if transformers_spec is None:
                    print("Transformers library not found. Using DummyModel instead.")
                    return False

                import transformers
                from transformers import AutoModelForCausalLM, AutoTokenizer
                import torch

                print(f"Loading model: {self.model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(self.model_name)

                # Move to GPU if available and requested
                if self.device == 'cuda' and torch.cuda.is_available():
                    self.model = self.model.to('cuda')

                return True
            except ImportError:
                print("Could not import transformers. Using DummyModel instead.")
                return False

        except Exception as e:
            print(f"Error loading model: {str(e)}")
            return False

    def generate(self, prompt: str, max_length: int = 1000) -> str:
        """Generate text using the transformer model"""
        try:
            if not self.model or not self.tokenizer:
                return "Model not loaded properly."

            # Tokenize the prompt
            inputs = self.tokenizer(prompt, return_tensors="pt")

            # Move to same device as model
            if hasattr(self.model, 'device'):
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            # Generate
            import torch
            with torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_return_sequences=1,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True
                )

            # Decode the output
            response = self.tokenizer.decode(output[0], skip_special_tokens=True)

            # Remove the original prompt
            if response.startswith(prompt):
                response = response[len(prompt):]

            return response.strip()

        except Exception as e:
            return f"Error generating response: {str(e)}"


class LangChainModel(ModelInterface):
    """Interface for LangChain integration"""
    def __init__(self, model_config: Dict[str, Any] = None):
        super().__init__(model_config)

        self.model_type = model_config.get('model_type', 'openai')
        self.model_name = model_config.get('model_name', 'gpt-3.5-turbo')
        self.api_key = model_config.get('api_key') or os.getenv(f"{self.model_type.upper()}_API_KEY")

    def load(self) -> bool:
        """Load LangChain model"""
        try:
            # Check if LangChain is available
            try:
                langchain_spec = importlib.util.find_spec("langchain")
                if langchain_spec is None:
                    print("LangChain library not found. Using DummyModel instead.")
                    return False

                # Only import when we're actually using it
                if self.model_type == 'openai':
                    from langchain.chat_models import ChatOpenAI
                    if not self.api_key:
                        print("OpenAI API key not found. Using DummyModel instead.")
                        return False

                    self.llm = ChatOpenAI(
                        model_name=self.model_name,
                        temperature=0.7,
                        openai_api_key=self.api_key
                    )
                    return True

                elif self.model_type == 'anthropic':
                    from langchain.chat_models import ChatAnthropic
                    if not self.api_key:
                        print("Anthropic API key not found. Using DummyModel instead.")
                        return False

                    self.llm = ChatAnthropic(
                        model=self.model_name,
                        temperature=0.7,
                        anthropic_api_key=self.api_key
                    )
                    return True

                else:
                    print(f"Unsupported model type: {self.model_type}")
                    return False

            except ImportError:
                print("Could not import LangChain. Using DummyModel instead.")
                return False

        except Exception as e:
            print(f"Error loading LangChain model: {str(e)}")
            return False

    def generate(self, prompt: str, max_length: int = 1000) -> str:
        """Generate text using LangChain"""
        try:
            if not hasattr(self, 'llm'):
                return "Model not loaded properly."

            # Import langchain components
            from langchain.schema import HumanMessage

            # Create a message
            message = HumanMessage(content=prompt)

            # Generate response
            response = self.llm([message])

            # Extract content
            return response.content

        except Exception as e:
            return f"Error generating response: {str(e)}"


def get_model(model_type: str = "dummy", model_config: Dict[str, Any] = None) -> ModelInterface:
    """Factory function to get the appropriate model"""
    model_config = model_config or {}

    if model_type == "dummy":
        return DummyModel(model_config)

    elif model_type == "transformers":
        return TransformersModel(model_config)

    elif model_type == "langchain":
        return LangChainModel(model_config)

    else:
        print(f"Unknown model type: {model_type}. Using DummyModel instead.")
        return DummyModel(model_config)