"""
Utilities for extracting, validating, and creating tool calls from JSON strings.
This module handles the conversion of JSON/string representations to LangChain AIMessage objects.
"""

import ast
import json
import re
import uuid
from typing import Optional, List, Dict, Any, Tuple
from langchain_core.messages import AIMessage


# ===== JSON Extraction and Validation =====

def extract_json_list_from_string(input_str: str) -> Optional[List[Dict[str, Any]]]:
    """
    Extract JSON list from string with various outer layer formats.
    
    Args:
        input_str: String containing JSON data
        
    Returns:
        Parsed list of dictionaries or None if parsing fails
        
    Raises:
        ValueError: If input is not a string
    """
    if not isinstance(input_str, str):
        raise ValueError("Input must be a string")
    
    # Clean the input string
    cleaned_str = clean_input_string(input_str)
    
    if not cleaned_str:
        return None
    
    # Try multiple parsing strategies
    parsing_strategies = [
        try_direct_json_parse,
        try_single_quotes_to_double,
        try_extract_with_regex,
        try_literal_eval_parse  # Renamed from try_eval_safe_parse
    ]
    
    for strategy in parsing_strategies:
        try:
            result = strategy(cleaned_str)
            if result is not None and isinstance(result, list):
                return result
        except Exception:
            continue
    
    return None

