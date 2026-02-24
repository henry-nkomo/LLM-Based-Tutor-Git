from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any, Sequence, Literal
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class mainState(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
        extra='allow'  # Allow extra fields
    )
    username: Optional[str] = None
    user_message: Optional[str] = None
    user_id: Optional[int] = None
    ai_response: Optional[str] = None
    history: Optional[List[dict]] = None
    delagatee: Optional[str] = None
    skill_component: Optional[Dict[str,Any]] = None
    target_skill: Optional[str] = None
    attempts: Optional[int] = 0
    feedback: Optional[str] = None
    mark: Optional[int] = None
    status: Optional[str] = None
    current_state: Optional[str] = None
    current_tutor_message: Optional[str] = None
    current_question: Optional[str] = None
    messages: Annotated[Sequence[BaseMessage], add_messages] = []


class generalChat(BaseModel):
    user_message: str
    username: str
    user_id: Optional[int] = None
    dashboard_history: Optional[List[dict]] = None
    message: Optional[str] = None
    ai_message: Optional[Any] = None
    messages: Annotated[Sequence[BaseMessage], add_messages] = []  # LangGraph message management
    
    class Config:
        arbitrary_types_allowed = True

class DiagnosisQueries(BaseModel):
    queries: List[str] = Field(description="List of diagnosis statements", max_length=4)