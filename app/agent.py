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

import json
import os
from datetime import datetime
import base64
import uuid 
import re

import google.auth
import vertexai
from google import genai
from google.genai import types

from google.adk.sessions import InMemorySessionService, Session
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import FunctionTool, agent_tool

from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext

from google.cloud import storage

from google.adk.runners import InMemoryRunner

from pydantic import BaseModel, Field, conlist
from typing import List, Optional, Annotated

import google.cloud.firestore as firestore

from google.adk.sessions.base_session_service import BaseSessionService

import asyncio

from .prompts import (
    LESSON_PLANNER_INSTRUCTION,
    LESSON_DELIVERED_INSTRUCTION,
    IMAGE_GENERATOR_INSTRUCTION,
    PRESENTATION_PLANNER_INSTRUCTION,
    MAIN_TUTOR_ORCHESTRATOR_INSTRUCTION
)

from app.models import (
    PlanLessonInput,
    LessonPlan,
    PresentationInput
)

# Constants
# --- Configurable constants ---
VERTEXAI_ENABLED = os.getenv("VERTEXAI", "true").lower() == "true"
LOCATION = os.getenv("VERTEXAI_LOCATION", "us-central1")
VOICE_NAME = os.getenv("VOICE_NAME", "Aoede")
MODEL_ID2 = os.getenv("MODEL_ID2", "gemini-live-2.5-flash-preview-native-audio")
MODEL_ID = os.getenv("MODEL_ID", "gemini-2.0-flash-live-preview-04-09")
LESSON_LOGIC_MODEL_ID = os.getenv("LESSON_LOGIC_MODEL_ID", "gemini-2.5-flash-lite-preview-06-17")
IMAGE_MODEL_ID = os.getenv("IMAGE_MODEL_ID", "imagen-3.0-generate-002")

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "generated_images_kiddo")

STAGING_BUCKET = os.getenv("STAGING_BUCKET", "gs://kido-sessions")


# Initialize Google Cloud clients
credentials, project_id = google.auth.default()



if VERTEXAI_ENABLED:
    vertexai.init(project=project_id, location=LOCATION, staging_bucket=STAGING_BUCKET)
    genai_client = genai.Client(project=project_id, location=LOCATION, vertexai=True)
    storage_client = storage.Client(project=project_id)
else:
    # For API key-based usage (outside Vertex AI)
    genai_client = genai.Client(http_options={"api_version": "v1alpha"})
    


def send_current_section_markdown_func(section_index: int, markdown_content: str):
    """
    This tool is called by the lesson_delivered_agent to send the Markdown
    for the current section to the frontend.
    """
    return {"status": "success", "section_index": section_index,"markdown_content": markdown_content, "markdown_content_length": len(markdown_content)}


# end of long running tasks

    
# --- Define Custom Tool for Imagen Generation ---
# This function will be wrapped as an ADK tool
def generate_image_with_imagen(prompt: str) -> dict:
    """
    Generates an image using the Imagen model, uploads it to GCS,
    and returns the public URL.
    Args:
        prompt: A descriptive text prompt for the image to be generated.
    Returns:
        A dictionary containing the public URL of the generated image or an error message.
    """
    try:
        print(f"[TOOL] Calling Imagen with prompt: '{prompt}'")
        response = genai_client.models.generate_images(
            model=IMAGE_MODEL_ID,
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1)
        )

        print(f"[TOOL] Imagen response: {response}")

        if response.generated_images:
            generated_image_obj = response.generated_images[0]
            
            # Get the image bytes from the response
            image_bytes_data = None
            if hasattr(generated_image_obj, 'image') and generated_image_obj.image:
                nested_image_data = generated_image_obj.image
                if hasattr(nested_image_data, 'image_bytes') and nested_image_data.image_bytes:
                    image_bytes_data = nested_image_data.image_bytes
                    print(f"[TOOL] Retrieved image bytes (length: {len(image_bytes_data)} bytes)")
                elif hasattr(nested_image_data, 'gcs_uri') and nested_image_data.gcs_uri:
                    # If GCS URI is directly provided, we can just use that
                    # This path might be taken by some model configurations
                    print(f"[TOOL] Imagen directly returned GCS URI: {nested_image_data.gcs_uri}")
                    return {"image_url": nested_image_data.gcs_uri, "status": "Image generated and hosted successfully."}
            
            if not image_bytes_data:
                return {"error": "Image generation successful, but no image bytes or GCS URI found in response."}

            # --- UPLOAD TO GCS ---
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            # Generate a unique filename for the image
            filename = f"generated_images/{uuid.uuid4()}.png"
            blob = bucket.blob(filename)

            # Upload the image bytes
            blob.upload_from_string(image_bytes_data, content_type='image/png')

            public_url = blob.public_url
            print(f"[TOOL] Image uploaded to GCS: {public_url}")

            # --- RETURN ONLY THE URL TO THE LLM ---
            return {"image_url": public_url, "status": "Image generated and hosted successfully."}
        else:
            return {"error": "Image generation failed: No images generated in the response."}
    except Exception as e:
        print(f"[TOOL ERROR] Imagen generation failed or GCS upload failed: {e}")
        return {"error": f"Failed to generate or upload image: {str(e)}"}

