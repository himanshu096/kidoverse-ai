# KidoVerse AI - Kido

A real-time multimodal AI agent powered by Gemini Live API, supporting audio interactions with tool calling capabilities and a modern React frontend.

Agent generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) version `0.5.2`

![live_api_diagram](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/live_api_diagram.png)

## Project Structure

This project is organized as follows:

```
kidoverse-ai/
├── app/                 # Core Python backend application
│   ├── agent.py         # Main agent logic with tool calling
│   ├── server.py        # FastAPI backend server with WebSocket support
│   ├── models.py        # Data models and schema definitions
│   └── prompts.py       # Agent prompts and instructions
├── frontend/            # React-based multimodal web interface
│   ├── src/             # React source code
│   │   ├── components/  # UI components (agent display, controls, etc.)
│   │   ├── contexts/    # React contexts (Auth, Live API)
│   │   ├── hooks/       # Custom React hooks
│   │   └── utils/       # Frontend utilities and API clients
│   ├── public/          # Static assets and animations
│   ├── package.json     # Frontend dependencies
│   └── README.md        # Frontend deployment guide
├── deployment/          # Infrastructure and deployment configuration
│   ├── terraform/       # Terraform infrastructure as code
│   ├── ci/              # Continuous integration configs
│   └── cd/              # Continuous deployment configs
├── tests/               # Test suites
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── load_test/       # Load testing scripts
├── Dockerfile           # Container configuration
├── firebase.json        # Firebase hosting configuration
├── Makefile             # Development and deployment commands
└── pyproject.toml       # Python project dependencies and configuration
```

## Key Features

**Python Backend** (in `app/` folder):
- **Real-time bidirectional communication** via WebSockets with Gemini Live API
- **Integrated tool calling** with custom tools for enhanced agent capabilities
- **Production-grade reliability** with retry logic and automatic reconnection
- **Deployment flexibility** supporting both AI Studio and Vertex AI endpoints
- **FastAPI server** with comprehensive logging and monitoring

