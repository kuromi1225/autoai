import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.roles import ProjectManagerAgent, ProgrammerAgent, TesterAgent

class TestAgentRoles(unittest.TestCase):

    @patch('app.roles.AIAgent.__init__') # Patch AIAgent's __init__ within roles.py
    def setUp(self, mock_agent_init):
        # Prevent actual model loading during role tests
        mock_agent_init.return_value = None

        # Mock the generate_response method for all roles indirectly via AIAgent
        # This assumes all roles will call super().generate_response or self.generate_response
        self.mock_generate_response = MagicMock(return_value="Default mock response")

        # To make self.generate_response work in each role instance:
        # We need to patch it on the AIAgent class that BaseRole inherits from.
        self.generate_patcher = patch('app.agent.AIAgent.generate_response', self.mock_generate_response)
        self.generate_patcher.start()

        self.pm = ProjectManagerAgent(model_name="mock_model")
        self.pg = ProgrammerAgent(model_name="mock_model", repo_path=".") # Add repo_path
        self.tester = TesterAgent(model_name="mock_model")

        # Ensure generate_response is mocked for each instance if they don't use super() for it
        # Or ensure the patch on AIAgent is effective.
        # If roles directly call self.generate_response inherited from AIAgent, the class patch is enough.


    def tearDown(self):
        self.generate_patcher.stop()

    def test_pm_define_requirements(self):
        print("Testing PM Define Requirements...")
        self.mock_generate_response.return_value = "PM requirements response"
        response = self.pm.define_requirements("Goal")
        self.assertEqual(response, "PM requirements response")
        self.mock_generate_response.assert_called_with("As a Project Manager, my task is to: Define detailed requirements for the project goal: Goal.. Please provide a detailed plan or action.")
        print("PM Define Requirements test PASSED.")

    def test_pg_write_code(self):
        print("Testing PG Write Code...")
        self.mock_generate_response.return_value = "```python\ndef hello():\n  print(\"Hello\")\n```"
        # Patch os.makedirs and open for file writing part of write_code
        with patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            response_data = self.pg.write_code("Create hello function", "hello.py")
            self.assertIn("def hello():", response_data.get("code", ""))
            mock_makedirs.assert_called_once()
            mock_file.assert_called_with(os.path.join(self.pg.repo_path, "hello.py"), "w")
        self.mock_generate_response.assert_called_with("As a Programmer, my task is to: Write Python code for the following task: Create hello function. Only output the code. Ensure the code is complete and runnable if possible.. Please provide a detailed plan or action.")
        print("PG Write Code test PASSED.")


    @patch('app.roles.ProgrammerAgent.run_git_command')
    def test_pg_commit_changes(self, mock_run_git):
        print("Testing PG Commit Changes...")
        mock_run_git.return_value = "Commit successful"
        # Create a dummy file to be "committed"
        dummy_file = os.path.join(self.pg.repo_path, "dummy.py")
        # Ensure the directory for the dummy file exists if repo_path is "."
        os.makedirs(os.path.dirname(dummy_file), exist_ok=True)
        with open(dummy_file, "w") as f:
            f.write("test")

        response = self.pg.commit_changes("Test commit", [dummy_file]) # Pass file path as list

        self.assertEqual(response, "Commit successful")
        # Check that git add was called for the file and then git commit
        calls = [
            unittest.mock.call(['add', dummy_file]),
            unittest.mock.call(['commit', '-m', 'Test commit'])
        ]
        mock_run_git.assert_has_calls(calls)

        os.remove(dummy_file) # Clean up dummy file
        print("PG Commit Changes test PASSED.")


    def test_tester_create_test_plan(self):
        print("Testing Tester Create Test Plan...")
        self.mock_generate_response.return_value = "Tester plan response"
        response = self.tester.create_test_plan("Requirements")
        self.assertEqual(response, "Tester plan response")
        self.mock_generate_response.assert_called_with("As a Tester, my task is to: Create a test plan for the following requirements: Requirements.. Please provide a detailed plan or action.")
        print("Tester Create Test Plan test PASSED.")

if __name__ == '__main__':
    unittest.main()
