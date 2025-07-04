# Deployment README.md

This folder contains the infrastructure-as-code and CI/CD pipeline configurations for deploying the **Multimodal Live AI Tutoring Agent** on Google Cloud.

The application is an educational platform that leverages [**Terraform**](http://terraform.io) to define and provision the underlying infrastructure, while [**Cloud Build**](https://cloud.google.com/build/) orchestrates the continuous integration and continuous deployment (CI/CD) pipeline.

## Application Overview

This deployment supports a comprehensive AI tutoring system featuring:
- **Real-time multimodal interactions** (audio, video, text) via Gemini Live API
- **Intelligent lesson planning and delivery** with structured educational content
- **Image generation capabilities** using Imagen for educational illustrations
- **Persistent learning state management** with Firestore integration
- **React-based frontend** with educational UI components and authentication
- **FastAPI backend** with WebSocket support for real-time communication


**Description:**

1. CI Pipeline (`deployment/ci/pr_checks.yaml`):

   - Triggered on pull request creation/update
   - Runs unit and integration tests
   - Validates educational agent functionality

2. CD Pipeline (`deployment/cd/staging.yaml`):

   - Triggered on merge to `main` branch
   - Builds and pushes application to Artifact Registry
   - Deploys to staging environment for educational testing
   - Performs load testing to ensure scalability for classroom use

3. Production Deployment (`deployment/cd/deploy-to-prod.yaml`):
   - Triggered after successful staging deployment
   - Requires manual approval for production educational environment
   - Deploys to production environment with full tutoring capabilities

## Setup

> **Note:** For a streamlined one-command deployment of the entire CI/CD pipeline and infrastructure using Terraform, you can use the [`uvx agent-starter-pack setup-cicd` CLI command](https://googlecloudplatform.github.io/agent-starter-pack/cli/setup_cicd.html). Currently only supporting Github.

**Prerequisites:**

1. A set of Google Cloud projects:
   - Staging project (for educational testing)
   - Production project (for live tutoring environment)
   - CI/CD project (can be the same as staging or production)
2. Terraform installed on your local machine
3. Enable required APIs in the CI/CD project. This will be required for the Terraform deployment:

   ```bash
   gcloud config set project $YOUR_CI_CD_PROJECT_ID
   gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
   ```

4. **Additional APIs for AI Tutoring Features:**
   ```bash
   # Enable APIs for the AI tutoring capabilities
   gcloud services enable aiplatform.googleapis.com firestore.googleapis.com run.googleapis.com artifactregistry.googleapis.com
   ```

## Step-by-Step Guide

1. **Create a Git Repository using your favorite Git provider (GitHub, GitLab, Bitbucket, etc.)**

2. **Connect Your Repository to Cloud Build**
   For detailed instructions, visit: [Cloud Build Repository Setup](https://cloud.google.com/build/docs/repositories#whats_next).<br>

   ![Alt text](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/connection_cb.gif)

3. **Configure Terraform Variables**

   - Edit [`deployment/terraform/vars/env.tfvars`](../terraform/vars/env.tfvars) with your Google Cloud settings.

   | Variable               | Description                                                     | Required |
   | ---------------------- | --------------------------------------------------------------- | :------: |
   | project_name           | Project name used as a base for resource naming (e.g., "ai-tutor")                 |   Yes    |
   | prod_project_id        | **Production** Google Cloud Project ID for live tutoring deployment. |   Yes    |
   | staging_project_id     | **Staging** Google Cloud Project ID for educational testing.    |   Yes    |
   | cicd_runner_project_id | Google Cloud Project ID where CI/CD pipelines will execute.     |   Yes    |
   | region                 | Google Cloud region for resource deployment (recommended: us-central1).                    |   Yes    |
   | host_connection_name   | Name of the host connection you created in Cloud Build          |   Yes    |
   | repository_name        | Name of the repository you added to Cloud Build                 |   Yes    |

   Other optional variables may include: telemetry and feedback log filters for educational analytics, service account roles for AI services, and for advanced educational features: lesson analytics pipelines, learning progress tracking, and educational datastore configurations.

4. **Deploy Infrastructure with Terraform**

   - Open a terminal and navigate to the Terraform directory:

   ```bash
   cd deployment/terraform
   ```

   - Initialize Terraform:

   ```bash
   terraform init
   ```

   - Apply the Terraform configuration:

   ```bash
   terraform apply --var-file vars/env.tfvars
   ```

   - Type 'yes' when prompted to confirm

After completing these steps, your AI tutoring infrastructure will be set up and ready for educational deployment!

## Dev Deployment

For End-to-end testing of the AI tutoring application, including educational analytics, lesson state persistence, and learning progress tracking to BigQuery, without the need to trigger a CI/CD pipeline.

First, enable required Google Cloud APIs:

```bash
gcloud config set project <your-dev-project-id>
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com aiplatform.googleapis.com firestore.googleapis.com
```

After you edited the relative [`env.tfvars` file](../terraform/dev/vars/env.tfvars), follow the following instructions:

```bash
cd deployment/terraform/dev
terraform init
terraform apply --var-file vars/env.tfvars
```

Then deploy the AI tutoring application using the following command (from the root of the repository):

```bash
make backend
```

## Educational Features in Production

Once deployed, your AI tutoring agent will provide:

- **Personalized lesson planning** based on student requests and learning levels
- **Interactive educational content** with real-time markdown presentations
- **Visual learning support** through AI-generated educational images
- **Learning progress tracking** with persistent session management
- **Multimodal interactions** supporting voice, video, and text-based learning
- **Scalable architecture** to support multiple concurrent students

### End-to-end Demo video

<a href="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/template_deployment_demo.mp4">
  <img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/preview_video.png" alt="Watch the video" width="300"/>
</a>