# Wrap the Python function as an ADK FunctionTool
# The 'name' here is what the LLM will 'call' in its tool_code
generate_image_tool = FunctionTool(
    generate_image_with_imagen
)

generate_image_tool.is_long_running = True
print(f"[AGENT DEBUG] Custom 'generate_image_tool' created.")

def signal_ui_feedback_func(status: str, message: str):
    """
    A special tool that does nothing except signal to the system that a certain UI feedback state should be triggered on the frontend.
    For example, call this with status='generating_image' before calling the image generation tool.
    """
    print(f"[UI_SIGNAL] Received signal: status='{status}', message='{message}'")
    return {"status": "signal_received"}

signal_ui_feedback_tool = FunctionTool(signal_ui_feedback_func)

send_current_section_markdown_tool = FunctionTool(
    send_current_section_markdown_func
)

send_current_section_markdown_tool.is_long_running = True


APP_NAME = "kido-app-462308"

def before_lesson_planner_callback(callback_context: CallbackContext):
    """
    Callback that runs before the lesson planner agent.
    It fetches the user's learning history and injects it into the session state.
    """
    print("[CALLBACK] before_lesson_planner_callback triggered.")
    user_id = callback_context.state.get('user_id')
    if user_id:
        print(f"[CALLBACK] Found user_id: {user_id}. Fetching learning profile.")
        learning_profile = get_user_learning_profile(user_id) # Direct python call
        if learning_profile and learning_profile.get("completed_topics"):
            # Put the profile into the session state for the agent to use
            callback_context.state['user_learning_context'] = learning_profile
            print(f"[CALLBACK] Injected learning profile into session state: {learning_profile}")
        else:
            # Explicitly clear any old context if no new one is found
            callback_context.state['user_learning_context'] = None
            print(f"[CALLBACK] No completed lessons found for user {user_id}. Cleared any existing context.")
    else:
        print("[CALLBACK] No user_id found in state, cannot fetch learning profile.")


presentation_agent = Agent(
        name="PresentationAgentLessonPlan",
        model="gemini-2.0-flash-lite",
        description="An agent specialized in converting structured lesson plans into Markdown presentations",
        instruction=PRESENTATION_PLANNER_INSTRUCTION,
        tools=[],
        input_schema=PresentationInput,
        # output_schema=LessonPlan, # This is incorrect, output is markdown string
        # output_key="current_lesson_plan", # This overwrites the actual lesson plan object
    )

    # Create the lesson planner tool instance with the shared session service
    
lesson_planner_agent = Agent(
        name="plan_lesson_tool",
        model="gemini-2.0-flash-lite",
        description="An AI assistant specialized in creating detailed lesson plans, including generating supporting images.",
        instruction=LESSON_PLANNER_INSTRUCTION,
        tools=[],
        input_schema=PlanLessonInput,
        output_schema=LessonPlan,
        output_key="current_lesson_plan",
        before_agent_callback=before_lesson_planner_callback,
    )
print(f"[AGENT DEBUG] lesson_planner_agent initialized with model: {lesson_planner_agent.model}")


# --- Centralized State Update Helper ---
def _update_and_persist_state(context, updates):
    """Centralized function to update state and persist to Firestore."""
    context.state.update(updates)
    user_id = context.state.get('user_id')
    if user_id:
        # Use create_task to run in the background without awaiting
        # This is safe to call from a sync function within an async event loop
        asyncio.create_task(save_lesson_state_to_firestore(user_id, context.state))
        print(f"[STATE_HELPER] State persistence task created for user {user_id} with updates: {list(updates.keys())}")
    else:
        print("[STATE_HELPER] WARNING: No user_id found in state for persistence.")


