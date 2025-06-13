from .roles import ProjectManagerAgent, ProgrammerAgent, TesterAgent

class Orchestrator:
    def __init__(self, model_name="Qwen/Qwen2-7B-Instruct"):
        print("Initializing Orchestrator...")
        self.pm = ProjectManagerAgent(model_name=model_name)
        self.pg = ProgrammerAgent(model_name=model_name)
        self.tester = TesterAgent(model_name=model_name)
        self.project_data = {
            "requirements": None,
            "tasks": [],
            "code": {}, # Store code snippets by task
            "test_plans": {}, # Store test plans by task/feature
            "test_results": {} # Store test results
        }
        print("Orchestrator initialized with PM, PG, and Tester agents.")

    def execute_project_flow(self, project_goal):
        print(f"\n----- Starting Project Flow for: {project_goal} -----")

        # 1. PM defines requirements
        print("\n----- Phase 1: Defining Requirements -----")
        self.project_data["requirements"] = self.pm.define_requirements(project_goal)
        print(f"Orchestrator: Requirements defined: {self.project_data['requirements']}")

        if not self.project_data["requirements"] or "none" in self.project_data["requirements"].lower():
            print("Orchestrator: No requirements defined. Stopping project flow.")
            return self.project_data

        # 2. PM creates tasks
        print("\n----- Phase 2: Creating Tasks -----")
        tasks_string = self.pm.create_tasks(self.project_data["requirements"])
        # Simple parsing of tasks, assuming tasks are listed line by line
        self.project_data["tasks"] = [task.strip() for task in tasks_string.split('\n') if task.strip()]
        print(f"Orchestrator: Tasks created: {self.project_data['tasks']}")

        if not self.project_data["tasks"]:
            print("Orchestrator: No tasks created. Stopping project flow.")
            return self.project_data

        # 3. PG writes code for each task & Tester creates test plan
        print("\n----- Phase 3: Development & Test Planning -----")
        for task_idx, task_description in enumerate(self.project_data["tasks"]):
            task_id = f"task_{task_idx + 1}"
            print(f"\n--- Sub-Phase: Coding for Task: {task_description} ---")
            code_output = self.pg.write_code(task_description)
            self.project_data["code"][task_id] = code_output
            print(f"Orchestrator: Code for '{task_description}':\n{code_output}")

            print(f"\n--- Sub-Phase: Test Planning for Task: {task_description} ---")
            # For simplicity, test plan is based on the task description. Could also be based on requirements snippet.
            test_plan = self.tester.create_test_plan(f"Test cases for: {task_description} based on overall requirements: {self.project_data['requirements']}")
            self.project_data["test_plans"][task_id] = test_plan
            print(f"Orchestrator: Test plan for '{task_description}':\n{test_plan}")

        # 4. Tester "executes" tests for each task's code
        # This is still conceptual. Real execution would need a proper environment.
        print("\n----- Phase 4: Testing -----")
        for task_id, code_to_test in self.project_data["code"].items():
            task_description = self.project_data["tasks"][int(task_id.split('_')[1]) -1] # Retrieve task description
            print(f"\n--- Sub-Phase: Testing code for task: {task_description} ---")
            test_plan = self.project_data["test_plans"].get(task_id, "No test plan available.")
            if code_to_test and "none" not in code_to_test.lower():
                test_results = self.tester.execute_tests(test_plan, code_to_test)
                self.project_data["test_results"][task_id] = test_results
                print(f"Orchestrator: Test results for '{task_description}':\n{test_results}")
            else:
                print(f"Orchestrator: No code available to test for '{task_description}'. Skipping testing.")
                self.project_data["test_results"][task_id] = "Skipped - No code provided."


        print("\n----- Project Flow Completed -----")
        return self.project_data

if __name__ == '__main__':
    print("Starting Orchestrator test...")
    # You might need to download a smaller model like Qwen/Qwen2-1.5B-Instruct or Qwen/Qwen2-0.5B-Instruct
    # if Qwen/Qwen2-7B-Instruct is too large for your local setup without significant GPU resources.
    # Ensure you are logged in to Hugging Face CLI if the model is gated or requires authentication.
    # `huggingface-cli login`
    try:
        # Using a smaller model for local testing feasibility if full 7B is too heavy
        # orchestrator = Orchestrator(model_name="Qwen/Qwen2-1.5B-Instruct")
        orchestrator = Orchestrator() # Default is Qwen2-7B-Instruct
        project_goal_orc = "Create a Python script that sorts a list of numbers and writes it to a file."
        final_project_data = orchestrator.execute_project_flow(project_goal_orc)

        print("\n----- Final Project Data -----")
        for key, value in final_project_data.items():
            print(f"\n{key.replace('_', ' ').title()}:")
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            elif isinstance(value, list):
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"  {value}")

    except Exception as e:
        print(f"An error occurred during orchestrator test: {e}")
        print("Make sure you have enough resources (RAM/VRAM) for the selected model.")
        print("If you are using a large model like Qwen2-7B, ensure you have a suitable GPU and CUDA installed.")
        print("Try using a smaller model variant (e.g., Qwen2-0.5B-Instruct or Qwen2-1.5B-Instruct) for testing if issues persist.")
