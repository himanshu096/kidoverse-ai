# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import asyncio
import base64
import warnings
import uuid 

from app.agent import root_agent, load_session_state_from_firestore, test_firestore_connectivity, load_lesson_state_from_firestore, save_lesson_state_to_firestore
from google.adk.sessions import InMemorySessionService

from pathlib import Path
from dotenv import load_dotenv

from google.genai.types import (
    Part,
    Content,
    Blob,
)

import backoff
from fastapi.middleware.cors import CORSMiddleware

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.sessions import VertexAiSessionService

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime


warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

#
# ADK Streaming
#


load_dotenv()

APP_NAME = os.getenv("APP_NAME")
main_app_runner = None



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Context Manager for FastAPI application lifespan events.
    Handles startup and shutdown logic.
    """
    global main_app_runner

    # Test Firestore connectivity on startup
    print("Testing Firestore connectivity...")
    firestore_ok = test_firestore_connectivity()
    if not firestore_ok:
        print("WARNING: Firestore connectivity test failed! State persistence may not work.")
    else:
        print("Firestore connectivity test passed.")

    # Use in-memory session service for fast, non-blocking performance
    session_service = InMemorySessionService()

    # Create a Runner with Firestore persistence
    main_app_runner = Runner(
        app_name=APP_NAME if APP_NAME else "kido-app-462308",
        agent=root_agent,
        session_service=session_service,
    )

    print("Application startup complete.")
    yield # This is where the application starts serving requests

    # --- Shutdown logic (executed when the application is shutting down) ---
    print("Application shutdown initiated...")
    # Add any cleanup code here if necessary, e.g., closing database connections
    print("Application shutdown complete.")
    
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def start_agent_session(user_id, is_audio=False):
    """Starts an agent session"""
    
    global root_agent
    global main_app_runner
    
    if root_agent is None or main_app_runner is None:
        raise RuntimeError("Application not fully initialized. root_agent or session_service is None.")
    
    print("[DEBUG] InMemoryRunner created.")
    
    session_service_for_crud = main_app_runner.session_service
    
    try:
        session = await session_service_for_crud.get_session(app_name=APP_NAME if APP_NAME else "kido-app-462308", user_id=user_id, session_id="")
        if session is not None:
            print(f"[{user_id}] Existing session retrieved with ID: {session.id}")
        else:
            print(f"[{user_id}] Failed to retrieve session for user {user_id}")
            raise RuntimeError(f"Session retrieval failed for user {user_id}")
    except Exception:
        session = await session_service_for_crud.create_session(
            app_name=APP_NAME if APP_NAME else "kido-app-462308",
            user_id=user_id,
            session_id="",
        )
        print(f"[{user_id}] New session created with ID: {session.id}")

    # --- Restore state from Firestore if available ---
    restored_state = load_session_state_from_firestore(APP_NAME, user_id)
    if restored_state:
        print(f"[RESTORE] Restoring session state from Firestore for user_id={user_id}")
        session.state.update(restored_state)
        # Ensure user_id is not overwritten by restored state
        session.state['user_id'] = user_id
        print(f"[RESTORE] Ensured user_id is set in session state: {session.state.get('user_id')}")
    else:
        print(f"[RESTORE] No existing state found for user_id={user_id}")
        # Ensure user_id is set even if no restored state
        session.state['user_id'] = user_id
        print(f"[RESTORE] Set user_id in session state: {session.state.get('user_id')}")

    # Set response modality
    # modality = "AUDIO" if is_audio else "TEXT"
    
    modality = "AUDIO"

    run_config = RunConfig(response_modalities=[modality])
    
    print(f"[DEBUG] RunConfig created. Set response modality to: {modality}")

    # Create a LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Start agent session
    live_events = main_app_runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    print("[DEBUG] runner.run_live called. Expecting live_events stream.")
    return main_app_runner, live_events, live_request_queue


async def agent_to_client_messaging(websocket: WebSocket, live_events):
    """
    Handles communication from the ADK agent to the client WebSocket.
    It streams events from the agent and sends structured messages back to the client
    as individual JSON objects.
    """
    print("[DEBUG] agent_to_client_messaging task started. Awaiting events from agent.")
    try:
        async for event in live_events:
            # print(f"[AGENT TO CLIENT] Processing ADK event:", event)

            # Process content parts
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # Handle inline_data (audio) - sent as a serverContent message with one audio part
                    if part.inline_data:
                        if part.inline_data.mime_type.startswith("audio/pcm"):
                            audio_data = part.inline_data.data
                            if audio_data:
                                audio_message = {
                                    "serverContent": {
                                        "modelTurn": {
                                            "parts": [{
                                                "inlineData": {
                                                    "data": base64.b64encode(audio_data).decode("ascii"),
                                                    "mimeType": part.inline_data.mime_type
                                                }
                                            }]
                                        }
                                    }
                                }
                                await websocket.send_bytes(json.dumps(audio_message).encode('utf-8'))
                                print(f"[AGENT TO CLIENT]: Sent individual audio/pcm message ({len(audio_data)} bytes).")

                    elif part.function_call:
                        tool_name = part.function_call.name
                        tool_args = part.function_call.args
                        print(f"[AGENT TO CLIENT]: Detected function call for tool '{tool_name}' with args: {tool_args}")
                        
                        # Handle the dedicated UI feedback signal tool
                        if tool_name == "signal_ui_feedback_func":
                            status_message = {
                                "ui_feedback": {
                                    "status": tool_args.get("status", "thinking"),
                                    "message": tool_args.get("message", "Please wait...")
                                }
                            }
                            await websocket.send_bytes(json.dumps(status_message).encode('utf-8'))
                            print(f"[AGENT TO CLIENT]: Sent UI feedback from signal tool: {status_message}.")
                        
                        # Handle feedback for other long-running tools
                        elif tool_name == "lesson_creation_workflow":
                            status_message = {
                                "ui_feedback": {
                                    "status": "thinking",
                                    "message": "I'm planning a new lesson for you..."
                                }
                            }
                            await websocket.send_bytes(json.dumps(status_message).encode('utf-8'))
                            print(f"[AGENT TO CLIENT]: Sent UI feedback message: {status_message}.")

                    # Handle function_response
                    elif part.function_response:
                        tool_name = part.function_response.name
                        tool_output = part.function_response.response

                        print(
                            f"[AGENT TO CLIENT]: Processing function response for tool '{tool_name}' with output: {tool_output}"
                        )
                        
                        # --- Special handling for image tool response: Send custom "image" JSON object ---
                        if tool_name == "generate_image_with_imagen" and isinstance(tool_output, dict) and "image_url" in tool_output:
                            image_url = tool_output["image_url"]
                            image_alt = tool_output.get("status", "Generated image")
                            image_message = {
                                "image": {  # Custom top-level key for image
                                    "url": image_url,
                                    "alt": image_alt
                                }
                            }
                            await websocket.send_bytes(json.dumps(image_message).encode('utf-8'))
                            print(f"[AGENT TO CLIENT]: Sent custom image message: {image_message}.")
                        elif tool_name == "send_current_section_markdown_tool" and isinstance(tool_output, dict):
                            markdown_message = {
                                "markdown": {
                                    "sectionIndex": tool_output.get("section_index"),
                                    "content": tool_output.get("markdown_content", "")
                                }
                            }
                            await websocket.send_bytes(json.dumps(markdown_message).encode('utf-8'))
                            print(f"[AGENT TO CLIENT]: Sent section markdown message: {markdown_message}.")
                            # Skip generic toolResponse for this helper tool
                        else:
                            # --- Default handling for all other tool responses: Send "toolResponse" JSON object ---
                            # This matches the existing isToolResponseMessage type expected by MultimodalLiveClient
                            tool_response_message = {
                                "toolResponse": {
                                    "functionResponses": [ # Even if it's one, it expects an array
                                        {
                                            "name": tool_name,
                                            "response": tool_output,
                                            "id": part.function_response.id # Include ID if present
                                        }
                                    ]
                                }
                            }
                            await websocket.send_bytes(json.dumps(tool_response_message).encode('utf-8'))
                            print(f"[AGENT TO CLIENT]: Sent generic tool response message: {tool_response_message}.")

            # Send turnComplete/interrupted as separate, dedicated messages after all content parts
            if event.turn_complete:
                turn_complete_message = {
                    "serverContent": { # These flags are part of serverContent structure
                        "turnComplete": True,
                        "modelTurn": {"parts": []} # Empty parts array for control messages
                    }
                }
                await websocket.send_bytes(json.dumps(turn_complete_message).encode('utf-8'))
                print("[AGENT TO CLIENT]: Sent turnComplete message.")

            if event.interrupted:
                interrupted_message = {
                    "serverContent": { # These flags are part of serverContent structure
                        "interrupted": True,
                        "modelTurn": {"parts": []} # Empty parts array for control messages
                    }
                }
                await websocket.send_bytes(json.dumps(interrupted_message).encode('utf-8'))
                print("[AGENT TO CLIENT]: Sent interrupted message.")

    except Exception as e:
        print(f"[ERROR] Agent to client messaging failed: {e}")
        raise


async def client_to_agent_messaging(websocket, live_request_queue):
    """Client to agent communication"""
    print("[DEBUG] client_to_agent_messaging task started. Waiting for client messages.")
    try:
        while True:
            message = await websocket.receive_json()
            # print(f"[CLIENT TO AGENT] Received from client: {message}")

            if "realtimeInput" in message:
                # IMPORTANT FIX: Access data from the first item in 'mediaChunks' array
                media_chunks = message["realtimeInput"].get("mediaChunks")
                if media_chunks and isinstance(media_chunks, list) and len(media_chunks) > 0:
                    first_chunk = media_chunks[0]
                    base64_data = first_chunk.get("data")
                    mime_type = first_chunk.get("mimeType", "audio/pcm") # Default to pcm if not specified

                    if base64_data:
                        decoded = base64.b64decode(base64_data)
                        live_request_queue.send_realtime(
                            Blob(data=decoded, mime_type=mime_type)
                        )
                        print(f"[CLIENT TO AGENT] Sent realtime audio to agent queue (length: {len(decoded)} bytes).")
                else:
                    print(f"[WARN] 'realtimeInput' received without valid 'mediaChunks': {message}")
            elif "clientContent" in message:
                text_data = message["clientContent"]
                if text_data:
                    content = Content(role="user", parts=[Part.from_text(text=text_data)])
                    live_request_queue.send_content(content=content)
                    print(f"[CLIENT TO AGENT] Sent text content to agent queue: '{text_data}'")
            else:
                print(f"[WARN] Unexpected format from client: {message}")

    except WebSocketDisconnect:
        print("[CLIENT TO AGENT] WebSocket disconnected gracefully.")
    except Exception as e:
        print(f"[ERROR] Client message handling failed: {e}")
        raise


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Client websocket endpoint"""
    
    is_audio_flag = True
    # Wait for client connection
    await websocket.accept()
    print("Client connected")

    # We'll get user_id from the setup message
    user_id = None
    
    # Start tasks
    agent_to_client_task = None
    client_to_agent_task = None
    
    try:
        # Wait for setup message to get user_id
        setup_message = await websocket.receive_json()
        if "setup" in setup_message:
            user_id = setup_message["setup"].get("user_id")
            run_id = setup_message["setup"].get("run_id")
            print(f"[SETUP] run_id={run_id}, user_id={user_id}")
            print(f"[SETUP DEBUG] user_id type: {type(user_id)}, length: {len(str(user_id)) if user_id else 0}")
            
            if not user_id:
                print("[ERROR] No user_id provided in setup message")
                await websocket.close(code=4000, reason="No user_id provided")
                return
        else:
            print("[ERROR] No setup message received")
            await websocket.close(code=4000, reason="No setup message")
            return

        print(f"Client #{user_id} connected")

        # Start agent session
        user_id_str = str(user_id)
        print(f"[SETUP DEBUG] Converting user_id to string: '{user_id}' -> '{user_id_str}'")
        runner, live_events, live_request_queue = await start_agent_session(user_id_str, is_audio=is_audio_flag)

        # Start tasks
        agent_to_client_task = asyncio.create_task(
            agent_to_client_messaging(websocket, live_events)
        )
        client_to_agent_task = asyncio.create_task(
            client_to_agent_messaging(websocket, live_request_queue)
        )
        
        # Wait until one of the tasks finishes (e.g., client disconnects)
        done, pending = await asyncio.wait(
            [agent_to_client_task, client_to_agent_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel() # Cancel any remaining tasks
        await asyncio.gather(*pending, return_exceptions=True) # Await cancellation
        
    except WebSocketDisconnect:
        print(f"Client #{user_id} WebSocket disconnected gracefully.")
    except Exception as e:
        print(f"Unhandled error in websocket_endpoint for client #{user_id}: {e}")
    finally:
        # Close LiveRequestQueue when connection ends
        if 'live_request_queue' in locals():
            live_request_queue.close()
        print(f"Client #{user_id} disconnected and resources cleaned up.")