def clean_input_string(input_str: str) -> Optional[str]:
    """
    Remove common wrapper patterns and clean the string.
    
    Args:
        input_str: Raw input string
        
    Returns:
        Cleaned string or None if empty
    """
    if not input_str.strip():
        return None
    
    # Remove code block markers
    cleaned = re.sub(r'^```json\s*|\s*```$', '', input_str.strip(), flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r'^```\s*|\s*```$', '', cleaned.strip())
    
    # Remove "json" prefix on its own line
    cleaned = re.sub(r'^json\s*', '', cleaned.strip(), flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove extra whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def try_direct_json_parse(cleaned_str: str) -> List[Dict[str, Any]]:
    """
    Try parsing as standard JSON.
    
    Args:
        cleaned_str: Cleaned string to parse
        
    Returns:
        Parsed list of dictionaries
    """
    return json.loads(cleaned_str)


def try_single_quotes_to_double(cleaned_str: str) -> List[Dict[str, Any]]:
    """
    Convert single quotes to double quotes for JSON compatibility.
    
    Args:
        cleaned_str: Cleaned string to parse
        
    Returns:
        Parsed list of dictionaries
    """
    # Use regex to replace single quotes while preserving content
    # This handles the case where the string uses single quotes instead of double
    converted = re.sub(r"'([^']*)'", r'"\1"', cleaned_str)
    # Handle escaped single quotes within strings
    converted = converted.replace("\\'", "'")
    return json.loads(converted)


def try_extract_with_regex(cleaned_str: str) -> Optional[List[Dict[str, Any]]]:
    """
    Use regex to find and extract JSON-like list patterns.
    
    Args:
        cleaned_str: Cleaned string to parse
        
    Returns:
        Parsed list or None if no match found
    """
    # Pattern to match list structures
    list_pattern = r'\[\s*\{.*\}\s*\]'
    match = re.search(list_pattern, cleaned_str, re.DOTALL)
    
    if match:
        list_str = match.group(0)
        # Try with single quote conversion
        return try_single_quotes_to_double(list_str)
    
    return None

def try_literal_eval_parse(cleaned_str: str) -> Optional[List[Dict[str, Any]]]:
    """
    Safely parse Python literal syntax using ast.literal_eval.
    This is MUCH safer than eval() as it only evaluates literals.
    
    Args:
        cleaned_str: Cleaned string to parse
        
    Returns:
        Parsed list or None if parsing fails
    """
    try:
        # ast.literal_eval safely evaluates strings containing Python literals
        # It can only evaluate: strings, bytes, numbers, tuples, lists, dicts,
        # sets, booleans, and None
        result = ast.literal_eval(cleaned_str)
        if isinstance(result, list):
            return result
    except (ValueError, SyntaxError):
        pass
    return None

def verify_json_list(data_list: List[Dict[str, Any]]) -> bool:
    """
    Verify the extracted list is valid JSON format and meets specific structure requirements:
    - Each item must be a dict
    - Each dict must have exactly 2 keys: 'name' and 'args'
    - 'name' value must be a string
    - 'args' value must be a dict
    
    Args:
        data_list: List to verify
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data_list, list):
        return False
    
    # Basic JSON verification
    try:
        json_str = json.dumps(data_list)
        json.loads(json_str)
    except Exception:
        return False
    
    # Enhanced structure validation
    if len(data_list) == 0:
        return False
    
    all_items_valid = True
    for i, item in enumerate(data_list):
        item_valid = validate_list_item(item, i)
        if not item_valid:
            all_items_valid = False
    
    return all_items_valid


def validate_list_item(item: Any, index: int = 0) -> bool:
    """
    Validate a single item in the list.
    
    Args:
        item: Item to validate
        index: Index of the item (for debugging)
        
    Returns:
        True if valid, False otherwise
    """
    # Check if item is a dictionary
    if not isinstance(item, dict):
        return False
    
    # Check number of keys
    keys = list(item.keys())
    if len(keys) != 2:
        return False
    
    # Check for required keys
    if 'name' not in keys:
        return False
    
    if 'args' not in keys:
        return False
    
    # Check 'name' value type
    name_value = item['name']
    if not isinstance(name_value, str):
        return False
    
    # Check 'args' value type
    args_value = item['args']
    if not isinstance(args_value, dict):
        return False
    
    return True


def get_and_validate_json_list(input_str: str) -> Tuple[Optional[List[Dict[str, Any]]], bool]:
    """
    Extract JSON list from string and validate its structure.
    
    Args:
        input_str: Input string to parse
        
    Returns:
        Tuple of (list_data, is_valid)
    """
    extracted_list = extract_json_list_from_string(input_str)
    if extracted_list is None:
        return None, False
    
    is_valid = verify_json_list(extracted_list)
    return extracted_list, is_valid


def transform_data_structure(
    original_list: List[Dict[str, Any]], 
    tool_call_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Transform the original list data to new structure.
    
    Args:
        original_list: Original list of tool calls
        tool_call_id: Optional custom tool call ID
        
    Returns:
        Transformed list with added metadata
    """
    transformed_list = []

    for item in original_list:
        # Generate random ID if not provided
        if tool_call_id is None:
            random_id = f"chatcmpl-tool-{uuid.uuid4().hex}"
        else:
            random_id = tool_call_id

        # Create new structure
        transformed_item = {
            'name': item['name'],
            'args': item['args'],
            'id': random_id,
            'type': 'tool_call'
        }

        transformed_list.append(transformed_item)

    return transformed_list


# ===== AIMessage Creation =====

def create_ai_message_with_tool_calls(
    input_str: str, 
    tool_call_id: Optional[str] = None, 
    content: str = ""
) -> Tuple[AIMessage, bool]:
    """
    Create an AIMessage with tool calls from input string.
    
    Args:
        input_str: Input string containing tool call data
        tool_call_id: Optional custom tool call ID
        content: Optional text content for the AI message
    
    Returns:
        Tuple: (AIMessage, is_valid)
        If valid: Returns AIMessage with tool_calls and True
        If invalid: Returns AIMessage with original input as content and False
    """
    # Extract and transform the tool calls
    data, is_valid = get_and_validate_json_list(input_str)
    
    if is_valid:
        # Parse the transformed JSON to create tool_calls structure
        tool_calls_data = transform_data_structure(data)
        
        # Convert to LangChain tool_calls format
        tool_calls = []
        for tool_call in tool_calls_data:
            tool_calls.append({
                "name": tool_call["name"],
                "args": tool_call["args"],
                "id": tool_call["id"],
                "type": "tool_call"
            })
        
        # Create AIMessage with tool calls
        ai_message = AIMessage(
            content=content,
            tool_calls=tool_calls
        )
        
        return ai_message, True
        
    else:
        # Create basic AIMessage with original input as content
        ai_message = AIMessage(
            content=f"Invalid tool call input: {input_str}",
            tool_calls=[]
        )
        
        return ai_message, False


def create_ai_message_from_multiple_tool_calls(
    tool_calls_list: List[str], 
    content: str = ""
) -> AIMessage:
    """
    Create AIMessage from multiple validated tool calls.
    
    Args:
        tool_calls_list: List of input strings for tool calls
        content: Optional text content for the AI message
    
    Returns:
        AIMessage with all valid tool calls
    """
    all_tool_calls = []
    valid_count = 0
    
    for i, tool_call_input in enumerate(tool_calls_list):

        data, is_valid = get_and_validate_json_list(tool_call_input)
        
        if is_valid:
            tool_calls_data = transform_data_structure(data)
            all_tool_calls.extend(tool_calls_data)
            valid_count += 1
    
    # Convert to LangChain tool_calls format
    langchain_tool_calls = []
    for tool_call in all_tool_calls:
        langchain_tool_calls.append({
            "name": tool_call["name"],
            "args": tool_call["args"],
            "id": tool_call["id"],
            "type": "tool_call"
        })
    
    ai_message = AIMessage(
        content=content,
        tool_calls=langchain_tool_calls
    )
    
    return ai_message

