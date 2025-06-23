# Multimodal Live AI Tutoring Agent

This pattern showcases a real-time conversational AI tutor powered by Google Gemini. The agent handles audio, video, and text interactions while providing personalized educational lessons with multimodal content generation capabilities.

![live_api_diagram](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/live_api_diagram.png)

**Key components:**

- **Python Backend** (in `app/` folder): A production-ready educational server built with [FastAPI](https://fastapi.tiangolo.com/) and [google-genai](https://googleapis.github.io/python-genai/) that features:

  - **Real-time bidirectional communication** via WebSockets between the frontend and Gemini model
  - **AI Tutoring System** with lesson planning, content delivery, and progress tracking
  - **Integrated tool calling** including:
    - **Imagen image generation** for educational illustrations and visual aids
    - **Markdown presentation delivery** for structured lesson content
    - **Learning history tracking** with Firestore persistence
    - **Lesson state management** for resuming interrupted sessions
  - **Multi-agent architecture** with specialized orchestrator and lesson delivery agents
  - **Production-grade reliability** with retry logic and automatic reconnection capabilities
  - **Deployment flexibility** supporting both AI Studio and Vertex AI endpoints
  - **Comprehensive logging and monitoring** for educational analytics

- **React Frontend** (in `frontend/` folder): Extends the [Multimodal live API Web Console](https://github.com/google-gemini/multimodal-live-api-web-console), with educational features like:
  - **Interactive lesson displays** with markdown rendering
  - **Real-time visual feedback** during lesson delivery
  - **Google OAuth authentication** for personalized learning experiences
  - **Responsive UI components** optimized for educational interactions

![live api demo](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/live_api_pattern_demo.gif)

## How It Works

Once both the backend and frontend are running, click the play button in the frontend UI to establish a connection with the backend. You can now interact with the AI Tutor! Try educational prompts such as:

- *"Can you teach me about photosynthesis for a 5th grade level?"*
- *"I want to learn basic algebra concepts"*
- *"Create a lesson about the solar system with images"*
- *"Continue my previous lesson"* (if you have lesson history)

The AI tutor will:
1. **Plan comprehensive lessons** tailored to your request and learning level
2. **Generate educational images** using Imagen to illustrate concepts
3. **Deliver structured content** via interactive markdown presentations
4. **Track your progress** and remember where you left off
5. **Adapt to your learning style** through multimodal interactions

## Educational Features

- **Personalized Lesson Planning**: Custom lesson plans based on topic, grade level, and learning objectives
- **Visual Learning Support**: Automatic generation of educational illustrations and diagrams
- **Interactive Presentations**: Real-time markdown delivery with structured content sections
- **Progress Persistence**: Lessons are saved and can be resumed across sessions
- **Learning History**: Complete tracking of completed lessons and learning achievements
- **Adaptive Delivery**: Real-time adjustment based on student responses and engagement
- **Multimodal Interaction**: Support for voice, video, and text-based learning

## Additional Resources for Multimodal Live API

Explore these resources to learn more about the Multimodal Live API and see examples of its usage:

- [Project Pastra](https://github.com/heiko-hotz/gemini-multimodal-live-dev-guide/tree/main): a comprehensive developer guide for the Gemini Multimodal Live API.
- [Google Cloud Multimodal Live API demos and samples](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/multimodal-live-api): Collection of code samples and demo applications leveraging multimodal live API in Vertex AI
- [Gemini 2 Cookbook](https://github.com/google-gemini/cookbook/tree/main/gemini-2): Practical examples and tutorials for working with Gemini 2
- [Multimodal Live API Web Console](https://github.com/google-gemini/multimodal-live-api-web-console): Interactive React-based web interface for testing and experimenting with Gemini Multimodal Live API.

## Current Status & Future Work

This educational pattern is under active development. Key areas planned for future enhancement include:

*   **Advanced Analytics**: Implementing comprehensive learning analytics and progress visualization
*   **Curriculum Integration**: Support for structured curriculum paths and prerequisites
*   **Assessment Tools**: Interactive quizzes and knowledge evaluation capabilities
*   **Collaborative Learning**: Multi-student session support and peer interaction features
*   **Observability**: Enhanced monitoring and tracing for educational metrics
*   **Load Testing**: Scalability testing for classroom and institutional deployment
