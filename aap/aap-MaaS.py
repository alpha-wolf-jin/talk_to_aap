#!/usr/bin/env python3

import os
import re
import json
import asyncio
from typing import TypedDict, Annotated, List, Dict, Any
from uuid import uuid4
from contextlib import AsyncExitStack

from dotenv import load_dotenv

from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import InMemorySaver

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import secrets
from datetime import datetime, timedelta
import requests
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from utilities.mcp_connection import connect_to_server, connect_to_servers
from utilities.prompts_aap import tools_assistant_prompt, extract_tool_call_prefix, extract_tool_call_suffix
from utilities.tool_call_utils import create_ai_message_with_tool_calls


# Constants
MAX_ITERATIONS = 8
RECURSION_LIMIT = 300
CONFIRMATION_MESSAGE_ID = "confirm_123"
SEPARATOR_LENGTH = 39
AAP_BASE_URL = "https://192.168.122.20/api/controller/v2/"

# Load environment variables
load_dotenv()

# Initialize LLM models
LLAMA_API_KEY = os.environ.get('LLMA_KEY')
llama_model = ChatOpenAI(
    model="llama-4-scout-17b-16e-w4a16",
    temperature=0,
    api_key=LLAMA_API_KEY,
    base_url="https://llama-4-scout-17b-16e-w4a16-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443/v1"
)

QWEN_API_KEY = os.environ.get('QWEN_KEY')
qwen_reasoning_model = ChatOpenAI(
    model="r1-qwen-14b-w4a16",
    temperature=0,
    api_key=QWEN_API_KEY,
    base_url="https://deepseek-r1-qwen-14b-w4a16-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443/v1"
)

# Initialize memory and FastAPI app
checkpoint_memory = InMemorySaver()
app = FastAPI()

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Authentication models and storage
class LoginRequest(BaseModel):
    username: str
    password: str

# Session storage
user_sessions = {}

def authenticate_with_aap(username: str, password: str) -> dict:
    """
    Authenticate with Ansible Automation Platform and retrieve token.
    
    Args:
        username: AAP username
        password: AAP password
        
    Returns:
        dict with 'success' (bool), 'token' (str if success), 'message' (str)
    """
    try:
        # AAP uses basic auth to get a token
        auth_url = f"{AAP_BASE_URL}tokens/"
        
        # Try to get existing token or create new one
        response = requests.post(
            auth_url,
            auth=(username, password),
            json={
                "description": "AAP AI Helper Session",
                "application": None,
                "scope": "write"
            },
            verify=False,  # For self-signed certificates
            timeout=10
        )
        
        if response.status_code == 201:
            # Token created successfully
            token_data = response.json()
            aap_token = token_data.get('token')
            return {
                "success": True,
                "token": aap_token,
                "message": "Authentication successful"
            }
        elif response.status_code == 401:
            return {
                "success": False,
                "token": None,
                "message": "Invalid username or password"
            }
        else:
            # Try alternative: direct API call to verify credentials
            # Some AAP versions might not support token creation
            test_url = f"{AAP_BASE_URL}me/"
            test_response = requests.get(
                test_url,
                auth=(username, password),
                verify=False,
                timeout=10
            )
            
            if test_response.status_code == 200:
                # Credentials valid, store basic auth
                import base64
                basic_auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                return {
                    "success": True,
                    "token": basic_auth,
                    "message": "Authentication successful (basic auth)",
                    "auth_type": "basic"
                }
            else:
                return {
                    "success": False,
                    "token": None,
                    "message": f"AAP authentication failed: {response.status_code}"
                }
                
    except requests.exceptions.RequestException as e:
        print(f"AAP connection error: {str(e)}")
        return {
            "success": False,
            "token": None,
            "message": f"Cannot connect to AAP: {str(e)}"
        }
    except Exception as e:
        print(f"AAP authentication error: {str(e)}")
        return {
            "success": False,
            "token": None,
            "message": f"Authentication error: {str(e)}"
        }

