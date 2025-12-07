# Ansible Automation Platform AI Assistant

An intelligent AI assistant for managing and interacting with Ansible Automation Platform (AAP) through natural language conversations. Built with LangChain, FastAPI, and the Model Context Protocol (MCP).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3.7-orange.svg)](https://langchain.com/)

## 🌟 Features

- **Natural Language Interface**: Interact with AAP using conversational AI
- **Human-in-the-Loop**: Tool execution requires user confirmation for safety
- **Secure Authentication**: AAP OAuth tokens or basic auth integration
- **Comprehensive AAP Management**: Create and manage:
  - Organizations
  - Users  
  - Credentials
  - Inventories
  - Projects
  - Job Templates
- **Real-time Communication**: WebSocket-based chat interface with multi-line input support
- **Security-First**: Automatic redaction of sensitive information (tokens, passwords)
- **Multi-Model AI**:
  - Llama 4 Scout for implementation planning
  - Qwen R1 for reasoning and tool extraction
- **Agentic Workflow**: LangGraph-based agent with human approval checkpoints
- **Professional Code Quality**:
  - PEP 8 compliant
  - Comprehensive type hints
  - Safe parsing (no `eval()`)
  - Centralized configuration

## 📋 Prerequisites

- **Python 3.10+**
- **Ansible Automation Platform** instance (v2.x)
- **API Keys** for LLM models:
  - Llama 4 Scout (for implementation planning)
  - Qwen R1 (for reasoning and tool extraction)
- **MCP Server** running

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd talk-aap
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

All required dependencies are specified with pinned versions for reproducibility.

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
# AAP Configuration
AAP_HOST=192.168.122.20
AAP_BASE_URL=https://192.168.122.20/api/controller/v2/
AAP_VERIFY_SSL=False

# MCP Server Configuration
MCP_HOST=localhost
MCP_PORT=8000

# LLM API Keys (Required)
LLAMA_API_KEY=your_llama_api_key_here
QWEN_API_KEY=your_qwen_api_key_here

# Optional: Custom Model URLs
# LLAMA_BASE_URL=https://your-llama-endpoint.com/v1
# QWEN_BASE_URL=https://your-qwen-endpoint.com/v1

# Agent Configuration
MAX_ITERATIONS=8
RECURSION_LIMIT=300
SESSION_EXPIRY_HOURS=24

# Logging
LOG_LEVEL=INFO
DEBUG=False
```

**Note**: Legacy environment variable names (`LLMA_KEY`, `QWEN_KEY`) are still supported.

### 4. Start the MCP Server

```bash
cd mcp-server
chmod +x start
./start
```

The MCP server will start on `http://localhost:8000`

### 5. Start the Main Application

```bash
cd aap
chmod +x start
./start
```

The application will be available at `http://localhost:8080`

### 6. Access the Application

1. Open your browser to `http://localhost:8080`
2. Login with your AAP credentials
3. Start chatting with the AI assistant!

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────┐
│             Web Browser (Client)                │
│  - Login Page (AAP Authentication)              │
│  - Chat Interface (WebSocket)                   │
│  - Multi-line Input (Enter for new line)        │
└────────────────┬────────────────────────────────┘
                 │ WebSocket + HTTPS
                 │
┌────────────────▼────────────────────────────────┐
│          FastAPI Application                    │
│  - AAPAssistantAgent (LangGraph Agent)          │
│  - Session Management (user_sessions)           │
│  - WebSocket Handler                            │
│  - Route Handlers                               │
└────────────────┬────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼──────────┐    ┌────────▼────────────────┐
│   LLM Models │    │   MCP Server (SSE)      │
│              │    │  - Tool Definitions     │
│ Llama 4      │    │  - Job Execution        │
│ (Planning)   │    │  - Result Formatting    │
│              │    └────────┬────────────────┘
│ Qwen R1      │             │
│ (Reasoning)  │             │
└──────────────┘    ┌────────▼────────────────┐
                    │  Ansible Playbooks      │
                    │  - AAP Operations       │
                    │  - Resource Management  │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  Ansible Automation     │
                    │  Platform (AAP)         │
                    │  - REST API             │
                    │  - Organizations        │
                    │  - Projects, Users      │
                    │  - Job Templates        │
                    └─────────────────────────┘
```

### Agent Workflow (LangGraph)

```
User Input
    │
    ▼
┌──────────────────────┐
│ summarize_user_input │  Step 1: Preprocess query
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────┐
│generate_implementation_  │  Step 2: Generate plan
│         plan             │  (Llama 4 Scout)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────┐
│ analyze_ai_response  │  Step 3: Extract tool calls
└──────────┬───────────┘  (Qwen R1 Reasoning)
           │
           ▼
    ┌──────────────┐
    │should_execute│  Step 4: Determine intent
    │   _tools?    │  (Qwen R1 Reasoning)
    └──┬──────┬────┘
       │      │
    NO │      │ YES
       │      │
       ▼      ▼
    END   ┌──────────────────────┐
          │ handle_human_approval│  Step 5: User confirmation
          └──────────┬───────────┘
                     │
                  YES│ NO
                     │  └─→ Cancel & END
                     ▼
          ┌──────────────────┐
          │   take_action    │  Step 6: Execute tools
          │  (MCP Server)    │
          └──────────┬───────┘
                     │
                     ▼
          ┌──────────────────┐
          │  Tool Results    │
          └──────────┬───────┘
                     │
                     ▼
              Back to Step 2
           (or END if complete)
```

## 🔑 Core Components

### Main Classes

#### `AAPAssistantAgent`
The main LangGraph-based agent that orchestrates the conversation and tool execution.

**Key Methods**:
- `summarize_user_input()`: Preprocesses user queries
- `generate_implementation_plan()`: Generates plans using Llama 4
- `analyze_ai_response()`: Extracts tool calls using Qwen R1
- `should_take_action()`: Determines next action (routing)
- `take_action()`: Executes tools via MCP
- `connect_to_servers()`: Establishes MCP connections

#### `ConnectionManager`
Manages WebSocket connections for real-time communication.

**Methods**:
- `connect()`: Accept new WebSocket
- `disconnect()`: Remove WebSocket
- `send_personal_json()`: Send JSON to specific client
- `send_personal_text()`: Send text to specific client

#### `AgentState`
TypedDict defining the agent's state:
- `messages`: Conversation history
- `search_count`: Tool execution iteration counter
- `user_input`: User query history
- `config`: Configuration including AAP tokens

### Key Functions

**Session Management**:
- `authenticate_with_aap()`: AAP authentication with token or basic auth
- `create_session()`: Create user session with AAP token
- `verify_session()`: Validate session token and expiry
- `get_username_from_session()`: Retrieve username from session
- `get_aap_token_from_session()`: Retrieve AAP credentials from session

**WebSocket Handlers**:
- `websocket_endpoint()`: Main WebSocket connection handler
- `handle_human_approval()`: Human-in-the-loop approval flow
- `send_tool_calls_for_approval()`: Display tool calls to user
- `get_user_confirmation()`: Get user yes/no response
- `process_tool_results()`: Format and send tool execution results

**AI Decision Making**:
- `should_execute_tools()`: Determine if AI response indicates tool execution

**Route Handlers**:
- `serve_login_page()`: Serve login page
- `login()`: Handle AAP authentication
- `chat_page()`: Serve chat interface
- `logout()`: Handle user logout

## 🔐 Security Features

### Authentication
- ✅ Users authenticate with AAP credentials
- ✅ Session tokens with configurable expiry (24 hours default)
- ✅ Support for OAuth tokens and basic auth
- ✅ Secure session storage with automatic cleanup
- ✅ Session validation on every WebSocket message

### Data Protection
- ✅ **Multi-layer redaction** of sensitive data:
  - Tokens, passwords, API keys
  - Authentication headers (Bearer, Basic)
  - JWT tokens
  - Base64-encoded credentials
- ✅ **Redaction applied at**:
  - Tool call parameters before sending to UI
  - Tool results before displaying
  - AI responses before sending to client
  - Log messages
- ✅ **Safe parsing**: Uses `ast.literal_eval()` instead of dangerous `eval()`
- ✅ SSL/TLS support for AAP connections
- ✅ No credentials in version control
- ✅ `.gitignore` configured to exclude sensitive files

### Safe Tool Execution
- ✅ Human approval required for ALL tool executions
- ✅ Clear display of tool actions (with redacted sensitive params)
- ✅ Ability to cancel operations before execution
- ✅ Tool execution happens server-side, not client-side
- ✅ Job monitoring with timeout protection

### Code Security
- ✅ Custom exception classes for better error handling
- ✅ Comprehensive type hints throughout codebase
- ✅ Input validation and sanitization
- ✅ See `playbooks/SECURITY.md` for credential management best practices

## 📖 Usage Guide

### Chat Interface

The chat interface provides an intuitive multi-line input experience:

**How to Use**:
- **Type your message**: Enter text in the input box
- **Press `Enter`**: Adds a new line (multi-line support)
- **Click `Send` button**: Submits your complete message
- **Resize text box**: Drag bottom-right corner to adjust size

**Example Multi-line Input**:
```
Create a new user with these details:
[Press Enter]
Username: john_doe
[Press Enter]
Email: john@example.com
[Press Enter]
Make them a superuser
[Click Send]
```

### Example Conversations

#### List All Organizations

```
User: What organizations do we have?
Assistant: I will list all organizations in your AAP instance.

[Tool Execution Requires Approval]
Tool: list_organizations

[User clicks "Yes"]

Results:
- **DevOps Team** (ID: 1)
- **Production Infrastructure** (ID: 2)
- **QA Environment** (ID: 3)
```

#### Create a New User

```
User: Create a user named john_doe with email john@example.com

Assistant: I will create a new user with the following details:
- Username: john_doe
- Email: john@example.com

[Tool Execution Requires Approval]
Tool: create_user
Parameters:
  - username: john_doe
  - email: john@example.com

[User clicks "Yes"]

Success! User john_doe created successfully.
```

#### Launch a Job Template

```
User: Run the "Deploy Application" job template

Assistant: I will launch the "Deploy Application" job template.

[Tool Execution Requires Approval]
Tool: launch_job_template
Parameters:
  - template_name: Deploy Application

[User clicks "Yes"]

Job launched successfully!
Job ID: 12345
Status: Running
Monitoring job...

Job completed successfully!
```

## 🛠️ Development

### Project Structure

```
talk-aap/
├── aap/                              # Main application
│   ├── aap-MaaS.py                  # FastAPI app & AAPAssistantAgent
│   ├── config.py                    # Centralized configuration
│   ├── logger.py                    # Logging setup
│   ├── exceptions.py                # Custom exceptions
│   ├── start                        # Startup script
│   │
│   ├── static/                      # Static assets
│   │   └── Red-Hat.png             # Red Hat logo
│   │
│   ├── templates/                   # HTML templates
│   │   ├── login.html              # AAP login page
│   │   └── chat-aap.html           # Chat interface
│   │
│   └── utilities/                   # Utility modules
│       ├── mcp_connection.py       # MCP server connection
│       ├── prompts_aap.py          # System prompts
│       ├── decision_prompts.py     # Tool execution decision
│       └── tool_call_utils.py      # Tool parsing & validation
│
├── mcp-server/                      # MCP Server
│   ├── aap-mcp.py                  # MCP server & tool definitions
│   └── start                        # MCP startup script
│
├── playbooks/                       # Ansible playbooks
│   ├── create_aap_credential.yaml
│   ├── create_aap_inventory.yml
│   ├── create_aap_job_template.yml
│   ├── create_aap_org.yaml
│   ├── create_aap_project.yml
│   ├── create_aap_user.yml
│   ├── list_aap_credentials.yml
│   ├── list_aap_inventories.yml
│   ├── list_aap_job_templates.yml
│   ├── list_aap_org.yaml
│   ├── list_aap_projects.yml
│   ├── list_aap_users.yml
│   └── SECURITY.md                  # Security best practices
│
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Git exclusions
│
├── README.md                        # This file
├── CHANGELOG.md                     # Version history
├── IMPROVEMENTS_SUMMARY.md          # Code quality improvements
├── CLEANUP_SUMMARY.md               # Unused code removal
├── VARIABLE_NAMING_IMPROVEMENTS.md  # Variable naming details
└── FUNCTION_CLASS_NAME_IMPROVEMENTS.md  # Function/class naming
```

### Adding New MCP Tools

#### 1. Define Tool in MCP Server

Edit `mcp-server/aap-mcp.py`:

```python
@mcp.tool()
def my_new_aap_tool(
    param1: str,
    param2: int,
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    Description of what your tool does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        aap_token: AAP authentication token (auto-injected)
        auth_type: Authentication type (auto-injected)
        aap_base_url: AAP base URL (auto-injected)
        username: Username for basic auth (auto-injected)
    
    Returns:
        JSON string with execution results
    """
    # Your implementation
    job_id = JOB_TEMPLATE_IDS.get("my_new_tool")
    # Launch job, monitor, return results
    ...
```

#### 2. Create Ansible Playbook

Create `playbooks/my_new_playbook.yml`:

```yaml
---
- name: My New AAP Operation
  hosts: localhost
  gather_facts: false
  
  tasks:
    - name: Perform operation via AAP API
      uri:
        url: "{{ controller_url }}/api/v2/resource/"
        method: POST
        headers:
          Authorization: "Bearer {{ aap_token }}"
        body_format: json
        body:
          name: "{{ resource_name }}"
        validate_certs: "{{ verify_ssl }}"
      register: result
    
    - name: Display result
      debug:
        var: result
```

#### 3. Update Configuration

Add job template ID to `aap/config.py`:

```python
JOB_TEMPLATE_IDS = {
    # ... existing templates ...
    "my_new_tool": 99,  # Your template ID
}
```

#### 4. Create Job Template in AAP

1. Go to AAP UI → Resources → Templates
2. Click "+ Add" → "Job Template"
3. Configure:
   - Name: "My New Tool"
   - Project: Your project
   - Playbook: `my_new_playbook.yml`
   - Inventory: Your inventory
4. Note the ID from the URL
5. Update `config.py` with this ID

### Code Quality Tools

```bash
# Linting
ruff check .

# Formatting
black .

# Type checking
mypy aap/ mcp-server/

# Security scanning
bandit -r aap/ mcp-server/
```

### Running Tests

```bash
# Unit tests (if added)
pytest tests/

# Integration tests (if added)
pytest tests/integration/
```

## 🔧 Configuration Reference

### Job Template IDs

The application uses specific job template IDs defined in `aap/config.py`. Update these to match your AAP instance:

```python
JOB_TEMPLATE_IDS = {
    "create_organization": 35,
    "list_organizations": 37,
    "create_user": 38,
    "list_users": 40,
    "create_credential": 41,
    "list_credentials": 43,
    "create_inventory": 44,
    "list_inventories": 46,
    "create_project": 47,
    "list_projects": 49,
    "create_job_template": 50,
    "list_job_templates": 52,
}
```

**Finding Template IDs in AAP**:
1. Navigate to Resources → Templates
2. Click on a job template
3. Check the URL: `/templates/job_template/{ID}/details`

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AAP_HOST` | No | `192.168.122.20` | AAP hostname/IP |
| `AAP_BASE_URL` | No | Auto-generated | Full AAP API URL |
| `AAP_VERIFY_SSL` | No | `False` | Verify SSL certificates |
| `MCP_HOST` | No | `localhost` | MCP server host |
| `MCP_PORT` | No | `8000` | MCP server port |
| `LLAMA_API_KEY` | **Yes** | - | Llama model API key |
| `QWEN_API_KEY` | **Yes** | - | Qwen model API key |
| `LLAMA_BASE_URL` | No | Default | Llama API endpoint |
| `QWEN_BASE_URL` | No | Default | Qwen API endpoint |
| `MAX_ITERATIONS` | No | `8` | Max tool execution iterations |
| `RECURSION_LIMIT` | No | `300` | LangGraph recursion limit |
| `SESSION_EXPIRY_HOURS` | No | `24` | Session timeout in hours |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `DEBUG` | No | `False` | Enable debug mode |

## 🐛 Troubleshooting

### MCP Server Connection Issues

**Symptom**: "Failed to connect to MCP server"

**Solutions**:
1. Verify MCP server is running:
   ```bash
   curl http://localhost:8000/sse
   ```
2. Check `MCP_HOST` and `MCP_PORT` in `.env`
3. Review MCP server logs
4. Ensure no firewall blocking port 8000

### AAP Authentication Failures

**Symptom**: Login fails or "Invalid credentials"

**Solutions**:
1. Verify AAP credentials are correct
2. Check `AAP_HOST` and `AAP_BASE_URL` in `.env`
3. Ensure AAP is accessible:
   ```bash
   curl -k https://your-aap-host/api/v2/ping/
   ```
4. Check if account is locked in AAP
5. Try with `AAP_VERIFY_SSL=False` if SSL issues

### LLM API Errors

**Symptom**: "API key error" or "Model not found"

**Solutions**:
1. Verify API keys in `.env`:
   - `LLAMA_API_KEY`
   - `QWEN_API_KEY`
2. Check API endpoints are accessible
3. Verify API key permissions and quotas
4. Review application logs for specific errors

### WebSocket Connection Drops

**Symptom**: Chat disconnects or messages not sending

**Solutions**:
1. Check browser console for errors
2. Verify session token is valid
3. Try refreshing and logging in again
4. Check for network proxy/firewall issues
5. Review server logs for WebSocket errors

### Tool Execution Hangs

**Symptom**: Tool execution never completes

**Solutions**:
1. Check AAP job status in AAP UI
2. Verify playbook exists and is correct
3. Check job template configuration
4. Review playbook logs in AAP
5. Ensure job template IDs in `config.py` are correct

### Session Expired

**Symptom**: "Session expired" or "Invalid session"

**Solutions**:
1. Login again
2. Adjust `SESSION_EXPIRY_HOURS` in `.env`
3. Check server time/timezone settings

## 📚 Code Quality Improvements

This project has undergone comprehensive code quality improvements. See detailed documentation:

- **`IMPROVEMENTS_SUMMARY.md`**: Overall code quality improvements
  - Security fixes (removed hard-coded secrets, unsafe `eval()`)
  - Dependency management
  - Centralized configuration
  - Custom exceptions

- **`CLEANUP_SUMMARY.md`**: Unused code removal
  - Removed unused variables
  - Removed unused imports
  - Removed unused prompt templates

- **`VARIABLE_NAMING_IMPROVEMENTS.md`**: Variable naming improvements
  - PEP 8 compliance
  - More descriptive names
  - Consistent naming patterns

- **`FUNCTION_CLASS_NAME_IMPROVEMENTS.md`**: Function and class naming
  - PEP 8 compliant class names (PascalCase)
  - Descriptive function names
  - Boolean naming patterns
  - Action handler patterns

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Follow PEP 8 style guide
5. Add type hints
6. Add tests if applicable
7. Run linters and formatters
8. Commit with clear messages
9. Push and submit a pull request

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all functions/classes
- Keep functions focused and small
- Use descriptive variable names

## 📜 License

[Specify your license here]

## 🙏 Acknowledgments

- **LangChain** - For the agentic framework
- **FastAPI** - For the modern web framework
- **Ansible Automation Platform** - For automation capabilities
- **Model Context Protocol (MCP)** - From Anthropic
- **Qwen** and **Llama** - For powerful LLM models

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Contact: [Your contact information]

## 🎯 Roadmap

### Planned Features
- [ ] Additional AAP resource support (workflow templates, surveys)
- [ ] Enhanced error recovery
- [ ] Conversation history persistence
- [ ] Multi-user support with role-based access
- [ ] Audit logging
- [ ] Integration with additional LLM providers
- [ ] Web-based configuration UI
- [ ] Automated testing suite

---

**Important**: This is an AI-powered tool that interacts with production systems. Always:
- Review tool actions before approval
- Test in non-production environments first
- Follow your organization security policies
- Keep API keys and credentials secure
- Monitor tool executions
- Review logs regularly

**Version**: 1.0.0 (with code quality improvements)

**Last Updated**: December 2025