# --- Define Root Agent (Orchestrator) ---
def handle_before_agent_callback(callback_context: CallbackContext):
    """Enhanced before_agent callback with better error handling and logging"""
    agent_name = callback_context.agent_name if hasattr(callback_context, 'agent_name') else "Unknown"
    print(f"[AGENT DEBUG] before_agent callback triggered for {agent_name}")
    print(f"[AGENT DEBUG] Current user_id in session: {callback_context.state.get('user_id')}")
    print(f"[AGENT DEBUG] Session state has user_id: {'user_id' in callback_context.state}")
    print(f"[AGENT DEBUG] Session state has current_lesson_plan: {'current_lesson_plan' in callback_context.state}")
    
    # --- Welcome back logic for root orchestrator ---
    if agent_name == "main_tutor_orchestrator_agent":
        print(f"[AGENT DEBUG] Main tutor orchestrator agent being invoked")
        # Enhanced welcome back logic that reads from lesson state
        user_id = callback_context.state.get('user_id')
        print(f"[WELCOME_BACK DEBUG] Starting welcome back logic for user_id: {user_id}")
        
        # Initialize variables
        last_topic = None
        last_progress = None
        
        if user_id:
            lesson_state = load_lesson_state_from_firestore(user_id)
            print(f"[WELCOME_BACK DEBUG] Loaded lesson state from Firestore: {lesson_state is not None}")
            
            if lesson_state and lesson_state.get("current_lesson_plan"):
                # We have an actual lesson in progress, use that
                last_topic = lesson_state.get("current_lesson_plan", {}).get("topic")
                last_progress = {
                    "current_lesson_plan": lesson_state.get("current_lesson_plan"),
                    "current_lesson_section_index": lesson_state.get("current_lesson_section_index", 0),
                }
                # Restore the lesson state to session
                print(f"[WELCOME_BACK DEBUG] Restoring lesson state to session: {last_topic}")
                callback_context.state.update(lesson_state)
                print(f"[WELCOME_BACK] Restored lesson state for topic: {last_topic}")
            else:
                print(f"[WELCOME_BACK DEBUG] No lesson state found, checking session state")
                last_topic = callback_context.state.get("user:last_lesson_topic")
                last_progress = callback_context.state.get("user:last_lesson_progress")
                print(f"[WELCOME_BACK] Using session state for topic: {last_topic}")
        else:
            print(f"[WELCOME_BACK DEBUG] No user_id found in callback_context.state")
        
        print(f"[WELCOME_BACK DEBUG] Final last_topic: {last_topic}")
        print(f"[WELCOME_BACK DEBUG] Final last_progress: {last_progress}")
        
        if last_topic:
            callback_context.state["welcome_back_message"] = f"Hey, you were learning {last_topic} last time. Would you like to continue?"
            if last_progress:
                callback_context.state["resume_lesson_progress"] = last_progress
                print(f"[WELCOME_BACK] Set welcome back message and resume progress for topic: {last_topic}")
        else:
            print(f"[WELCOME_BACK] No previous lesson found for user {user_id}")
    # --- Existing logic for lesson_delivered_agent ---
    if agent_name == "lesson_delivered_agent":
        lesson_plan = callback_context.state.get("current_lesson_plan")
        parsed_markdowns = callback_context.state.get("parsed_section_markdowns")
        current_section_index = callback_context.state.get("current_lesson_section_index", 0)
        
        print(f"[BEFORE_AGENT] Lesson delivery agent invoked")
        print(f"[BEFORE_AGENT] Lesson plan present: {lesson_plan is not None}")
        print(f"[BEFORE_AGENT] Parsed markdowns present: {parsed_markdowns is not None}")
        print(f"[BEFORE_AGENT] Current section index: {current_section_index}")
        if parsed_markdowns:
            print(f"[BEFORE_AGENT] Number of parsed markdown sections: {len(parsed_markdowns)}")
        
        # NOTE: Logic to regenerate markdown has been removed.
        # State persistence should ensure that if a lesson plan exists,
        # the markdown also exists.
        
        if lesson_plan:
            print(f"[BEFORE_AGENT] Lesson delivery agent found lesson plan. Topic: {lesson_plan.get('topic', 'Unknown')}")
            callback_context.state["lesson_plan_for_delivery"] = lesson_plan
            lesson_context = f"""
You are now delivering a lesson on: {lesson_plan.get('topic', 'Unknown Topic')}
Duration: {lesson_plan.get('duration_minutes', 'Unknown')} minutes
Learning objectives: {', '.join(lesson_plan.get('learning_objectives', []))}

The lesson plan structure is available in your session context. Follow it while adapting to the student's pace and responses.
"""
            callback_context.state["lesson_context"] = lesson_context
        else:
            print(f"[BEFORE_AGENT] Warning: Lesson delivery agent started without a lesson plan")
            callback_context.state["lesson_context"] = """
You are ready to deliver a lesson, but no specific lesson plan was provided. 
Ask the student what they'd like to learn about, then be prepared to teach that topic.
"""

def get_my_learning_history_func():
    """
    Call this tool to retrieve the user's completed lesson history.
    It should be called when the user asks "what have I learned?" or similar questions about their progress.
    This tool takes no arguments.
    """
    # The actual logic is handled in the after_tool_callback, which has access to session state.
    return {"status": "pending_history_retrieval"}

# Wrap it
get_my_learning_history_tool = FunctionTool(get_my_learning_history_func)

def complete_lesson_func():
    """
    Call this tool WITHOUT any arguments when a lesson is fully completed.
    This will archive the lesson and prepare for the next user request.
    """
    # This function is just a trigger. The real work is in the callback.
    return {"status": "pending_cleanup"}

# Wrap it
complete_lesson_tool = FunctionTool(complete_lesson_func)


