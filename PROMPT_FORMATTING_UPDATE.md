# Prompt Formatting Update

## Overview
Updated the `tools_assistant_prompt` to improve how the AI agent formats parameter information when explaining tools to users.

## Problem
The AI was formatting parameters in a paragraph style that was hard to read:

**Before** ❌:
```
To create an organization in Ansible Automation Platform, you can use the `create_organization` tool.

Here are the steps:

1. **Required Parameter**: You need to provide the `org_name` (name of the organization to create).
2. **Optional Parameters**: You can also provide `org_description` (description of the organization), `org_galaxy_credentials` (galaxy credentials to associate), and `org_default_environment` (default execution environment).
```

## Solution
Added explicit parameter formatting guidelines to produce clear, numbered lists:

**After** ✅:
```
To create an organization in Ansible Automation Platform, you can use the `create_organization` tool.

**Required Parameters:**
1. org_name: Name of the organization to create

**Optional Parameters:**
1. org_description: Description of the organization
2. org_galaxy_credentials: Galaxy credentials to associate
3. org_default_environment: Default execution environment
```

## Changes Made

### File: `aap/utilities/prompts_aap.py`

#### 1. Added "Parameter Formatting in Explanations" Section

Added after the existing "Parameter Handling" section:

```markdown
**Parameter Formatting in Explanations:**
When explaining tool parameters to users, use this clear, numbered format:

**Required Parameters:**
1. parameter_name: Description of the parameter

**Optional Parameters:**
1. parameter_name: Description of the parameter
2. another_parameter: Description of another parameter

Example:
[Full example provided in prompt]
```

#### 2. Updated "Response Structure" Section

Changed from generic "list required parameters" to specific formatting instructions:

**Before**:
```markdown
For Tool Selection:
1. Acknowledge the user's problem
2. Explain which tool(s) will help
3. List required parameters
4. Ask for any missing information
```

**After**:
```markdown
For Tool Selection and Parameter Explanation:
1. Acknowledge the user's request
2. Explain which tool(s) will help
3. Format parameters clearly using the numbered format:
   - **Required Parameters:** (numbered list)
   - **Optional Parameters:** (numbered list)
4. Ask for any missing information

Example:
[Full example provided]
```

## Benefits

### 1. **Improved Readability** 📖
- Clear separation between required and optional parameters
- Each parameter on its own line
- Consistent formatting across all tool explanations

### 2. **Better User Experience** ✨
- Users can quickly scan the parameter list
- Easy to identify what's required vs optional
- No ambiguity in parameter descriptions

### 3. **Professional Formatting** 💼
- Follows standard documentation practices
- Numbered lists for easy reference
- Bold headers for clear sections

### 4. **Consistency** 🎯
- All tool explanations will follow the same format
- Predictable structure for users
- Easier to parse visually

## Example Usage

### Tool Explanation Example

**User asks**: "How do I create an organization?"

**AI will now respond**:
```
To create an organization in Ansible Automation Platform, you can use the `create_organization` tool.

**Required Parameters:**
1. org_name: Name of the organization to create

**Optional Parameters:**
1. org_description: Description of the organization
2. org_galaxy_credentials: Galaxy credentials to associate
3. org_default_environment: Default execution environment

Please provide the organization name you'd like to create.
```

### Multiple Tools Example

**User asks**: "How do I create a user?"

**AI will respond**:
```
To create a user in Ansible Automation Platform, you can use the `create_user` tool.

**Required Parameters:**
1. user_username: Username for the new user
2. user_email: Email address for the new user

**Optional Parameters:**
1. user_password: Password for the user
2. user_first_name: First name of the user
3. user_last_name: Last name of the user
4. user_is_superuser: Whether the user should be a superuser (true/false)
5. user_is_system_auditor: Whether the user should be a system auditor (true/false)

Please provide the username and email address.
```

## Implementation Details

### Location
- **File**: `/data/AI/talk-aap/aap/utilities/prompts_aap.py`
- **Variable**: `tools_assistant_prompt`
- **Lines**: Added after line 87 and updated around line 204

### How It Works

1. **Prompt Instruction**: The updated prompt now contains explicit formatting examples
2. **AI Behavior**: When the `generate_implementation_plan` node uses this prompt, the LLM will follow the formatting guidelines
3. **Consistency**: The example is repeated twice in the prompt to reinforce the pattern
4. **Clear Directives**: Uses bold headers and numbered lists as the standard

## Testing

To test the new formatting:

1. Start the application
2. Ask: "How do I create an organization?"
3. Verify the response follows the new format
4. Try with other tools (create_user, create_project, etc.)
5. Confirm all tool explanations use the same format

## Impact

- **Breaking Changes**: None (only changes output formatting, not functionality)
- **Backward Compatibility**: Fully compatible
- **User-Facing**: Yes, improves user experience
- **API Changes**: None

## Related Files

- `aap/aap-MaaS.py`: Uses this prompt in `generate_implementation_plan()` method
- `aap/utilities/decision_prompts.py`: Different prompt file (not affected)

## Future Enhancements

Potential improvements:
- Add examples for tools with no required parameters
- Add examples for tools with complex nested parameters
- Consider adding parameter type information (string, int, bool, etc.)
- Add parameter validation examples

---

**Updated**: December 2025  
**Author**: AI Assistant  
**Version**: 1.0.1
