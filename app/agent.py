from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

class AIAgent:
    def __init__(self, model_name="Qwen/Qwen2-7B-Instruct"):
        print(f"Initializing agent with model: {model_name}")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        print("Tokenizer loaded.")

        # Specify dtype for model loading, bfloat16 for mixed precision if supported and desired
        # For CPU or if bfloat16 is not supported, float32 will be used by default.
        model_dtype = torch.bfloat16 if self.device.type == 'cuda' else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=model_dtype,
            device_map="auto" # Automatically distribute model layers across available devices (CPU/GPU)
        )
        print("Model loaded.")
        self.model.eval()  # Set the model to evaluation mode

    def generate_response(self, prompt, max_length=500, temperature=0.7):
        print(f"Generating response for prompt: '{prompt}'")
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        # Generate text
        with torch.no_grad(): # Ensure no gradients are calculated during inference
            generation_output = self.model.generate(
                inputs.input_ids,
                max_length=max_length,
                temperature=temperature,
                pad_token_id=self.tokenizer.eos_token_id, # Set pad_token_id to eos_token_id for open-ended generation
                do_sample=True, # Enable sampling for more diverse responses
                top_k=50, # Consider the top 50 tokens for sampling
                top_p=0.95  # Use nucleus sampling with p=0.95
            )

        response_ids = generation_output[0]
        response_text = self.tokenizer.decode(response_ids, skip_special_tokens=True)
        print(f"Generated response: '{response_text}'")
        return response_text

if __name__ == '__main__':
    # This is a basic test of the agent
    print("Starting AI Agent test...")
    try:
        agent = AIAgent()
        test_prompt = "Hello, who are you?"
        print(f"Sending test prompt: '{test_prompt}'")
        response = agent.generate_response(test_prompt)
        print(f"Received response: {response}")
    except Exception as e:
        print(f"An error occurred during agent test: {e}")