# --- Enhanced after_tool callback with Firestore sync ---
def handle_orchestrator_tool_callback(tool, args, tool_context, tool_response):
    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
    
    print(f"[CALLBACK] Processing response from tool: {tool_name}")
    print(f"[CALLBACK] Processing response from tool: {tool_name} with args: {args}")

    if tool_name == "get_my_learning_history_func":
        print("[CALLBACK] History tool called. Fetching history.")
        user_id = tool_context.state.get("user_id")
        if not user_id:
            return {"summary": "I can't seem to find your user profile to check your history."}

        completed_lessons = get_user_completed_lessons(user_id)
        if not completed_lessons:
            return {"summary": "You haven't completed any lessons yet. What would you like to learn about first?"}

        topic_list = [f"- {lesson['topic']} (on {lesson.get('completion_date', 'N/A')[:10]})" for lesson in completed_lessons]
        
        summary = (
            f"You have completed {len(completed_lessons)} lesson(s) so far! Great job!\n\n"
            "Here are the topics you've mastered:\n" +
            '\n'.join(topic_list)
        )
        return {"summary": summary}

    if tool_name == "complete_lesson_func":
        print("[CALLBACK] Lesson completion tool called. Clearing state.")
        state = tool_context.state
        user_id = state.get("user_id")
        lesson_plan = state.get("current_lesson_plan")

        if user_id and lesson_plan:
            # Save to completed lessons history
            specific_topic = lesson_plan.get("topic", "Unknown")
            save_completed_lesson_to_firestore(user_id, lesson_plan)
            print(f"[CALLBACK] Saved completed lesson '{specific_topic}' for user {user_id}.")
            # Store the specific topic for the next conversational turn.
            state['last_completed_topic'] = specific_topic

        # Keys to remove from session state
        keys_to_clear = [
            "current_lesson_plan", 
            "parsed_section_markdowns", 
            "current_lesson_section_index",
            "lesson_plan_for_delivery",
            "lesson_context",
            "welcome_back_message",
            "resume_lesson_progress",
            "user:last_lesson_progress",
        ]
        cleared_keys = []
        for key in keys_to_clear:
            if key in state:
                # Use assignment to None instead of pop, which is not supported
                state[key] = None
                cleared_keys.append(key)
        
        print(f"[CALLBACK] Cleared session state keys: {cleared_keys}")

        if user_id:
            # Persist the cleared state to Firestore
            asyncio.create_task(save_lesson_state_to_firestore(user_id, {}))
            print(f"[CALLBACK] Firestore persistence task created for clearing lesson state.")
        
        return {"status": "success", "message": "Lesson state has been cleared."}
    if tool_name == "lesson_creation_workflow":
        print(f"[CALLBACK] Lesson creation workflow finished.")
        # The response from a Sequential agent is the response of the LAST step.
        # In our case, this is the markdown from the presentation agent.
        presentation_markdown = tool_response
        
        parsed_section_markdowns = []
        if isinstance(presentation_markdown, str):
            sections = presentation_markdown.split('---')
            for idx, section in enumerate(sections):
                section_content = section.strip()
                if section_content:
                    parsed_section_markdowns.append({"index": idx, "markdown": section_content})
        
        # The lesson plan was saved to state in the first step of the workflow.
        # Now we save the generated markdown.
        updates = {
            "parsed_section_markdowns": parsed_section_markdowns,
            "current_lesson_section_index": 0,
        }
        _update_and_persist_state(tool_context, updates)
        
        return { "status": "success", "message": "Lesson plan and presentation are ready.", "ready_for_delivery": True }
        
    elif tool_name == "send_current_section_markdown_func":
        section_index = args.get("section_index")
        markdown_content = args.get("markdown_content")
        
        print(f"[CALLBACK] send_current_section_markdown_func called with section_index={section_index}")
        print(f"[CALLBACK] Markdown content length: {len(markdown_content) if markdown_content else 0}")
        print(f"[CALLBACK] Markdown content preview: {markdown_content[:200] if markdown_content else 'None'}...")
        
        # --- Update user:last_lesson_progress on section advance ---
        # This logic is about creating a temporary resume point, not full state persistence
        if tool_context.state.get("current_lesson_plan") is not None:
            tool_context.state["user:last_lesson_progress"] = {
                "current_lesson_plan": tool_context.state["current_lesson_plan"],
                "current_lesson_section_index": tool_context.state.get("current_lesson_section_index", 0),
            }
            print(f"[CALLBACK] Updated user:last_lesson_progress with section_index={tool_context.state.get('current_lesson_section_index', 0)}")
            
        # Update the current section index and persist the entire state
        updates = {"current_lesson_section_index": section_index}
        _update_and_persist_state(tool_context, updates)
        
        return {
            "status": "success",
            "section_index": section_index,
            "markdown_content": markdown_content,
        }
    else:
        print(f"[CALLBACK] Passing through response from {tool_name}")
        return tool_response