def create_session(username: str, aap_token: str, auth_type: str = "token") -> str:
    """
    Create a new session for a user with AAP token.
    
    Args:
        username: AAP username
        aap_token: AAP authentication token or basic auth string
        auth_type: Type of authentication ("token" or "basic")
        
    Returns:
        Session token string
    """
    token = secrets.token_urlsafe(32)
    user_sessions[token] = {
        "username": username,
        "aap_token": aap_token,
        "auth_type": auth_type,
        "created_at": datetime.now()
    }
    return token

def verify_session(token: str) -> bool:
    """Verify if a session token is valid."""
    if token in user_sessions:
        # Optional: Check if session is expired (e.g., after 24 hours)
        created_at = user_sessions[token]["created_at"]
        if datetime.now() - created_at > timedelta(hours=24):
            del user_sessions[token]
            return False
        return True
    return False

def get_username_from_session(token: str) -> str:
    """Get username from session token."""
    if token in user_sessions:
        return user_sessions[token]["username"]
    return None

def get_aap_token_from_session(token: str) -> tuple:
    """
    Get AAP token from session token.
    
    Returns:
        tuple: (aap_token, auth_type) or (None, None)
    """
    if token in user_sessions:
        return user_sessions[token].get("aap_token"), user_sessions[token].get("auth_type", "token")
    return None, None

def make_aap_api_call(endpoint: str, aap_token: str, auth_type: str = "token", method: str = "GET", data: dict = None) -> dict:
    """
    Make an authenticated API call to Ansible Automation Platform.
    
    Args:
        endpoint: API endpoint path (e.g., "jobs/", "inventories/")
        aap_token: AAP authentication token or basic auth string
        auth_type: Type of authentication ("token" or "basic")
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Request body data (for POST/PUT)
        
    Returns:
        dict: API response data
    """
    url = f"{AAP_BASE_URL}{endpoint}"
    
    headers = {}
    auth = None
    
    if auth_type == "token":
        headers["Authorization"] = f"Bearer {aap_token}"
    elif auth_type == "basic":
        headers["Authorization"] = f"Basic {aap_token}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, verify=False, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, verify=False, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, verify=False, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, verify=False, timeout=30)
        else:
            return {"error": f"Unsupported HTTP method: {method}"}
        
        if response.status_code in [200, 201, 202, 204]:
            if response.content:
                return response.json()
            else:
                return {"status": "success", "status_code": response.status_code}
        else:
            return {
                "error": f"AAP API call failed",
                "status_code": response.status_code,
                "message": response.text
            }
            
    except Exception as e:
        return {
            "error": f"AAP API call exception: {str(e)}"
        }


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.remove(websocket)
    
    async def send_personal_json(self, data: dict, websocket: WebSocket):
        """Send JSON data to a specific WebSocket."""
        await websocket.send_json(data)
    
    async def send_personal_text(self, message: str, websocket: WebSocket):
        """Send text message to a specific WebSocket."""
        await websocket.send_text(message)

#####################################################

#########
# Agentic
#########

def reduce_messages(left: list[AnyMessage], right: list[AnyMessage]) -> list[AnyMessage]:
    """Merge new messages with existing messages, replacing duplicates by ID."""
    # Assign ids to messages that don't have them
    for message in right:
        if not message.id:
            message.id = str(uuid4())

    # Merge the new messages with the existing messages
    merged = left.copy()
    for message in right:
        for i, existing in enumerate(merged):
            # Replace any existing messages with the same id
            if existing.id == message.id:
                merged[i] = message
                break
        else:
            # Append any new messages to the end
            merged.append(message)
    return merged

class AgentState(TypedDict):
    """State definition for the agent, tracking message history."""
    messages: Annotated[list[AnyMessage], reduce_messages]
    search_count: int
    user_input: Annotated[list[str], lambda x, y: x + y]
    config: dict  # Add config to state for AAP token access


