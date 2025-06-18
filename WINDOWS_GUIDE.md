# AutoAI on Windows: Setup Guide

This guide provides step-by-step instructions for setting up and running the AutoAI project on a Windows environment.

## 1. Prerequisites

Before you begin, ensure you have the following installed and configured:

* **Docker Desktop for Windows:** Make sure it is installed and running. It should be configured to use the **WSL 2 backend** for optimal performance. You can download it from the [official Docker website](https://www.docker.com/products/docker-desktop/).
* **Git:** To clone the project repository. You can download it from [git-scm.com](https://git-scm.com/download/win).
* **PowerShell:** Windows 10 and 11 come with PowerShell pre-installed. It is recommended to use PowerShell 7+ for the best experience.

## 2. Setup and Launch

Follow these steps in your PowerShell terminal:

**Step 1: Clone the Repository**
```powershell
git clone <your-repository-url>
cd autoai
```

**Step 2: Run the Startup Script**
This single script will handle everything: it generates the necessary secrets, creates the `.env` configuration file, and starts all the application services using Docker Compose.

```powershell
.\start.ps1
```

**What the script does:**

1.  **Checks Prerequisites:** Verifies that Docker and `docker-compose` are installed and running.
2.  **Generates Secrets:** Runs the `setup-secrets.ps1` script. This creates a `secrets` directory and populates it with randomly generated passwords and keys. It also creates a `.env` file in the root directory, which `docker-compose` uses to configure the services.
3.  **Builds & Starts Containers:** Executes `docker-compose up --build -d` to build the container images (if they don't exist) and start all services (backend, frontend, database, etc.) in detached mode.

## 3\. Accessing the Application

Once the script finishes successfully:

  * **Frontend (Web UI):** Open your web browser and navigate to [http://localhost:5173](https://www.google.com/search?q=http://localhost:5173)
  * **Backend API:** The API server will be running at `http://localhost:5000`.

You should now be able to see the login page.

## 4\. Initial Login

The database is initialized with a default user for testing purposes.

  * **Username:** `admin`
  * **Password:** `password`

Use these credentials to log in for the first time. The user creation logic can be found in `backend/init.sql`.

## 5\. Troubleshooting

  * **`ExecutionPolicy` Error in PowerShell:** If you get an error about script execution being disabled, run the following command in PowerShell (as Administrator) and try again:
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
    ```
  * **Docker Errors:** If `docker-compose up` fails, check the logs for the specific service that failed:
    ```powershell
    # View logs for all services
    docker-compose logs -f

    # View logs for a specific service (e.g., backend)
    docker-compose logs -f backend
    ```
  * **Stopping the Application:** To stop all running services:
    ```powershell
    docker-compose down
    ```

<!-- end list -->