def handle_delivery_agent_tool_callback(tool, args, tool_context, tool_response):
    """Enhanced after_tool callback with comprehensive response handling"""
    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
    
    print(f"[CALLBACK1] handle_before_tool_callback response from tool: {tool_name}")
    print(f"[CALLBACK1] handle_before_tool_callback response from tool: {tool_name} with args: {args}")
    
    # Handle image generation tool
    if tool_name == "generate_image_with_imagen":
        if isinstance(tool_response, dict):
            if "image_url" in tool_response and "error" not in tool_response:
                # Successful image generation
                image_url = tool_response["image_url"]
                print(f"[CALLBACK1] Image generated successfully: {image_url}")
                # Store in session for potential future reference
                current_images = tool_context.state.get("generated_image_urls", [])
                current_images.append({
                    "url": image_url,
                    "timestamp": datetime.now().isoformat(),
                    "prompt": args.get("prompt", "Unknown prompt")
                })
                tool_context.state["generated_image_urls"] = current_images
                # Return simplified response for the LLM (only on first generation)
                return {
                    "status": "success",
                    "message": "Image generated successfully and is now visible to the student.",
                    "image_url": image_url
                }
            elif "error" in tool_response:
                print(f"[CALLBACK1] Image generation failed: {tool_response['error']}")
                return {
                    "status": "error",
                    "message": "I had trouble creating that image. Let me try to explain with words instead!"
                }
        return {"status": "error", "message": "Unexpected response from image generation"}
    
    elif tool_name == "send_current_section_markdown_func":
        section_index = args.get("section_index")
        markdown_content = args.get("markdown_content")

        if section_index is not None:
            tool_context.state["current_lesson_section_index"] = section_index

        print(f"[CALLBACK1] Received request to send section {section_index} markdown content")
        print(f"[DEBUG] State after section advance: section_index={tool_context.state.get('current_lesson_section_index')}, parsed_section_markdowns={tool_context.state.get('parsed_section_markdowns')}")
        
        # Enhanced logging and state management
        print(f"[CALLBACK1] send_current_section_markdown_func called with section_index={section_index}")
        print(f"[CALLBACK1] Markdown content length: {len(markdown_content) if markdown_content else 0}")
        print(f"[CALLBACK1] Markdown content preview: {markdown_content[:200] if markdown_content else 'None'}...")
        
        # Update the current section index
        if section_index is not None:
            tool_context.state["current_lesson_section_index"] = section_index
            print(f"[CALLBACK1] Updated current_lesson_section_index to {section_index}")
        else:
            print(f"[CALLBACK1] WARNING: section_index is None!")
        
        print(f"[DEBUG] State after section update in delivery agent:")
        print(f"[DEBUG] - current_lesson_section_index: {tool_context.state.get('current_lesson_section_index')}")
        print(f"[DEBUG] - parsed_section_markdowns: {len(tool_context.state.get('parsed_section_markdowns', []))} sections")
        
        # --- Debug: Check if parsed_section_markdowns exists and has the right content ---
        parsed_markdowns = tool_context.state.get('parsed_section_markdowns')
        if parsed_markdowns and isinstance(parsed_markdowns, list) and section_index is not None:
            if section_index < len(parsed_markdowns):
                expected_markdown = parsed_markdowns[section_index].get('markdown', '')
                print(f"[CALLBACK1] Expected markdown from parsed_section_markdowns[{section_index}]: {expected_markdown[:200]}...")
                if markdown_content != expected_markdown:
                    print(f"[CALLBACK1] WARNING: Markdown content mismatch! Using provided content.")
            else:
                print(f"[CALLBACK1] WARNING: Section index {section_index} out of range for parsed_section_markdowns (length: {len(parsed_markdowns)})")
        else:
            print(f"[CALLBACK1] WARNING: parsed_section_markdowns not found or invalid: {parsed_markdowns}")
        
        # --- Update user:last_lesson_progress on section advance ---
        if tool_context.state.get("current_lesson_plan") is not None:
            tool_context.state["user:last_lesson_progress"] = {
                "current_lesson_plan": tool_context.state["current_lesson_plan"],
                "current_lesson_section_index": tool_context.state.get("current_lesson_section_index", 0),
            }
            print(f"[CALLBACK1] Updated user:last_lesson_progress with section_index={tool_context.state.get('current_lesson_section_index', 0)}")
        
        # --- Save lesson state to Firestore after section advance in delivery agent ---
        user_id = tool_context.state.get('user_id')
        if user_id:
            print(f"[CALLBACK1] Creating task to save lesson state to Firestore for user {user_id} after section advance")
            asyncio.create_task(save_lesson_state_to_firestore(user_id, tool_context.state))
        else:
            print(f"[CALLBACK1] WARNING: No user_id found for Firestore save")
        
        # --- Firestore persistence after lesson checkpoint ---
        session_id = tool_context.state.get('session_id', None)
        if user_id and session_id:
            asyncio.create_task(persist_session_state_to_firestore(APP_NAME, user_id, session_id, dict(tool_context.state)))
            print(f"[CALLBACK1] Session state persistence task created")
        
        return {
            "status": "success",
            "section_index": section_index,
            "markdown_content": markdown_content,
        }
    # Handle other tools - return their response as-is
    else:
        print(f"[CALLBACK] Passing through response from {tool_name}")
        return tool_response


# --- Define the Lesson Creation Workflow ---
lesson_creation_workflow_agent = SequentialAgent(
    name="lesson_creation_workflow",
    description="A workflow that first creates a lesson plan based on a topic, and then generates a presentation for it. The final output is the presentation content.",
    # The `input_schema` of the first step becomes the input for the workflow.
    # The output of the first step is passed as input to the second step.
    sub_agents=[lesson_planner_agent, presentation_agent]
)

