# Frontend Deployment Guide

This guide provides step-by-step instructions for deploying the frontend of the **Multimodal Live AI Tutoring Agent** to Firebase Hosting.

## Overview

The frontend is a React-based multimodal web interface that provides:
- **Interactive lesson displays** with markdown rendering
- **Real-time agent communication** via WebSocket connections
- **Google OAuth authentication** for personalized learning experiences
- **Educational UI components** optimized for tutoring interactions
- **Visual feedback and animations** during lesson delivery

## Prerequisites

1.  **Node.js and npm**: Ensure you have Node.js (which includes npm) installed on your system. You can download it from [nodejs.org](https://nodejs.org/).
2.  **Firebase CLI**: The Firebase Command Line Interface is required for deployment. If you don't have it installed, open your terminal and run:
    ```bash
    npm install -g firebase-tools
    ```
3.  **Google Account**: You will need a Google account to log in to Firebase.
4.  **Firebase Project**: Create a Firebase project in the [Firebase Console](https://console.firebase.google.com/) if you haven't already.

## Deployment Steps

The entire deployment process should be run from the **root directory** of the project.

### 1. Login to Firebase

First, you need to authenticate the Firebase CLI with your Google account. Run the following command:

```bash
firebase login
```

A browser window will open, prompting you to log in to your Google account and grant the necessary permissions.

### 2. Initialize Firebase (First Time Only)

If this is your first time deploying, you need to initialize Firebase in your project:

```bash
firebase init hosting
```

When prompted:
- Select "Use an existing project" and choose your Firebase project
- Set the public directory to: `frontend/build`
- Configure as a single-page app: `Yes`
- Don't overwrite the existing `index.html` if prompted

### 3. Select the Firebase Project

Your local project needs to be linked to a specific Firebase project. If you need to change projects or set it for the first time:

```bash
firebase use --add
```

Select your Firebase project from the list. This will create a `.firebaserc` file in your project root to remember your selection for future deployments.

### 4. Install Dependencies and Build the Frontend

Before deploying, you need to install the frontend's dependencies and create a production-ready build:

```bash
cd frontend && npm install && npm run build
```

This command will create a `frontend/build` directory, which contains the optimized static files for your user interface.

### 5. Deploy to Firebase Hosting

Finally, deploy the application. Navigate back to the root directory and run the deploy command:

```bash
cd .. && firebase deploy --only hosting
```

The `--only hosting` flag ensures that you are only deploying the frontend assets. The command will upload the contents of the `frontend/build` directory.

After the command completes, it will display the **Hosting URL** where your AI tutoring agent frontend is now live.

## Configuration

### Backend Connection

The frontend is configured to connect to your backend WebSocket server. You may need to update the WebSocket URLs in:
- `frontend/src/App.tsx`
- `frontend/src/utils/multimodal-live-client.ts`

For production deployments, ensure these point to your deployed Cloud Run backend service.

### Google OAuth Setup

For authentication features, follow the setup guide in [`GOOGLE_OAUTH_SETUP.md`](./GOOGLE_OAUTH_SETUP.md).

## Local Development

For local development and testing:

1. **Start the backend server** (from project root):
   ```bash
   make local-backend
   ```

2. **Start the frontend development server** (in another terminal):
   ```bash
   make ui
   ```

3. **Access the application** at `http://localhost:8501`

## Troubleshooting

- **Build Errors**: Ensure all dependencies are installed with `npm install`
- **Authentication Issues**: Verify your Google OAuth configuration
- **Connection Errors**: Check that backend WebSocket URLs are correctly configured
- **Firebase Errors**: Ensure you're logged into the correct Firebase account and project

---

By following these steps, you can reliably deploy the latest version of your AI tutoring agent frontend. 