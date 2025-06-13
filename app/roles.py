from .agent import AIAgent
import subprocess
import os

class BaseRole(AIAgent):
    def __init__(self, model_name="Qwen/Qwen2-7B-Instruct", role_name="BaseRole"):
        super().__init__(model_name)
        self.role_name = role_name
        print(f"{self.role_name} initialized.")

    def perform_task(self, task_description):
        prompt = f"As a {self.role_name}, my task is to: {task_description}. Please provide a detailed plan or action."
        print(f"{self.role_name} is performing task: {task_description}")
        response = self.generate_response(prompt)
        print(f"{self.role_name} response: {response}")
        return response

class ProjectManagerAgent(BaseRole):
    def __init__(self, model_name="Qwen/Qwen2-7B-Instruct"):
        super().__init__(model_name, role_name="Project Manager")

    def define_requirements(self, project_goal):
        task_description = f"Define detailed requirements for the project goal: {project_goal}."
        return self.perform_task(task_description)

    def create_tasks(self, project_requirements):
        task_description = f"Based on the requirements: '{project_requirements}', create a list of development tasks."
        return self.perform_task(task_description)

class ProgrammerAgent(BaseRole):
    def __init__(self, model_name="Qwen/Qwen2-7B-Instruct", repo_path="."):
        super().__init__(model_name, role_name="Programmer")
        self.repo_path = os.path.abspath(repo_path)
        print(f"Programmer agent initialized for repository: {self.repo_path}")
        # Ensure the repo path exists, or initialize a new repo if specified
        if not os.path.exists(self.repo_path) or not os.path.isdir(os.path.join(self.repo_path, '.git')):
             print(f"Warning: Git repository not found at {self.repo_path}. Some Git operations may fail or need init.")
             # One might choose to automatically init a repo here, but it's safer to require it to exist.
             # self.run_git_command(["init"])

    def run_git_command(self, command_list):
        base_command = ["git"]
        # Ensure commands run within the specified repository directory
        # However, some commands like clone don't run inside an existing repo path.
        # For simplicity, this example assumes most commands are run from within the repo.

        full_command = base_command + command_list
        print(f"Executing Git command: {' '.join(full_command)} in {self.repo_path}")
        try:
            # For commands like 'clone', the cwd should be parent of repo_path, or repo_path itself might not exist yet.
            # This logic needs to be more nuanced for a real-world application.
            # For now, we assume self.repo_path is an initialized git repo.
            process = subprocess.Popen(full_command, cwd=self.repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=60) # Added timeout
            if process.returncode == 0:
                print(f"Git command successful. Output:\n{stdout}")
                return stdout
            else:
                print(f"Git command failed. Error:\n{stderr}")
                return f"Error: {stderr}"
        except subprocess.TimeoutExpired:
            print("Git command timed out.")
            process.kill()
            return "Error: Git command timed out."
        except Exception as e:
            print(f"An exception occurred while running git command: {e}")
            return f"Error: {str(e)}"

    def write_code(self, task_description, file_path="generated_code.py"):
        task_prompt = f"Write Python code for the following task: {task_description}. Only output the code. Ensure the code is complete and runnable if possible."
        generated_code = self.perform_task(task_prompt) # perform_task is from BaseRole

        # Clean up the generated code (model might add explanations)
        # This is a simplistic way; more robust parsing might be needed.
        if "```python" in generated_code:
            generated_code = generated_code.split("```python\n")[1].split("```")[0]
        elif "```" in generated_code: # handles cases where just ``` is used
             generated_code = generated_code.split("```\n")[1].split("```")[0]


        # Write the code to the specified file path within the repo
        full_file_path = os.path.join(self.repo_path, file_path)
        try:
            os.makedirs(os.path.dirname(full_file_path), exist_ok=True) # Ensure directory exists
            with open(full_file_path, "w") as f:
                f.write(generated_code)
            print(f"Code successfully written to {full_file_path}")
            return {"file_path": full_file_path, "code": generated_code}
        except Exception as e:
            print(f"Error writing code to file {full_file_path}: {e}")
            return {"file_path": full_file_path, "error": str(e)}

    def commit_changes(self, commit_message, file_paths=None):
        if file_paths:
            for file_path in file_paths:
                # Ensure file_path is relative to repo_root for add command, or absolute
                abs_path = os.path.join(self.repo_path, file_path)
                if not os.path.exists(abs_path):
                    print(f"File {abs_path} not found for git add. Skipping.")
                    continue
                self.run_git_command(["add", file_path])
        else:
            # If no specific files, attempt to add all changes
             print("No specific files provided for commit. Staging all changes in the repository.")
             self.run_git_command(["add", "."]) # Stages all changes in cwd (repo_path)

        return self.run_git_command(["commit", "-m", commit_message])

    def push_changes(self, remote_name="origin", branch_name="main"): # Changed default to main
        return self.run_git_command(["push", remote_name, branch_name])

    def create_pull_request(self, title, body, head_branch, base_branch="main"):
        # Creating pull requests programmatically usually requires interacting with a Git hosting service's API (GitHub, GitLab, etc.)
        # This is a placeholder for that functionality.
        # For GitHub, you might use the `gh` CLI tool.
        # Example: gh pr create --title "My PR" --body "This is the body" --head "feature-branch" --base "main"
        pr_command = [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--head", head_branch,
            "--base", base_branch
        ]
        print(f"Attempting to create pull request: {title} from {head_branch} to {base_branch}")
        # Ensure 'gh' CLI is installed and configured.
        result = self.run_git_command(pr_command)
        if "Error:" not in result and ("pull request" in result.lower() or "pr create" in result.lower()): # check if 'gh' command output indicates success
            print("Pull request creation command executed. Check output for URL or errors.")
        else:
            print("Pull request creation might have failed or 'gh' CLI is not available/configured.")
            print("Manual PR creation might be needed. Command output:", result)
        return result

    def fix_bugs(self, bug_description, code_context, file_path=None):
        task_prompt = f"Fix the bug described as '{bug_description}' in the following code context: \n{code_context}\n. Only output the corrected code."
        corrected_code = self.perform_task(task_prompt)

        if "```python" in corrected_code:
            corrected_code = corrected_code.split("```python\n")[1].split("```")[0]
        elif "```" in corrected_code:
             corrected_code = corrected_code.split("```\n")[1].split("```")[0]

        if file_path:
            full_file_path = os.path.join(self.repo_path, file_path)
            try:
                with open(full_file_path, "w") as f:
                    f.write(corrected_code)
                print(f"Corrected code written to {full_file_path}")
                return {"file_path": full_file_path, "code": corrected_code, "status": "success"}
            except Exception as e:
                print(f"Error writing corrected code to file {full_file_path}: {e}")
                return {"file_path": full_file_path, "error": str(e), "status": "failed"}
        else:
            # If no file_path, just return the code for review or manual application
            return {"code": corrected_code, "status": "success_no_write"}