# Wrap the workflow in an AgentTool to be used by the orchestrator
lesson_creation_tool = agent_tool.AgentTool(
    agent=lesson_creation_workflow_agent,
    skip_summarization=False # We want the final markdown output
)
lesson_creation_tool.is_long_running = True


lesson_delivered_agent = Agent(
    name="lesson_delivered_agent",
    model=MODEL_ID,
    description="An AI assistant specialized in delivering lessons and answering questions during a lesson.",
    instruction=LESSON_DELIVERED_INSTRUCTION,
    tools=[generate_image_tool, send_current_section_markdown_tool, signal_ui_feedback_tool],
    after_tool_callback=handle_delivery_agent_tool_callback,
    before_agent_callback=handle_before_agent_callback,
)
print(f"[AGENT DEBUG] lesson_delivered_agent initialized with model: {lesson_delivered_agent.model}")


root_agent = Agent(
name="main_tutor_orchestrator_agent",
model=MODEL_ID, # live model for real-time interaction
description="A versatile AI assistant that can answer general questions and generate images.",
instruction=MAIN_TUTOR_ORCHESTRATOR_INSTRUCTION,
# The root agent now has a single tool for creating lessons.
tools=[lesson_creation_tool, complete_lesson_tool, get_my_learning_history_tool],
sub_agents=[lesson_delivered_agent],
after_tool_callback=handle_orchestrator_tool_callback,
before_agent_callback=handle_before_agent_callback,
)
# NOTE: Only lesson_delivered_agent can call generate_image_with_imagen. All lesson delivery, including image generation, must be delegated to lesson_delivered_agent after planning.

print(f"[AGENT DEBUG] root_agent initialized. Tools: {[getattr(tool, 'name', str(tool)) for tool in root_agent.tools]}")

# --- Firestore lesson state helpers (manual persistence, not session service) ---
firestore_client = firestore.Client()
lesson_collection = firestore_client.collection("adk_lessons")
session_collection = firestore_client.collection("adk_sessions")
completed_lessons_collection = firestore_client.collection("adk_completed_lessons")