class AAPAssistantAgent:
    """LangGraph-based AAP assistant agent for automation tasks."""
    
    def __init__(self, model: ChatOpenAI, checkpointer: InMemorySaver, max_iterations: int = 3):
        """
        Initialize the research assistant.
        
        Args:
            model: LLM model to use
            checkpointer: Memory checkpointer for state persistence
            max_iterations: Max number of calling web search tool
        """
        self.llm = model
        self.model = model
        self.max_iterations = max_iterations
        self.system_prompt = " "
        self.checkpointer = checkpointer
        self.graph = self._build_graph()
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, Any] = {}
        self.llm_with_tools = None
        self.available_prompts: List[str] = []
        self.available_tools: List[str] = []
        self.service_description: str = ''
        self.separator: str = "\n" + "-" * SEPARATOR_LENGTH + "\n"
        self.all_tools: List[str] = []
        self.tool_prompt = SystemMessage(content=tools_assistant_prompt)


    async def connect_to_server(self, server_name: str, server_config: Dict[str, Any]):
        """Connect to a specific MCP server."""
        await connect_to_server(self, server_name, server_config)

    async def connect_to_servers(self):
        """Connect to all configured MCP servers."""
        await connect_to_servers(self)

    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph state machine."""
        graph = StateGraph(AgentState)

        graph.add_node("sum", self.summarize_user_input)
        graph.add_node("llm", self.generate_implementation_plan)
        graph.add_node("check", self.analyze_ai_response)
        graph.add_node("action", self.take_action)
        
        graph.add_edge(START, "sum")
        graph.add_edge("sum", "llm")
        graph.add_edge("llm", "check")
        graph.add_conditional_edges(
            "check",
            self.should_take_action,
            {"tool": "action", "sum": "sum", "end": END},
        )
        
        graph.add_edge("action", "llm")
        
        result = graph.compile(checkpointer=self.checkpointer, interrupt_before=["action"])
        
        return result

    def should_take_action(self, state: AgentState) -> str:
        """Check if we should continue or terminate."""
        messages = state['messages']
 
        print('--'*10, f"Len messag: {len(messages)}", '--'*10)
        print('--'*10, f"SearchCount: {state['search_count']}", '--'*10)
        
        # Stop conditions
        if state['search_count'] >= self.max_iterations:
            return 'end'

        last_msg = messages[-1]
        if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
            return 'end'
       
        if last_msg.tool_calls:
            return 'tool'


    def analyze_ai_response(self, state: AgentState) -> dict:
        """Analyze AI response and extract tool calls if needed."""
        print('***'*30)
        print("\n\nFrom analyze_ai_response - Tool Execution Agent\n\n")
        print('***'*30)
        print("--"*20, "From analyze_ai_response", "--"*20)

        # If call_llm already generated tool calls, no further analysis needed
        tool_calls = state['messages'][-1].tool_calls
        if len(tool_calls) > 0:
            print("Implement Agent directly created tool call.")
            return {'status': 'pass'}

        messages = state['messages']
        message = messages[-1]
        ai_response_content = f"{message.content}"
        should_execute = should_execute_tools(ai_response_content, self.all_tools)
        
        if should_execute:
            context = extract_tool_call_prefix + "\n" + self.service_description + "\n<messages>\n" + ai_response_content + "\n" + extract_tool_call_suffix

            response = qwen_reasoning_model.invoke(context)
            print('$$'*40)
            print(response.content)
            print('$$'*40)

            print('--'*20, 'extract tool call', '--'*20)

            match = re.search(r"(\[.*\])", f"{response.content}", re.DOTALL)

            if match:
                content = match.group(1).strip()
                print(content)
           
                ai_message, is_valid = create_ai_message_with_tool_calls(
                    content,
                    content=""
                )
                if is_valid:
                    return {'messages': [ai_message]}

        print("--"*20, "From analyze_ai_response", "--"*20)
        return {'status': 'pass'}

    def generate_implementation_plan(self, state: AgentState) -> dict:
        """Generate implementation plan using LLM based on user input."""
        messages = state['messages']
        user_input = state['user_input']
        query = user_input[-1]
        
        print('***'*30)
        print("\n\nFrom generate_implementation_plan - Llama 4 - Advice Implementation plan Agent\n\n")
        print('***'*30)
        
        system_prompt = tools_assistant_prompt + "\n\n" + self.service_description
        self.tool_prompt = SystemMessage(content=system_prompt)
        messages = [self.tool_prompt] + messages 
        self.system_prompt = None

        response = self.llm_with_tools.invoke(messages)

        return {'messages': [response]}

    def summarize_user_input(self, state: AgentState) -> dict:
        """Preprocess and analyze user input before processing."""
        messages = state['messages']
        user_input = state['user_input']
        issue = user_input[-1]
        query = f"""