**React Frontend** (in `frontend/` folder):
- **Multimodal interface** supporting audio, video, and text interactions
- **Real-time agent display** with visual feedback and animations
- **Authentication system** with Google OAuth integration
- **Modern UI components** with responsive design
- **WebSocket integration** for seamless backend communication

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager - [Install](https://docs.astral.sh/uv/getting-started/installation/)
- **Node.js & npm**: For frontend development - [Install](https://nodejs.org/)
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)
- **Terraform**: For infrastructure deployment - [Install](https://developer.hashicorp.com/terraform/downloads)
- **make**: Build automation tool - [Install](https://www.gnu.org/software/make/) (pre-installed on most Unix-based systems)

## Google Authentication Setup

### Required Google Cloud Services

Enable the following APIs in your Google Cloud Project:

```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
```

### Google OAuth Configuration

For the frontend authentication system, you'll need to set up Google OAuth:

1. **Create OAuth 2.0 Credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Add your authorized origins (e.g., `http://localhost:8501`, your Firebase hosting URL)

2. **Configure Environment Variables:**
   
   For **local development**, create a `.env` file in your project root:
   ```bash
   # Google Cloud Configuration
   GOOGLE_CLOUD_PROJECT=your-project-id
   VERTEXAI=true
   VERTEXAI_LOCATION=us-central1
   
   # OAuth Configuration (for frontend)
   REACT_APP_GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com
   
   # Optional: Use AI Studio instead of Vertex AI
   # VERTEXAI=false
   # GOOGLE_API_KEY=your-google-ai-studio-api-key
   ```

   **Frontend Environment Setup:**
   
   Copy the example environment file and update it with your credentials:
   ```bash
   # Copy the example file
   cp frontend/.env.example frontend/.env
   
   # Edit the file with your actual values
   # frontend/.env should contain:
   # REACT_APP_WEBSOCKET_URL=ws://localhost:8000/ws
   # REACT_APP_GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
   ```

3. **Firebase Project Setup:**
   - Create a Firebase project at [Firebase Console](https://console.firebase.google.com/)
   - Enable Authentication and choose Google as a sign-in provider
   - Add your OAuth client ID to Firebase Authentication settings

### Service Account Authentication

For **production deployment**, ensure your Cloud Run service has proper permissions:

```bash
# Grant necessary roles to your Cloud Run service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

For detailed OAuth setup instructions, see [`frontend/GOOGLE_OAUTH_SETUP.md`](frontend/GOOGLE_OAUTH_SETUP.md).

## Quick Start (Local Development)

Install required packages and launch the local development environment:

```bash
make install && make playground
```

This will start both the backend server and React frontend simultaneously.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `make install`       | Install all required dependencies (Python and Node.js packages)                           |
| `make playground`    | Launch local development environment with backend and frontend                              |
| `make backend`       | Deploy agent to Cloud Run                                                                  |
| `make local-backend` | Launch local development server only                                                       |
| `make ui`            | Launch React frontend only                                                                 |
| `make test`          | Run unit and integration tests                                                             |
| `make lint`          | Run code quality checks (codespell, ruff, mypy)                                           |
| `make setup-dev-env` | Set up development environment resources using Terraform                                   |
| `uv run jupyter lab` | Launch Jupyter notebook                                                                    |

For full command options and usage, refer to the [Makefile](Makefile).

## Usage

This template follows a "bring your own agent" approach - you focus on your business logic in `app/agent.py`, and the template handles the surrounding components (UI, infrastructure, deployment, monitoring).

Here's the recommended workflow for local development:

1.  **Install Dependencies:**
    ```bash
    make install
    ```

2.  **Start the Full Development Environment:**
    ```bash
    make playground
    ```
    This starts both the backend (port 8000) and frontend (port 8501) simultaneously.

    **Or start components separately:**

    **Backend Server:**
    ```bash
    make local-backend
    ```
    Wait for `INFO: Application startup complete.` before starting the frontend.

    **Frontend UI (in another terminal):**
    ```bash
    make ui
    ```

<details>
<summary><b>Optional: Use AI Studio / API Key instead of Vertex AI</b></summary>

By default, the backend uses Vertex AI and Application Default Credentials. If you prefer to use Google AI Studio and an API key:

```bash
export VERTEXAI=false
export GOOGLE_API_KEY="your-google-api-key" # Replace with your actual key
make local-backend
```
Ensure `GOOGLE_API_KEY` is set correctly in your environment.
</details>

3.  **Interact with the Agent:**
    - Open the React UI in your browser (usually `http://localhost:8501`)
    - Click the play button in the UI to connect to the backend
    - Try multimodal interactions: voice, video, or text
    - Test tool calling with prompts like: *"What's the weather in San Francisco?"*
    - Modify agent logic in `app/agent.py` - the server auto-reloads on changes

<details>
<summary><b>Cloud Shell Usage</b></summary>

To run the agent using Google Cloud Shell:

1.  **Start the Frontend:**
    In a Cloud Shell tab, run:
    ```bash
    make ui
    ```
    Accept prompts to use a different port if 8501 is busy. Click the `localhost:PORT` link for the web preview.

2.  **Start the Backend:**
    Open a *new* Cloud Shell tab. Set your project: `gcloud config set project [PROJECT_ID]`. Then run:
    ```bash
    make local-backend
    ```

3.  **Configure Backend Web Preview:**
    Use the Cloud Shell Web Preview feature to expose port 8000. Change the default port from 8080 to 8000. See [Cloud Shell Web Preview documentation](https://cloud.google.com/shell/docs/using-web-preview#preview_the_application).

4.  **Connect Frontend to Backend:**
    - Copy the URL generated by the backend web preview (e.g., `https://8000-cs-....cloudshell.dev/`)
    - Paste this URL into the "Server URL" field in the frontend UI settings
    - Click the "Play button" to connect

*Note:* The feedback feature in the frontend might not work reliably in Cloud Shell due to cross-origin issues between the preview URLs.
</details>

## Deployment

> **Note:** For a streamlined one-command deployment of the entire CI/CD pipeline and infrastructure using Terraform, you can use the [`agent-starter-pack setup-cicd` CLI command](https://googlecloudplatform.github.io/agent-starter-pack/cli/setup_cicd.html). Currently only supporting Github.

### Dev Environment

Deploy to a development environment:

```bash
gcloud config set project <your-dev-project-id>
make backend
```

**Accessing the Deployed Backend Locally:**

To connect your local frontend (`make ui`) to the backend deployed on Cloud Run, use the `gcloud` proxy:

1.  **Start the proxy:**
    ```bash
    # Replace with your actual service name, project, and region
    gcloud run services proxy my-awesome-agent --port 8000 --project $PROJECT_ID --region us-central1
    ```
    Keep this terminal running.

2.  **Connect Frontend:** Your deployed backend is now accessible locally at `http://localhost:8000`. Point your React UI to this address.

### Frontend Deployment

The frontend can be deployed to Firebase Hosting. See [frontend/README.md](frontend/README.md) for detailed deployment instructions.

### Production Deployment

The repository includes a Terraform configuration for production deployment. Refer to [deployment/README.md](deployment/README.md) for detailed instructions on infrastructure setup and application deployment.

## Additional Resources

Explore these resources to learn more about the Multimodal Live API:

- [Project Pastra](https://github.com/heiko-hotz/gemini-multimodal-live-dev-guide/tree/main): A comprehensive developer guide for the Gemini Multimodal Live API
- [Google Cloud Multimodal Live API demos and samples](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/multimodal-live-api): Collection of code samples and demo applications
- [Gemini 2 Cookbook](https://github.com/google-gemini/cookbook/tree/main/gemini-2): Practical examples and tutorials for working with Gemini 2
- [Multimodal Live API Web Console](https://github.com/google-gemini/multimodal-live-api-web-console): Interactive React-based web interface for testing the API

![live api demo](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/live_api_pattern_demo.gif)


