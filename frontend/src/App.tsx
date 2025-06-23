/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useRef, useState, useEffect } from "react";
import "./App.scss";
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { LiveAPIProvider } from "./contexts/LiveAPIContext";
import SidePanel from "./components/side-panel/SidePanel";
import ControlTray from "./components/control-tray/ControlTray";
import cn from "classnames";
import ToolImage from "./components/image-component/ToolImage";
import MarkdownComponent from "./components/markdown-component/MarkdownComponent";
import Login from "./components/login/Login";
import MainHeader from "./components/main-header/MainHeader";
import AgentDisplay from "./components/agent-display/AgentDisplay";
import SuccessNotification from "./components/success-notification/SuccessNotification";

const defaultHost = "localhost:8000";
let wsUri: string;

// Use the current host for production, with wss for secure connection
wsUri = `wss://my-awesome-agent-564468103481.us-central1.run.app/ws`;


function MainContent() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);

  return (
    <div className="streaming-console">
      {/* Animated background elements */}
      <div className="background-shapes">
        <div className="shape shape-1"></div>
        <div className="shape shape-2"></div>
        <div className="shape shape-3"></div>
        <div className="shape shape-4"></div>
        <div className="shape shape-5"></div>
        <div className="shape shape-6"></div>
        <div className="shape shape-7"></div>
        <div className="shape shape-8"></div>
        <div className="shape shape-9"></div>
        <div className="shape shape-10"></div>
      </div>
      
      <div className="hidden">
        <SidePanel />
      </div>
      <main>
        <MainHeader />
        <div className="main-app-area">
          <AgentDisplay />
        </div>
        <ControlTray
          videoRef={videoRef}
          supportsVideo={true}
          onVideoStreamChange={setVideoStream}
        />
        {/* The video element is now separate to be controlled by ControlTray */}
        <video
          className={cn("stream", {
            hidden: !videoRef.current || !videoStream,
          })}
          ref={videoRef}
          autoPlay
          playsInline
        />
      </main>
    </div>
  );
}

function AppContent() {
  const { user, isAuthenticated, loading, successMessage, clearSuccessMessage } = useAuth();

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <Login />;
  }

  // Show main app if authenticated
  console.log("WebSocket URL:", wsUri);
  console.log("User ID for WebSocket:", user?.id);
  
  return (
    <div className="App">
      <LiveAPIProvider url={wsUri} userId={user?.id || ""}>
        <MainContent />
        {/* The SuccessNotification needs access to the AuthContext, so it stays here */}
        <SuccessNotification
          message={successMessage || ''}
          isVisible={!!successMessage}
          onClose={clearSuccessMessage}
          duration={3000}
        />
      </LiveAPIProvider>
    </div>
  );
}

function App() {
  // Google OAuth Client ID - Replace with your actual client ID
const GOOGLE_CLIENT_ID : string = process.env.REACT_APP_GOOGLE_CLIENT_ID || "";

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
