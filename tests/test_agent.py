import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to sys.path to allow imports from the 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent import AIAgent

class TestAIAgent(unittest.TestCase):

    @patch('app.agent.AutoModelForCausalLM.from_pretrained')
    @patch('app.agent.AutoTokenizer.from_pretrained')
    def test_agent_initialization(self, mock_tokenizer, mock_model):
        print("Testing AIAgent Initialization...")
        # Mock the tokenizer and model loading
        mock_tokenizer.return_value = MagicMock()
        mock_model.return_value = MagicMock()

        try:
            agent = AIAgent(model_name="mock_model")
            self.assertIsNotNone(agent)
            self.assertIsNotNone(agent.tokenizer)
            self.assertIsNotNone(agent.model)
            mock_tokenizer.assert_called_with("mock_model")
            mock_model.assert_called_with("mock_model", torch_dtype=agent.model.dtype, device_map="auto")
            print("AIAgent Initialization test PASSED.")
        except Exception as e:
            print(f"AIAgent Initialization test FAILED: {e}")
            raise

    @patch('app.agent.AutoModelForCausalLM.from_pretrained')
    @patch('app.agent.AutoTokenizer.from_pretrained')
    def test_agent_generate_response(self, mock_tokenizer_loader, mock_model_loader):
        print("Testing AIAgent Generate Response...")
        # Setup mocks
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer_instance.return_value = {"input_ids": MagicMock()} # Mocking the tokenizer call output
        mock_tokenizer_instance.eos_token_id = 50256 # Example EOS token ID
        mock_tokenizer_instance.decode = MagicMock(return_value="Mocked response")
        mock_tokenizer_loader.return_value = mock_tokenizer_instance

        mock_model_instance = MagicMock()
        mock_model_instance.generate = MagicMock(return_value=MagicMock()) # Mocking the model's generate method
        mock_model_loader.return_value = mock_model_instance

        agent = AIAgent(model_name="mock_model")
        agent.device = 'cpu' # Force CPU for testing generate path if an error occurs with inputs.to(self.device)

        try:
            prompt = "Test prompt"
            response = agent.generate_response(prompt, max_length=10)
            self.assertEqual(response, "Mocked response")
            mock_tokenizer_instance.assert_called_with(prompt, return_tensors="pt")
            # mock_model_instance.generate.assert_called_once() # More specific assertions can be added here
            print("AIAgent Generate Response test PASSED.")
        except Exception as e:
            print(f"AIAgent Generate Response test FAILED: {e}")
            raise

if __name__ == '__main__':
    unittest.main()