**Please analyze below user input**

User Input: {issue}
"""
        return {
                "messages": [HumanMessage(content=query)],
               }

    async def take_action(self, state: AgentState) -> dict:
        """Execute tool calls and return results."""
        tool_calls = state['messages'][-1].tool_calls
        results = []
        
        # Get AAP token from config
        config = state.get('config', {})
        configurable = config.get('configurable', {})
        aap_token = configurable.get('aap_token')
        auth_type = configurable.get('auth_type', 'token')
        username = configurable.get('username')
        
        for call in tool_calls:
            try:
                tool_name = call['name']
                tool_args = call['args']
                session = self.sessions.get(tool_name)
                
                # Inject AAP credentials into tool arguments
                if aap_token:
                    tool_args['aap_token'] = aap_token
                    tool_args['auth_type'] = auth_type
                    tool_args['aap_base_url'] = AAP_BASE_URL
                    tool_args['username'] = username
    
                print('--'*20, 'Debug for MCP', '--'*20)
                print('Tool Name:', tool_name)
                print('Tool Args (with AAP token):', {k: v if k != 'aap_token' else f"{v[:20]}..." for k, v in tool_args.items()})
                print(f'AAP Auth Type: {auth_type}')
                
                result = await session.call_tool(tool_name, arguments=tool_args)
                match = re.search(r"\[\s*'([^']+)'\s*\]", f"{result}")
                if match:
                    result = match.group(1)
                    
                print('Result:', f"\n{result}")
                print('Result Type:', type(result))
                print('--'*20, 'Debug for MCP', '--'*20)
    
                results.append(ToolMessage(
                    tool_call_id=call['id'],
                    name=call['name'],
                    content=str(result)
                ))
    
            except Exception as e:
                print(f"Tool execution failed: {str(e)}")
                results.append(ToolMessage(
                    tool_call_id=call['id'],
                    name=call['name'],
                    content=f"Tool error: {str(e)}"
                ))
        
        print("Returning to LLM for processing...")
        return {
            'messages': results,
            'search_count': state['search_count'] + 1,
        }
        
    def query(self, question: str, limit: int = 30) -> str:
        """Execute a research query."""
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=question)]},
            config={"recursion_limit": limit},
        )

        return result['messages'][-1].content

    async def cleanup(self):
        """Clean up async resources."""
        await self.exit_stack.aclose()

# Global chatbot instance
aap_chatbot = AAPAssistantAgent(
    model=llama_model,
    max_iterations=MAX_ITERATIONS,
    checkpointer=checkpoint_memory,
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    print("Start...")
    await aap_chatbot.connect_to_servers()
    app.state.manager = ConnectionManager()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    await aap_chatbot.cleanup()

@app.get("/")
async def serve_login_page(request: Request):
    """Serve the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(login_request: LoginRequest):
    """Handle user login with AAP authentication."""
    username = login_request.username
    password = login_request.password
    
    print(f"Login attempt for user: {username}")
    
    # Authenticate with AAP
    auth_result = authenticate_with_aap(username, password)
    
    if auth_result["success"]:
        # Create session token with AAP token
        auth_type = auth_result.get("auth_type", "token")
        session_token = create_session(username, auth_result["token"], auth_type)
        
        print(f"Login successful for user: {username}")
        print(f"AAP token stored in session (type: {auth_type})")
        
        return JSONResponse({
            "success": True,
            "message": auth_result["message"],
            "token": session_token
        })
    else:
        print(f"Login failed for user: {username} - {auth_result['message']}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "message": auth_result["message"]
            }
        )

@app.get("/chat")
async def chat_page(request: Request):
    """Serve the main chat page (requires authentication)."""
    # Check if user has valid session
    token = request.cookies.get("auth_token")
    if not token or not verify_session(token):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    username = get_username_from_session(token)
    return templates.TemplateResponse("chat-aap.html", {
        "request": request,
        "username": username
    })

@app.post("/logout")
async def logout():
    """Handle user logout."""
    return JSONResponse({"success": True, "message": "Logged out successfully"})

