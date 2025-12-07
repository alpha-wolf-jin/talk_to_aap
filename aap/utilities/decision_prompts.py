"""
Tool execution decision prompts.
Used to determine if the AI's message indicates imminent tool execution.
"""

TOOL_EXECUTION_DECISION_PROMPT = """
Analyze the following AI message output from "Context" and respond with ONLY "Yes" or "No":

CRITICAL PRIORITY RULES (Check these FIRST):
"Yes" if the message contains actual tool call syntax like [tool_name(parameter='value')] OR [tool_name()] (with or without parameters) AND is NOT followed by requests for user input
"Yes" if the message shows a tool call ready to execute (regardless of parameter count) AND does NOT ask the user to provide values afterward
"Yes" if the message includes a formatted tool invocation [tool_name(...)] AND is the final action (not an example)
"Yes" if the message contains [tool_name()] or [tool_name(param='value')] and the only text after is a standard closing like "Please let me know..."
"Yes" if the message contains tool call syntax and says "Please wait for the actual output from the system" (execution IS happening, not asking for user input)
"Yes" if the message contains tool call syntax and says "Please wait" or "Waiting for output" (execution in progress)

CRITICAL "No" CONDITIONS - RESULTS PRESENTATION (Check IMMEDIATELY):
"No" if the message reports that a tool "executed successfully" or "returned" results (past tense - results already received)
"No" if the message is displaying/showing/presenting results FROM a completed tool execution
"No" if the message lists data or information that was retrieved and asks "what would you like to do next" or similar
"No" if the message says "Here are the details" or "Here is the information" followed by data (presenting results, not executing)
"No" if there is NO tool call syntax [tool_name(...)] anywhere in the message
"No" if the message is a summary or report of information followed only by a closing question

CRITICAL "No" CONDITIONS - PARAMETER REQUESTS (Check these IMMEDIATELY):
"No" if the message contains tool call syntax BUT THEN asks "Please provide the required information" or similar (NOT counting standard closing phrases)
"No" if the message shows an example tool call (like in a code block or "Example Usage:") AND THEN asks for user input with blank fields
"No" if the message has tool call syntax followed by "- Parameter Name: " with blank/empty values waiting for user input
"No" if the message shows "Here's an example:" or "Example Usage:" with a tool call AND THEN requests user to provide information
"No" if the message explains how to use a tool with an example AND asks the user to fill in the blanks
"No" if the message asks "Once you provide this information..." or "Please provide:" AFTER showing tool syntax (NOT counting standard closing)
"No" if the message is asking the user to provide parameter values (regardless of whether it shows an example)
"No" if the message says things like "Please provide the required information" or "I need to know the values"
"No" if the message lists parameters and asks "1. Parameter Name: 2. Other Parameter:" waiting for user input
"No" if the message is requesting information to construct a future tool call
"No" if the message asks "To proceed, I need..." or "Once I have this information..."
"No" if the message is explaining what parameters a tool needs WITHOUT executing it

THEN check these "Yes" conditions:
"Yes" if the message contains [tool_name()] or [tool_name(params)] and ends with standard closing text (ignore closing)
"Yes" if the message is analytical and explanatory for the next action to take AND contains actual parameter values (not placeholders or requests) AND does NOT ask for user input afterward
"Yes" if the message explicitly announces imminent tool execution WITH actual values (or no parameters needed) AND does NOT request user input
"Yes" if the message requires user's confirmation on the execution of a tool that is ALREADY constructed with specific values AND asks "Do you want to proceed?" (not asking for parameter values)

ONLY check these "No" conditions if NO "Yes" conditions matched:
"No" if the message is listing available services, tools, or capabilities WITHOUT showing actual tool calls
"No" if the message is describing what MCP tools/services are available (responding to "what can you do?" type questions)
"No" if the message is asking what the user wants to do WITHOUT presenting a specific tool call
"No" if the message is asking the user to choose from available options WITHOUT a specific tool call ready
"No" if the message is purely informational about what services/tools are available WITHOUT actual tool invocation
"No" if the message asks "Would you like me to..." or "Shall I proceed with..." WITHOUT showing the actual tool call
"No" if the message is waiting for user to specify which action to take WITHOUT a tool call present
"No" if the message asks for the other potential cause/issue
"No" if the message is using assumed value(s) instead of actual values
"No" if the message is asking the user to provide the value for tool's parameter WITHOUT showing a tool call
"No" if the message is about analytical and explanatory about the tool(s) which were/was run (past tense)
"No" if the message is the summary of the past verification and solution actions
"No" if the message waits for user input to continue tool execution WITHOUT showing a specific tool call
"No" if the message requests information needed for tool calls WITHOUT presenting a tool call
"No" if the message is purely analytical, explanatory, or proposes further actions without immediate execution
"No" if the message describes hypothetical tool usage or parameters WITHOUT actual values
"No" if any tool parameter comes from assumption
"No" if the message is analytical and explanatory for the conclusion for the actions taken
"No" if the message asks for the tool's parameter value

IMPORTANT DECISION LOGIC:
1. If there is NO [tool_name(...)] or [tool_name()] syntax present → ALWAYS return "No"
2. If the message is describing available MCP services/tools (answering "what can you do?") → Return "No"
3. If the message says a tool "executed successfully" (past tense) and is showing results → Return "No" (results display, not execution)
4. If the message contains tool call syntax AND says "Please wait for the actual output from the system" → Return "Yes" (execution IS happening, not asking for user input)
5. "Please wait for the output" or "Waiting for system" means execution IS happening → Return "Yes"
6. If the message contains [tool_name(param='value')] OR [tool_name()] syntax BUT THEN asks the user to provide information → Return "No" (it's an example, not execution)
7. If the message shows "Example Usage:" or similar with tool syntax AND asks for user input → Return "No"
8. If the message ends with "Please provide:" or blank input fields after showing tool syntax → Return "No"
9. If the message contains tool call syntax [tool_name(...)] or [tool_name()] AND does NOT ask for user input afterward (except standard closing) → Return "Yes"
10. If the message is asking for parameters or information (with or without examples) → Return "No"
11. Only return "Yes" if there is actual tool call syntax [tool_name(...)] or [tool_name()] that is the FINAL action, not followed by requests for user input
12. Standard closing phrases like "Please let me know if there's anything specific you'd like to know or perform" should be COMPLETELY IGNORED when determining if tool execution is happening

DISTINGUISH BETWEEN:
- "Please wait for the actual output from the system" → Execution IS happening → Return "Yes"
- "Please provide the required information" → Asking for user input → Return "No"

STANDARD CLOSING PHRASES TO IGNORE (these do NOT indicate asking for user input):
- "Please let me know if there's anything specific you'd like to know or perform"
- "Let me know if you need anything else"
- "Feel free to ask if you have questions"
- Any similar polite closing statements

Context: {escaped_docs}

Response:"""

