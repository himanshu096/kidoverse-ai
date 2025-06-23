# This file will contain the Pydantic models for the application. 

from pydantic import BaseModel, Field, conlist
from typing import List, Optional, Annotated

# Define the input schema for the lesson planner
class PlanLessonInput(BaseModel):
    topic: str = Field(description="The topic for which to create a lesson plan.")
    user_learning_context: Optional[dict] = Field(None, description="Optional context about what the user already knows, including completed topics, grade level, and interests.")

class LessonSection(BaseModel):
    title: str = Field(..., description="The title of this lesson section (e.g., 'Hook', 'Main Content', 'Activity').")
    duration_minutes: int = Field(..., description="The estimated duration of this section in minutes.", ge=1, le=60)
    content: str = Field(..., description="The detailed content to be covered in this section, presented as bullet points or a narrative.")
    activity: str = Field(..., description="A practical activity or exercise for students in this section.")
    image_prompt: Optional[str] = Field(None, description="A clear, concise, child-friendly DALL-E/Imagen prompt for an image to accompany this section. Must be suitable for educational illustration.")

class WrapUp(BaseModel):
    title: str = Field(..., description="The title of the wrap-up section (e.g., 'Review & Celebrate').")
    duration_minutes: int = Field(..., description="The estimated duration of the wrap-up in minutes.", ge=1, le=30)
    content: str = Field(..., description="Summary of key learnings and main takeaways for the wrap-up.")
    activity: str = Field(..., description="A concluding activity or discussion for the wrap-up.")
    image_prompt: Optional[str] = Field(None, description="A clear, concise, child-friendly DALL-E/Imagen prompt for an image to accompany the wrap-up.")

class LessonPlan(BaseModel):
    topic: str = Field(..., description="The specific topic of the lesson plan.")
    duration_minutes: int = Field(..., description="The total estimated duration of the lesson plan in minutes (sum of all sections and wrap-up).", ge=5, le=120)
    grade_level: str = Field(..., description="The target grade level or age range for this lesson (e.g., 'Ages 6-10', 'Elementary', 'Middle School').")
    learning_objectives: List[str] = Field(..., description="A list of clear, measurable learning objectives for the lesson.")
    sections: Annotated[List[LessonSection], Field(..., min_length=2, description="A list of distinct sections making up the main body of the lesson plan.")]
    wrap_up: WrapUp = Field(..., description="The concluding section of the lesson plan.")

class LessonPlanOutput(BaseModel):
    topic: str
    duration_minutes: int
    grade_level: str
    learning_objectives: list[str]
    sections: list[dict] # Consider defining a nested Section model for better type safety
    wrap_up: dict # Consider defining a nested WrapUp model
    
    
class SendCurrentSectionMarkdownInput(BaseModel):
    section_index: int = Field(description="The 0-based index of the section whose Markdown content is being sent. For wrap-up, use total_sections_count.")
    markdown_content: str = Field(description="The Markdown content for the specific lesson section.")

class PresentationInput(BaseModel):
    lesson_plan: LessonPlan = Field(description="The JSON lesson plan to convert to Markdown.")
    