async def send_tool_calls_for_approval(websocket: WebSocket, ai_message: AIMessage) -> List[str]:
    """Send tool calls to the user for approval and return list of tool names."""
    tool_list = []
    
    try:
        for tool_call in ai_message.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            call_id = tool_call['id']

            print(f"Tool Name: {tool_name}")
            print(f"Tool Arguments: {tool_args}")
            print(f"Call ID: {call_id}")

            if tool_name not in tool_list:
                tool_list.append(tool_name)

            # Redact sensitive information before sending to user
            safe_args = {}
            sensitive_keys = ['aap_token', 'auth_type', 'aap_base_url', 'username', 'password', 'token', 'api_key', 'secret']
            
            for key, value in tool_args.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    safe_args[key] = '[REDACTED]'
                else:
                    safe_args[key] = value

            await app.state.manager.send_personal_json({
                "type": "tool_call",
                "name": tool_name,
                "args": safe_args  # Send redacted args instead of raw args
            }, websocket)
    except Exception as e:
        print(f"Error sending tool calls for approval: {str(e)}")
    
    return tool_list


async def get_user_confirmation(websocket: WebSocket) -> str:
    """Request and receive user confirmation for tool execution."""
    try:
        await app.state.manager.send_personal_json({
            "type": "confirmation_request",
            "content": "Do you want to proceed? (yes/no)",
            "message_id": CONFIRMATION_MESSAGE_ID
        }, websocket)

        data = await websocket.receive_json()

        if data.get("type") == "confirmation_response":
            return data.get("content", "").lower()
        
        return "no"
    except Exception as e:
        print(f"Error getting user confirmation: {str(e)}")
        return "no"