def _save_lesson_state_to_firestore_sync(user_id, lesson_state):
    """
    Synchronous implementation of saving lesson state to Firestore.
    This should be run in a separate thread to avoid blocking.
    """
    try:
        print(f"[FIRESTORE DEBUG] === SAVING LESSON STATE ===")
        print(f"[FIRESTORE DEBUG] User ID: '{user_id}' (type: {type(user_id)})")
        print(f"[FIRESTORE DEBUG] User ID length: {len(str(user_id)) if user_id else 0}")
        
        # Validate user_id
        if not user_id:
            print(f"[FIRESTORE ERROR] user_id is None or empty")
            return False
        
        # Ensure user_id is a string
        user_id_str = str(user_id).strip()
        if not user_id_str:
            print(f"[FIRESTORE ERROR] user_id is empty after conversion to string")
            return False
        
        print(f"[FIRESTORE DEBUG] Using user_id_str: '{user_id_str}'")
        
        lesson_state_to_save = {
            "user_id": user_id_str,
            "current_lesson_plan": lesson_state.get("current_lesson_plan"),
            "parsed_section_markdowns": lesson_state.get("parsed_section_markdowns"),
            "current_lesson_section_index": lesson_state.get("current_lesson_section_index"),
            "last_updated": datetime.now().isoformat(),
        }
        
        print(f"[FIRESTORE DEBUG] Saving lesson state for user {user_id_str}:")
        print(f"[FIRESTORE DEBUG] - current_lesson_plan: {lesson_state_to_save['current_lesson_plan'] is not None}")
        print(f"[FIRESTORE DEBUG] - current_lesson_section_index: {lesson_state_to_save['current_lesson_section_index']}")
        print(f"[FIRESTORE DEBUG] - parsed_section_markdowns: {len(lesson_state_to_save['parsed_section_markdowns']) if lesson_state_to_save['parsed_section_markdowns'] else 0} sections")
        
        if lesson_state_to_save['parsed_section_markdowns']:
            for idx, section in enumerate(lesson_state_to_save['parsed_section_markdowns']):
                print(f"[FIRESTORE DEBUG] - Section {idx} length: {len(section.get('markdown', ''))} chars")
        
        # Check if Firestore client is properly initialized
        if not hasattr(lesson_collection, 'document'):
            print(f"[FIRESTORE ERROR] lesson_collection is not properly initialized")
            return False
        
        # Check if document already exists
        doc_ref = lesson_collection.document(user_id_str)
        existing_doc = doc_ref.get()
        if existing_doc.exists:
            print(f"[FIRESTORE DEBUG] Document already exists for user {user_id_str}, will overwrite")
            existing_data = existing_doc.to_dict()
            if existing_data and isinstance(existing_data, dict):
                current_lesson_plan = existing_data.get('current_lesson_plan')
                if current_lesson_plan and isinstance(current_lesson_plan, dict):
                    print(f"[FIRESTORE DEBUG] Existing topic: {current_lesson_plan.get('topic', 'None')}")
                else:
                    print(f"[FIRESTORE DEBUG] Existing topic: None (no lesson plan)")
            else:
                print(f"[FIRESTORE DEBUG] Existing topic: None (invalid data)")
        else:
            print(f"[FIRESTORE DEBUG] Creating new document for user {user_id_str}")
        
        # Attempt to save
        print(f"[FIRESTORE DEBUG] Attempting to save document...")
        doc_ref.set(lesson_state_to_save)
        print(f"[FIRESTORE DEBUG] Lesson state saved to Firestore successfully")
        
        # Verify the save by reading it back
        verification_doc = doc_ref.get()
        if verification_doc.exists:
            saved_data = verification_doc.to_dict()
            print(f"[FIRESTORE DEBUG] Verification: Document exists after save")
            print(f"[FIRESTORE DEBUG] Verification: Saved section_index = {saved_data.get('current_lesson_section_index') if saved_data else 'None'}")
            
            # Safe check for parsed_section_markdowns
            parsed_markdowns = saved_data.get('parsed_section_markdowns') if saved_data else None
            if parsed_markdowns is not None:
                print(f"[FIRESTORE DEBUG] Verification: Saved markdown sections = {len(parsed_markdowns)}")
            else:
                print(f"[FIRESTORE DEBUG] Verification: Saved markdown sections = 0 (None)")
            
            # Safe check for topic
            current_lesson_plan = saved_data.get('current_lesson_plan') if saved_data else None
            if current_lesson_plan and isinstance(current_lesson_plan, dict):
                print(f"[FIRESTORE DEBUG] Verification: Saved topic = {current_lesson_plan.get('topic', 'None')}")
            else:
                print(f"[FIRESTORE DEBUG] Verification: Saved topic = None (no lesson plan)")
            return True
        else:
            print(f"[FIRESTORE ERROR] Document does not exist after save attempt!")
            return False
            
    except Exception as e:
        print(f"[FIRESTORE ERROR] Failed to save lesson state for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def save_lesson_state_to_firestore(user_id, lesson_state):
    """
    Asynchronously saves lesson state to Firestore by running the sync version in a thread.
    """
    return await asyncio.to_thread(
        _save_lesson_state_to_firestore_sync, user_id, lesson_state
    )

def save_completed_lesson_to_firestore(user_id, lesson_plan, completion_date=None):
    """
    Save a completed lesson to Firestore for tracking learning history.
    """
    if completion_date is None:
        completion_date = datetime.now().isoformat()
    
    completed_lesson_data = {
        "user_id": user_id,
        "topic": lesson_plan.get("topic", "Unknown"),
        "grade_level": lesson_plan.get("grade_level", "Unknown"),
        "duration_minutes": lesson_plan.get("duration_minutes", 0),
        "learning_objectives": lesson_plan.get("learning_objectives", []),
        "completion_date": completion_date,
        "sections_count": len(lesson_plan.get("sections", [])),
    }
    
    # Use topic as document ID to avoid duplicates
    doc_ref = completed_lessons_collection.document(f"{user_id}_{lesson_plan.get('topic', 'unknown').replace(' ', '_').lower()}")
    doc_ref.set(completed_lesson_data)
    print(f"[FIRESTORE] Saved completed lesson: {lesson_plan.get('topic', 'Unknown')} for user {user_id}")

def get_user_completed_lessons(user_id):
    """
    Get all completed lessons for a user from Firestore.
    """
    docs = completed_lessons_collection.where("user_id", "==", user_id).stream()
    completed_lessons = []
    for doc in docs:
        lesson_data = doc.to_dict()
        completed_lessons.append({
            "topic": lesson_data.get("topic", "Unknown"),
            "grade_level": lesson_data.get("grade_level", "Unknown"),
            "completion_date": lesson_data.get("completion_date", ""),
            "learning_objectives": lesson_data.get("learning_objectives", [])
        })
    return completed_lessons

def get_user_learning_profile(user_id):
    """
    Get a comprehensive learning profile for a user based on completed lessons.
    """
    completed_lessons = get_user_completed_lessons(user_id)
    
    if not completed_lessons:
        return {
            "completed_topics": [],
            "grade_level": "Ages 6-10",  # Default
            "learning_style": "mixed",
            "interests": [],
            "total_lessons_completed": 0
        }
    
    # Analyze completed lessons to build learning profile
    topics = [lesson["topic"] for lesson in completed_lessons]
    grade_levels = [lesson["grade_level"] for lesson in completed_lessons]
    all_objectives = []
    for lesson in completed_lessons:
        all_objectives.extend(lesson.get("learning_objectives", []))
    
    # Determine most common grade level
    grade_level = max(set(grade_levels), key=grade_levels.count) if grade_levels else "Ages 6-10"
    
    # Extract potential interests from topics and objectives
    interests = list(set(topics))  # Unique topics as interests
    
    return {
        "completed_topics": topics,
        "grade_level": grade_level,
        "learning_style": "mixed",  # Could be enhanced with more analysis
        "interests": interests,
        "total_lessons_completed": len(completed_lessons)
    }

def load_lesson_state_from_firestore(user_id):
    """
    Load the lesson state for a user from Firestore, if it exists.
    """
    doc_ref = lesson_collection.document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

# --- Call this after session creation to pre-populate state from Firestore ---
def populate_session_state_from_firestore(session):
    user_id = session.user_id
    lesson_state = load_lesson_state_from_firestore(user_id)
    if lesson_state:
        session.state.update(lesson_state)
        # Ensure parsed_section_markdowns is restored
        if 'parsed_section_markdowns' in lesson_state:
            session.state['parsed_section_markdowns'] = lesson_state['parsed_section_markdowns']
    # Always ensure user_id is set in session.state
    session.state['user_id'] = user_id

# --- Firestore lesson existence check and loader ---
def get_or_create_lesson_for_user(user_id, topic, session):
    """
    Checks Firestore for an existing lesson plan for this user and topic.
    If found and markdown is present, updates session.state and returns 'existing'.
    If not found or markdown missing, returns 'new'.
    """
    lesson_state = load_lesson_state_from_firestore(user_id)
    parsed_markdowns = lesson_state.get('parsed_section_markdowns') if lesson_state else None
    if (
        lesson_state
        and lesson_state.get("current_lesson_plan", {}).get("topic", "").lower() == topic.lower()
        and parsed_markdowns
        and isinstance(parsed_markdowns, list)
        and len(parsed_markdowns) > 0
    ):
        session.state.update(lesson_state)
        session.state['user_id'] = user_id
        session.state['parsed_section_markdowns'] = parsed_markdowns
        return "existing"
    else:
        session.state['user_id'] = user_id
        return "new"

async def persist_session_state_to_firestore(app_name, user_id, session_id, state):
    """
    Asynchronously persists session state to Firestore by running blocking I/O
    in a separate thread to avoid blocking the event loop.
    """
    def do_persist():
        try:
            doc_id = f"{app_name}__{user_id}"
            doc_ref = session_collection.document(doc_id)
            
            print(f"[FIRESTORE DEBUG] Persisting session state for user {user_id}, session {session_id}")
            print(f"[FIRESTORE DEBUG] Document ID: {doc_id}")
            
            # Check if document already exists
            existing_doc = doc_ref.get()
            if existing_doc.exists:
                print(f"[FIRESTORE DEBUG] Session document already exists, will overwrite")
            else:
                print(f"[FIRESTORE DEBUG] Creating new session document")
            
            doc_ref.set({
                "session_id": session_id,
                "state": state,
            })
            print(f"[FIRESTORE DEBUG] Session state persisted successfully")
            
            # Verify the save
            verification_doc = doc_ref.get()
            if verification_doc.exists:
                saved_data = verification_doc.to_dict()
                print(f"[FIRESTORE DEBUG] Session verification: Document exists after save")
                print(f"[FIRESTORE DEBUG] Session verification: Saved session_id = {saved_data.get('session_id') if saved_data else 'None'}")
            else:
                print(f"[FIRESTORE DEBUG] WARNING: Session document does not exist after save attempt!")
        except Exception as e:
            # It's important to catch exceptions inside the threaded function
            print(f"[FIRESTORE ERROR] Exception in do_persist for user {user_id}: {e}")
            import traceback
            traceback.print_exc()

    try:
        await asyncio.to_thread(do_persist)
    except Exception as e:
        # This will catch errors related to threading, but not from the function itself
        print(f"[FIRESTORE ERROR] Failed to run persist_session_state_to_firestore in thread for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise the exception so we can see it in the logs

def load_session_state_from_firestore(app_name, user_id):
    doc_id = f"{app_name}__{user_id}"
    doc_ref = session_collection.document(doc_id)
    doc = doc_ref.get()
    if doc is not None and hasattr(doc, 'exists') and doc.exists:
        data = doc.to_dict() if hasattr(doc, 'to_dict') else None
        return data.get("state", {}) if data else {}
    return {}

def test_firestore_connectivity():
    """
    Test function to verify Firestore connectivity and basic operations.
    """
    try:
        print(f"[FIRESTORE TEST] Testing Firestore connectivity...")
        
        # Test basic collection access
        test_doc = lesson_collection.document("test_connection")
        test_doc.set({"test": "data", "timestamp": datetime.now().isoformat()})
        print(f"[FIRESTORE TEST] Write test successful")
        
        # Test read
        doc = test_doc.get()
        if doc.exists:
            data = doc.to_dict()
            print(f"[FIRESTORE TEST] Read test successful: {data}")
        else:
            print(f"[FIRESTORE TEST] WARNING: Read test failed - document not found")
        
        # Clean up test document
        test_doc.delete()
        print(f"[FIRESTORE TEST] Cleanup test successful")
        print(f"[FIRESTORE TEST] All Firestore tests passed!")
        return True
        
    except Exception as e:
        print(f"[FIRESTORE TEST] ERROR: Firestore connectivity test failed: {e}")
        import traceback
        traceback.print_exc()
        return False