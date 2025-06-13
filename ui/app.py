from flask import Flask, request, jsonify, render_template_string
import sys
import os

# Add the parent directory to sys.path to allow imports from the 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.orchestrator import Orchestrator

app = Flask(__name__)

# Initialize the orchestrator
# Consider making the model name configurable, e.g., via environment variable or a settings file
# Using a smaller model for the UI by default if 7B is too resource-intensive for combined UI + model operations.
# For example: "Qwen/Qwen2-1.5B-Instruct" or "Qwen/Qwen2-0.5B-Instruct"
# Ensure the machine running this has resources for the chosen model.
# If running in Docker, ensure Docker has enough resources allocated.
try:
    orchestrator = Orchestrator(model_name="Qwen/Qwen2-0.5B-Instruct") # Smaller model for UI
    model_load_error = None
except Exception as e:
    orchestrator = None
    model_load_error = str(e)
    print(f"Error initializing Orchestrator: {e}")
    print("The UI will have limited functionality.")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous AI Agent UI</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1, h2 { color: #333; }
        textarea { width: 98%; padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; min-height: 80px;}
        button { background-color: #5cb85c; color: white; padding: 10px 15px; border: none; cursor: pointer; border-radius: 4px;}
        button:hover { background-color: #4cae4c; }
        .error { color: red; font-weight: bold; }
        .response { margin-top: 20px; padding: 15px; background-color: #e9e9e9; border: 1px solid #ccc; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; }
        .project-data-section { margin-top:10px; padding:10px; border: 1px solid #eee; background: #f9f9f9; }
        .project-data-section h3 {margin-top:0;}
    </style>
</head>
<body>
    <div class="container">
        <h1>Autonomous AI Agent Interface</h1>

        {% if model_load_error %}
            <p class="error">Failed to load AI Model/Orchestrator: {{ model_load_error }}</p>
            <p class="error">Please check server logs. UI functionality will be limited.</p>
        {% endif %}

        <h2>Define Project Goal</h2>
        <form id="projectForm">
            <textarea name="project_goal" placeholder="Enter the overall goal for the AI project..."></textarea>
            <button type="submit" {% if not orchestrator %}disabled{% endif %}>Start Project Flow</button>
        </form>

        <h2>Project Status & Output</h2>
        <div id="status"></div>
        <div id="projectData" class="response">
            <!-- Project data will be displayed here -->
        </div>
    </div>

    <script>
        document.getElementById('projectForm').addEventListener('submit', async function(event) {
            event.preventDefault();
            const projectGoal = event.target.project_goal.value;
            const statusDiv = document.getElementById('status');
            const projectDataDiv = document.getElementById('projectData');

            statusDiv.innerHTML = 'Processing... please wait.';
            projectDataDiv.innerHTML = '';

            try {
                const response = await fetch('/start_project', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ project_goal: projectGoal }),
                });

                if (!response.ok) {
                    const errorResult = await response.json();
                    throw new Error(errorResult.error || `HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                statusDiv.innerHTML = 'Project flow completed.';

                // Display project data
                let htmlOutput = '<h3>Project Artifacts:</h3>';
                for (const key in result.project_data) {
                    htmlOutput += `<div class="project-data-section"><h3>${formatTitle(key)}</h3>`;
                    const value = result.project_data[key];
                    if (typeof value === 'string') {
                        htmlOutput += `<p>${escapeHtml(value)}</p>`;
                    } else if (Array.isArray(value)) {
                        htmlOutput += '<ul>';
                        value.forEach(item => {
                            htmlOutput += `<li>${escapeHtml(item)}</li>`;
                        });
                        htmlOutput += '</ul>';
                    } else if (typeof value === 'object' && value !== null) {
                        htmlOutput += '<ul>';
                        for (const subKey in value) {
                            htmlOutput += `<li><strong>${escapeHtml(subKey)}:</strong> ${escapeHtml(value[subKey])}</li>`;
                        }
                        htmlOutput += '</ul>';
                    }
                    htmlOutput += '</div>';
                }
                projectDataDiv.innerHTML = htmlOutput;

            } catch (error) {
                statusDiv.innerHTML = `<p class="error">Error: ${error.message}</p>`;
                projectDataDiv.innerHTML = '';
            }
        });

        function formatTitle(str) {
            return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }

        function escapeHtml(unsafe) {
            if (unsafe === null || typeof unsafe === 'undefined') return '';
            return unsafe
                 .toString()
                 .replace(/&/g, "&amp;")
                 .replace(/</g, "&lt;")
                 .replace(/>/g, "&gt;")
                 .replace(/"/g, "&quot;")
                 .replace(/'/g, "&#039;");
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, orchestrator=orchestrator, model_load_error=model_load_error)

@app.route('/start_project', methods=['POST'])
def start_project():
    if not orchestrator:
        return jsonify({"error": "Orchestrator not available due to model loading issues."}), 500

    data = request.get_json()
    project_goal = data.get('project_goal')

    if not project_goal:
        return jsonify({"error": "Project goal is required."}), 400

    try:
        print(f"UI: Received project goal: {project_goal}")
        # This is a blocking call. For long-running tasks, consider background jobs (e.g., Celery)
        project_summary = orchestrator.execute_project_flow(project_goal)
        print(f"UI: Project flow finished. Summary: {project_summary}")
        return jsonify({"message": "Project flow initiated successfully.", "project_data": project_summary})
    except Exception as e:
        print(f"Error during project execution via UI: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Make sure to run this from the root directory of the project, or adjust paths accordingly.
    # Example: python ui/app.py
    # The Dockerfile is set up to run this script.
    print("Starting Flask UI application...")
    print(f"Orchestrator status: {'Loaded' if orchestrator else 'Not loaded (Error: ' + model_load_error + ')'}")
    app.run(host='0.0.0.0', port=80, debug=True)