async def process_tool_results(event: dict, websocket: WebSocket):
    """Process and send tool execution results to the user."""
    try:
        if 'action' in event:
            result = event['action']
            # Process ALL tool messages, not just the last one
            tool_messages = result['messages'] if 'messages' in result else []
            
            for tool_message in tool_messages:
                tool_return = tool_message.content
                tool_name = getattr(tool_message, 'name', 'unknown_tool')
                print(f"Tool Message from {tool_name}:", f"{tool_return}\n\n")
                
                final_text = f"{tool_return}"
                # Use a more robust regex that handles escaped quotes and content with quotes
                # Match text='...' but handle escaped quotes properly
                match = re.search(r"text='((?:[^'\\]|\\.)*)'", tool_return)
                if match:
                    text_content = match.group(1)
                    final_text = text_content
                    
                    if text_content.startswith('[') and text_content.endswith(']'):
                        clean_text = text_content[3:-3]
                        text = clean_text.replace('\\n', '\n').replace('\\"', '"')
                        final_text = re.sub(r'^[\s"\\]+|[\s"\\]+$', '', text)
                        final_text = final_text.replace('\\', ' ')

                final_text = final_text.strip()
                
                # Redact sensitive information from tool results
                sensitive_patterns = [
                    # Specific token patterns - be aggressive
                    (r'[A-Za-z0-9]{20,}', lambda m: '[REDACTED]' if len(m.group(0)) > 25 else m.group(0)),  # Long alphanumeric strings
                    (r'aap_token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'aap_token: [REDACTED]'),
                    (r'token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'token: [REDACTED]'),
                    (r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'password: [REDACTED]'),
                    (r'api_key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'api_key: [REDACTED]'),
                    (r'Bearer\s+[A-Za-z0-9\-_.]+', 'Bearer [REDACTED]'),
                    (r'Basic\s+[A-Za-z0-9+/=]+', 'Basic [REDACTED]'),
                    # Any base64-like or jwt-like strings
                    (r'eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', '[REDACTED]'),
                ]
                
                for pattern, replacement in sensitive_patterns:
                    final_text = re.sub(pattern, replacement, final_text, flags=re.IGNORECASE)
                
                # Format tool name for display (convert snake_case to Title Case)
                display_tool_name = ' '.join(word.capitalize() for word in tool_name.split('_'))
                
                # Create a clear header with the tool name
                separator = "=" * 60
                header = f"\n{separator}\n📋 Tool Result: {display_tool_name}\n{separator}\n\n"
                
                formatted_result = header + final_text
                
                print(formatted_result)
                
                await app.state.manager.send_personal_json({
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": formatted_result
                }, websocket)
        
        if 'llm' in event:
            result = event['llm']
            if result is not None and isinstance(result, dict) and 'messages' in result:
                response = result['messages'][-1].content
                if response.strip() != '':
                    # Redact sensitive information from LLM responses
                    sensitive_patterns = [
                        # Be very aggressive with token-like patterns
                        (r'`[A-Za-z0-9_-]{20,}`', '`[REDACTED]`'),  # Tokens in backticks
                        (r'token `[^`]+`', 'token `[REDACTED]`'),
                        (r'Token: [A-Za-z0-9_-]+', 'Token: [REDACTED]'),
                        (r'[A-Za-z0-9]{25,}', '[REDACTED]'),  # Very long alphanumeric strings
                        (r'aap_token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'aap_token: [REDACTED]'),
                        (r'token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'token: [REDACTED]'),
                        (r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'password: [REDACTED]'),
                        (r'api_key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'api_key: [REDACTED]'),
                        (r'Bearer\s+[A-Za-z0-9\-_.]+', 'Bearer [REDACTED]'),
                        (r'Basic\s+[A-Za-z0-9+/=]+', 'Basic [REDACTED]'),
                        (r'eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', '[REDACTED]'),  # JWT
                    ]
                    
                    for pattern, replacement in sensitive_patterns:
                        response = re.sub(pattern, replacement, response, flags=re.IGNORECASE)
                    
                    print('--'*40)
                    print("AI Response:", f"\n{response}")
                    print('--'*40)
                    await app.state.manager.send_personal_json({
                        "type": "assistant_message",
                        "content": response
                    }, websocket)
    except Exception as e:
        print(f"Error processing tool results: {str(e)}")
        await app.state.manager.send_personal_json({
            "type": "error",
            "content": f"Error processing results: {str(e)}"
        }, websocket)


async def handle_human_approval(stream_config: dict, websocket: WebSocket):
    """Handle human-in-the-loop approval for tool execution."""
    state = aap_chatbot.graph.get_state(stream_config)
    ai_message = state.values['messages'][-1]

    print('--'*20, 'Human In Loop', '--'*20)

    # If next call is tool calls, request approval
    if hasattr(ai_message, 'tool_calls') and ai_message.tool_calls:
        await send_tool_calls_for_approval(websocket, ai_message)
        response = await get_user_confirmation(websocket)
        
        print('--'*20, f"User confirmation {response}", '--'*20)
        print("\nResponse:", f"{response}\n")
        
        if response in ["yes", "y"]:
            await app.state.manager.send_personal_json({
                "type": "assistant_message",
                "content": "Great! Proceeding with the operation..."
            }, websocket)

            # Execute the tool calls
            async for event in aap_chatbot.graph.astream(None, stream_config):
                await process_tool_results(event, websocket)
        else:
            # Cancel the tool calls
            await app.state.manager.send_personal_json({
                "type": "assistant_message",
                "content": "Operation cancelled."
            }, websocket)

            state = aap_chatbot.graph.get_state(stream_config)
            ai_message = state.values['messages'][-1]
            
            print('--'*20, 'Message to update', '--'*20)
            print(f"\n{ai_message}\n\n")
            print('--'*20, 'Message to update', '--'*20)

            # Update AI message to remove tool calling
            update_content = "Please wait for the further user input."
            state.values['messages'][-1].content = update_content
            state.values['messages'][-1].additional_kwargs = {}
            state.values['messages'][-1].response_metadata = {}
            
            # Remove the tool call: empty overwrite current tool calls
            new_msg = ai_message.model_copy(update={"tool_calls": []})
            state.values['messages'][-1] = new_msg
            
            print('--'*20, 'Cancel Message', '--'*20)
            print('Cancel MSG:', f"\n{new_msg}\n\n")
            print('--'*20, 'Cancel Message', '--'*20)

            # Update the stream 
            aap_chatbot.graph.update_state(
                stream_config,
                state.values,
                as_node="llm"
            )
            
            for event in aap_chatbot.graph.stream(None, stream_config):
                for v in event.values():
                    print(v)
                    
            print("--"*40)
            print("stream_config:", f"\n{stream_config}")
            print("--"*40)



def should_execute_tools(ai_response_content: str, tool_list: List[str]) -> bool:
    """
    Determine if the AI response indicates imminent tool execution.
    
    Args:
        ai_response_content: The AI message output to analyze
        tool_list: List of available tools
        
    Returns:
        True if tool execution is imminent, False otherwise
    """
    from utilities.decision_prompts import TOOL_EXECUTION_DECISION_PROMPT
    from langchain_core.prompts import ChatPromptTemplate
    
    # Escape curly braces to prevent ChatPromptTemplate from treating them as variables
    escaped_content = ai_response_content.replace('{', '{{').replace('}', '}}')
    
    # Format the prompt with escaped content
    formatted_prompt = TOOL_EXECUTION_DECISION_PROMPT.format(escaped_docs=escaped_content)
    
    prompt = ChatPromptTemplate.from_template(formatted_prompt)
    chain = prompt | qwen_reasoning_model
    response = chain.invoke({})

    print('$$'*40)
    print("AI Response Content:", f"\n{ai_response_content}\n\n")
    print('$$'*40)
    print("Reasoning Y/N for tool execute:", f"\n{response.content}\n\n")
    print('$$'*40)

    content = f"{response.content}"
    return 'yes' in content.lower()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for handling chat interactions."""
    await app.state.manager.connect(websocket)
    
    # Get authentication token from cookies
    auth_token = None
    if 'cookie' in websocket.headers:
        cookies = websocket.headers['cookie']
        for cookie in cookies.split(';'):
            if 'auth_token=' in cookie:
                auth_token = cookie.split('auth_token=')[1].strip()
                break
    
    # Verify session and get AAP token
    if not auth_token or not verify_session(auth_token):
        await app.state.manager.send_personal_json({
            "type": "error",
            "content": "Authentication required. Please login again."
        }, websocket)
        await websocket.close()
        return
    
    aap_token, auth_type = get_aap_token_from_session(auth_token)
    username = get_username_from_session(auth_token)
    
    print(f"WebSocket connection authenticated for user: {username}")
    print(f"AAP token available for MCP calls (type: {auth_type})")
    
    # Store AAP token in websocket for access during session
    websocket.aap_token = aap_token
    websocket.auth_type = auth_type
    websocket.username = username
    
    try:
        while True:
            # Initialize thread_id if not exists
            if not hasattr(websocket, 'thread_id'):
                websocket.thread_id = str(uuid4())
            
            thread_id = websocket.thread_id
            
            stream_config = { 
                "configurable": {
                    "thread_id": thread_id,
                    "aap_token": aap_token,
                    "auth_type": auth_type,
                    "username": username
                },
                "recursion_limit": RECURSION_LIMIT
            }
                
            data = await websocket.receive_json()
            
            print('--'*30, 'Data from Web Input', '--'*30)
            print('Raw Data From Web:', f"{data}")
            print('--'*30, 'Data from Web Input', '--'*30)
            
            if data.get("type") == "user_message":
                query = data.get("content", "")
            else:
                continue
            
            print('--'*30, 'User Input', '--'*30)
            print("Customized User Input:", f"\n{query}")
            print('--'*30, 'User Input', '--'*30)
            
            stream_args = { 
                "search_count": 0,
                "user_input": [query],
                "config": stream_config,
                # Pass config through state so it's accessible in take_action
                "messages": []
            }
            
            # Trigger Agentic processing
            try:
                for s in aap_chatbot.graph.stream(stream_args, stream_config):
                    if 'llm' in s:
                        result = s['llm']
                        if result is not None and isinstance(result, dict) and 'messages' in result:
                            response = result['messages'][-1].content
                            if response.strip() != '':
                                await app.state.manager.send_personal_json({
                                    "type": "assistant_message",
                                    "content": response
                                }, websocket)

                # Interrupt before action as defined in compiling
                while aap_chatbot.graph.get_state(stream_config).next:
                    await handle_human_approval(stream_config, websocket)
                    
            except Exception as e:
                print(f"Error in agentic processing: {str(e)}")
                await app.state.manager.send_personal_json({
                    "type": "error",
                    "content": f"An error occurred: {str(e)}"
                }, websocket)

    except WebSocketDisconnect:
        app.state.manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        try:
            app.state.manager.disconnect(websocket)
        except:
            pass