class TesterAgent(BaseRole):
    def __init__(self, model_name="Qwen/Qwen2-7B-Instruct"):
        super().__init__(model_name, role_name="Tester")

    def create_test_plan(self, requirements):
        task_description = f"Create a test plan for the following requirements: {requirements}."
        return self.perform_task(task_description)

    def execute_tests(self, test_plan, code_to_test):
        # This is a conceptual representation. Actual test execution would require a test runner, environment, etc.
        task_description = f"Given the test plan: '{test_plan}', and the code: \n{code_to_test}\n. Describe the test execution and expected outcomes."
        # In a more advanced system, this might involve actually running code and parsing results.
        return self.perform_task(task_description)

# Update the __main__ test block in app/roles.py if needed,
# or test Git operations separately.
# For example, to test ProgrammerAgent with Git:
if __name__ == '__main__':
    print("Testing AI Agent Roles (with Git capabilities for Programmer)...")

    # Initialize a temporary directory for testing Git operations
    test_repo_dir = "temp_test_repo"
    if not os.path.exists(test_repo_dir):
        os.makedirs(test_repo_dir)

    # Initialize a git repo in the temp directory
    try:
        subprocess.run(["git", "init"], cwd=test_repo_dir, check=True, capture_output=True, text=True)
        # Create an initial commit so branches can be made, etc.
        with open(os.path.join(test_repo_dir, "initial.txt"), "w") as f:
            f.write("initial content")
        subprocess.run(["git", "add", "initial.txt"], cwd=test_repo_dir, check=True)
        # Configure dummy user for local commits
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=test_repo_dir, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=test_repo_dir, check=True) # Ensure default branch is main
    except Exception as e:
        print(f"Error initializing test git repo: {e}")
        # exit() # Exit if repo setup fails, as subsequent tests will fail

    print(f"Test Git repository initialized at ./{test_repo_dir}")

    # Test Programmer
    # Using a smaller model for local testing feasibility if full 7B is too heavy
    # pg = ProgrammerAgent(model_name="Qwen/Qwen2-0.5B-Instruct", repo_path=test_repo_dir)
    pg = ProgrammerAgent(repo_path=test_repo_dir) # Default model Qwen2-7B-Instruct

    coding_task_pg = "Create a Python function that calculates the factorial of a number."
    file_to_create = "math_utils.py"
    print(f"\nPG writing code for: '{coding_task_pg}' into file '{file_to_create}'")
    code_writing_result = pg.write_code(coding_task_pg, file_path=file_to_create)
    print(f"PG code writing result: {code_writing_result}")

    if "error" not in code_writing_result:
        print(f"\nPG committing changes for file: {file_to_create}")
        commit_result = pg.commit_changes(f"Add factorial function in {file_to_create}", [file_to_create])
        print(f"PG commit result: {commit_result}")

        # Note: Pushing and creating PRs require a remote repository and credentials.
        # These will likely fail or do nothing in a local-only test without further setup.
        # print("\nPG attempting to push changes (mock)...")
        # push_result = pg.push_changes(remote_name="origin", branch_name="main") # or current branch
        # print(f"PG push result: {push_result}")

        # print("\nPG attempting to create a pull request (mock)...")
        # pr_result = pg.create_pull_request(
        #     title="Add awesome factorial feature",
        #     body="This PR includes the new factorial function.",
        #     head_branch="main", # Assuming changes are on main or a feature branch
        #     base_branch="main"
        # )
        # print(f"PG PR creation result: {pr_result}")
    else:
        print("Skipping Git commit/push/PR due to error in code writing.")

    # Cleanup the temporary test repository (optional)
    # import shutil
    # print(f"\nCleaning up test repository: {test_repo_dir}")
    # shutil.rmtree(test_repo_dir)

    print("\nProgrammer Agent Git tests complete.")

    # ... (rest of the previous __main__ test block for PM and Tester can be here if desired)
    # For brevity, focusing on PG Git tests here.
    # Remember to re-add PM and Tester tests if you remove them for focused testing.
    print("Testing other AI Agent Roles (PM, Tester)...")
    pm = ProjectManagerAgent() # Add model_name if using smaller model
    project_goal_pm = "Develop a simple file hashing utility."
    requirements_pm = pm.define_requirements(project_goal_pm)
    tasks_pm = pm.create_tasks(requirements_pm)
    print(f"PM tasks: {tasks_pm}")

    tester = TesterAgent() # Add model_name if using smaller model
    test_requirements_tester = "The utility must hash files using SHA256."
    test_plan_tester = tester.create_test_plan(test_requirements_tester)
    print(f"Tester plan: {test_plan_tester}")

    print("\nFull AI Agent Roles test complete.")
