import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.orchestrator import Orchestrator

class TestOrchestrator(unittest.TestCase):

    @patch('app.orchestrator.ProjectManagerAgent')
    @patch('app.orchestrator.ProgrammerAgent')
    @patch('app.orchestrator.TesterAgent')
    def setUp(self, MockTesterAgent, MockProgrammerAgent, MockProjectManagerAgent):
        # Mock the agent classes themselves
        self.mock_pm = MockProjectManagerAgent.return_value
        self.mock_pg = MockProgrammerAgent.return_value
        self.mock_tester = MockTesterAgent.return_value

        # Configure mock methods for each agent
        self.mock_pm.define_requirements = MagicMock(return_value="Mocked requirements")
        self.mock_pm.create_tasks = MagicMock(return_value="Task 1\nTask 2") # Tasks separated by newline

        self.mock_pg.write_code = MagicMock(return_value={"code": "Mocked code for task", "file_path": "mocked_code.py"})

        self.mock_tester.create_test_plan = MagicMock(return_value="Mocked test plan")
        self.mock_tester.execute_tests = MagicMock(return_value="Mocked test results")

        self.orchestrator = Orchestrator(model_name="mock_model_for_orchestrator")

    def test_orchestrator_initialization(self):
        print("Testing Orchestrator Initialization...")
        self.assertIsNotNone(self.orchestrator.pm)
        self.assertIsNotNone(self.orchestrator.pg)
        self.assertIsNotNone(self.orchestrator.tester)
        print("Orchestrator Initialization test PASSED.")

    def test_execute_project_flow_full(self):
        print("Testing Orchestrator Execute Project Flow (Full)...")
        project_goal = "Test Project Goal"

        project_data = self.orchestrator.execute_project_flow(project_goal)

        self.mock_pm.define_requirements.assert_called_with(project_goal)
        self.assertEqual(project_data["requirements"], "Mocked requirements")

        self.mock_pm.create_tasks.assert_called_with("Mocked requirements")
        self.assertEqual(project_data["tasks"], ["Task 1", "Task 2"])

        self.assertEqual(self.mock_pg.write_code.call_count, 2)
        self.mock_pg.write_code.assert_any_call("Task 1")
        self.mock_pg.write_code.assert_any_call("Task 2")
        self.assertIn("task_1", project_data["code"])
        # The actual value of project_data["code"]["task_1"] is the dict returned by mock_pg.write_code
        self.assertEqual(project_data["code"]["task_1"], {"code": "Mocked code for task", "file_path": "mocked_code.py"})

        self.assertEqual(self.mock_tester.create_test_plan.call_count, 2)
        self.mock_tester.create_test_plan.assert_any_call("Test cases for: Task 1 based on overall requirements: Mocked requirements")
        self.assertIn("task_1", project_data["test_plans"])

        self.assertEqual(self.mock_tester.execute_tests.call_count, 2)
        # The second argument to execute_tests in the orchestrator is the *code_output* from pg.write_code,
        # which is a dictionary: {"code": "Mocked code for task", "file_path": "mocked_code.py"}
        self.mock_tester.execute_tests.assert_any_call("Mocked test plan", {"code": "Mocked code for task", "file_path": "mocked_code.py"})
        self.assertIn("task_1", project_data["test_results"])
        print("Orchestrator Execute Project Flow (Full) test PASSED.")

    def test_execute_project_flow_no_requirements(self):
        print("Testing Orchestrator Execute Project Flow (No Requirements)...")
        self.mock_pm.define_requirements.return_value = "None" # Simulate no requirements

        project_data = self.orchestrator.execute_project_flow("Another Goal")

        self.mock_pm.define_requirements.assert_called_with("Another Goal")
        self.assertEqual(project_data["requirements"], "None")
        self.mock_pm.create_tasks.assert_not_called() # Should stop if no requirements
        print("Orchestrator Execute Project Flow (No Requirements) test PASSED.")

    def test_execute_project_flow_no_tasks(self):
        print("Testing Orchestrator Execute Project Flow (No Tasks)...")
        self.mock_pm.create_tasks.return_value = "" # Simulate no tasks created

        project_data = self.orchestrator.execute_project_flow("Goal With No Tasks")

        self.assertEqual(project_data["requirements"], "Mocked requirements")
        self.mock_pm.create_tasks.assert_called_with("Mocked requirements")
        self.assertEqual(project_data["tasks"], [])
        self.mock_pg.write_code.assert_not_called() # Should stop if no tasks
        print("Orchestrator Execute Project Flow (No Tasks) test PASSED.")


if __name__ == '__main__':
    unittest.main()
