import os, requests, time, re
from typing import List, Dict, Any, Tuple
from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.server.http import create_sse_app

app = FastAPI()
mcp = FastMCP("AAP-01")

# Create SSE app
sse_app = create_sse_app(mcp, message_path="/", sse_path="/sse")

# Mount SSE app
app.mount("/", sse_app)

aap_host = os.getenv("AAP_HOST")

def aap_result(id: int, aap_token: str = None, auth_type: str = "token", aap_base_url: str = None) -> str:
    """Fetch job output/stdout from AAP using token authentication"""
    # Use provided base_url or construct from aap_host
    if aap_base_url:
        base = aap_base_url.rstrip('/')
        url = f"{base}/jobs/{id}/stdout/?format=json"
    else:
        url = f"https://{aap_host}/api/controller/v2/jobs/{id}/stdout/?format=json"

    print("AAP URL:", url)

    headers = {
        'Content-Type': 'application/json'
    }
    
    # Use token authentication
    if aap_token:
        if auth_type == "token":
            headers['Authorization'] = f"Bearer {aap_token}"
        elif auth_type == "basic":
            headers['Authorization'] = f"Basic {aap_token}"

    try:
        response = requests.get(
            url,
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('content', '')

    except requests.exceptions.RequestException as e:
        print(f"Error fetching job result: {e}")
        error_msg = f"Error fetching job {id} output\nDetails: {str(e)[:100]}"
        return error_msg

def aap_job_details(id: int, aap_token: str = None, auth_type: str = "token", aap_base_url: str = None) -> Dict[str, Any]:
    """Fetch detailed job information including status and error details using token authentication"""
    # Use provided base_url or construct from aap_host
    if aap_base_url:
        base = aap_base_url.rstrip('/')
        url = f"{base}/jobs/{id}/?format=json"
    else:
        url = f"https://{aap_host}/api/controller/v2/jobs/{id}/?format=json"
    
    print(f"Fetching job details: {url}")
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Use token authentication
    if aap_token:
        if auth_type == "token":
            headers['Authorization'] = f"Bearer {aap_token}"
        elif auth_type == "basic":
            headers['Authorization'] = f"Basic {aap_token}"
    
    try:
        response = requests.get(
            url,
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching job details: {e}")
        return {"error": f"Error fetching job {id} details\nDetails: {str(e)[:100]}"}

def aap_status(id: int, aap_token: str = None, auth_type: str = "token", aap_base_url: str = None) -> Tuple[str, Dict[str, Any]]:
    """
    Check job status and return both status and full job details using token authentication
    
    Returns:
        Tuple of (status_string, job_details_dict)
    """
    # Use provided base_url or construct from aap_host
    if aap_base_url:
        base = aap_base_url.rstrip('/')
        url = f"{base}/jobs/{id}/?format=json"
        system_job_url = f"{base}/system_jobs/{id}/?format=json"
    else:
        url = f"https://{aap_host}/api/controller/v2/jobs/{id}/?format=json"
        system_job_url = f"https://{aap_host}/api/controller/v2/system_jobs/{id}/?format=json"

    print("AAP URL:", url)
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Use token authentication
    if aap_token:
        if auth_type == "token":
            headers['Authorization'] = f"Bearer {aap_token}"
        elif auth_type == "basic":
            headers['Authorization'] = f"Basic {aap_token}"

    status = "unknown"
    job_details = {}

    # Try regular job endpoint first
    try:
        response = requests.get(
            url,
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        result = response.json()
        job_details = result

        if 'status' in result:
            status = result['status']
            return status, job_details

    except requests.exceptions.RequestException as e:
        print(f"Error checking job status: {e}")

    # Try system job endpoint if regular job failed
    try:
        response = requests.get(
            system_job_url,
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        result = response.json()
        job_details = result
        
        if 'status' in result:
            status = result['status']

    except requests.exceptions.RequestException as e:
        print(f"Error checking system job status: {e}")

    return status, job_details

def aap_call(id: int, payload: Dict[str, Any], aap_token: str = None, auth_type: str = "token", aap_base_url: str = None) -> int:
    """Launch a job template and return the job ID using token authentication"""
    # Use provided base_url or construct from aap_host
    if aap_base_url:
        base = aap_base_url.rstrip('/')
        url = f"{base}/job_templates/{id}/launch/"
    else:
        url = f"https://{aap_host}/api/controller/v2/job_templates/{id}/launch/"

    print("AAP URL:", url)
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Use token authentication
    if aap_token:
        if auth_type == "token":
            headers['Authorization'] = f"Bearer {aap_token}"
        elif auth_type == "basic":
            headers['Authorization'] = f"Basic {aap_token}"
        print(f"Using {auth_type} authentication")

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            verify=False
        )
        response.raise_for_status()
        result = response.json()
        return result['job']

    except requests.exceptions.HTTPError as e:
        print(f"Error launching job: {e}")
        
        status_code = e.response.status_code if e.response else "Unknown"
        error_str = str(e)
        
        # Split the error message intelligently
        if "for url:" in error_str:
            parts = error_str.split("for url:")
            error_msg = f"\nFailed to launch job template {id}:\n{parts[0].strip()}\nFor url:\n{parts[1].strip()}\n"
        else:
            error_msg = f"\nFailed to launch job template {id}:\n{error_str}\n"
        
        raise Exception(error_msg)
    except requests.exceptions.RequestException as e:
        print(f"Error launching job: {e}")
        raise Exception(f"\nFailed to launch job template {id}:\n{str(e)}\n")

def extract_and_clean_result(text: str) -> str:
    """Extract result content and remove ANSI escape codes"""
    if not text:
        return ""
    
    # Extract content between <result> tags
    match = re.search(r'<result>(.*?)</result>', text, re.DOTALL)

    if match:
        content = match.group(1)
    else:
        content = text

    # Remove ANSI escape codes (color codes)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    content = ansi_escape.sub('', content)

    # Clean up newlines and whitespace
    content = content.replace('\\\\n', '\n').replace('\\n', '\n')
    content = re.sub(r'\n\s*\n', '\n\n', content)

    return content

def wait_for_job_completion(job_id: int, max_retries: int = 60, aap_token: str = None, auth_type: str = "token", aap_base_url: str = None) -> Tuple[str, str]:
    """
    Wait for job completion and return result with proper error handling
    
    Args:
        job_id: The AAP job ID to monitor
        max_retries: Maximum number of retry attempts (default 60 seconds)
        aap_token: AAP authentication token
        auth_type: Authentication type ("token" or "basic")
        aap_base_url: AAP base URL
    
    Returns:
        Tuple of (status, result_content)
        - status: 'success', 'failed', 'timeout', or 'error'
        - result_content: Job output or error message
    """
    print(f"Monitoring job {job_id}...")
    
    retries = 0
    status = "running"
    job_details = {}
    
    # Wait for job completion
    while status in ["running", "pending", "waiting"] and retries < max_retries:
        status, job_details = aap_status(job_id, aap_token, auth_type, aap_base_url)
        time.sleep(1)
        retries += 1
    
    # Handle timeout
    if retries >= max_retries and status in ["running", "pending", "waiting"]:
        error_msg = f"Job {job_id} timed out after {max_retries} seconds (Status: {status})"
        print(error_msg)
        return "timeout", error_msg
    
    # Fetch job output
    result_content = aap_result(job_id, aap_token, auth_type, aap_base_url)
    cleaned_result = extract_and_clean_result(result_content)
    
    # Handle failed jobs
    if status == "failed":
        error_info = []
        error_info.append(f"Job {job_id} failed with status: {status}")
        
        # Include error details from job_details
        if job_details:
            if 'job_explanation' in job_details and job_details['job_explanation']:
                error_info.append(f"Explanation: {job_details['job_explanation']}")
            
            if 'result_traceback' in job_details and job_details['result_traceback']:
                error_info.append(f"Traceback: {job_details['result_traceback']}")
        
        # Include the actual job output which may contain error messages
        if cleaned_result:
            error_info.append(f"\nJob Output:\n{cleaned_result}")
        else:
            error_info.append("No job output available")
        
        error_message = "\n".join(error_info)
        print(f"Job failed: {error_message}")
        return "failed", error_message
    
    # Handle successful completion
    if status == "successful":
        print(f"Job {job_id} completed successfully")
        return "success", cleaned_result
    
    # Handle other statuses (canceled, error, etc.)
    warning_msg = f"Job {job_id} finished with status: {status}\n\nOutput:\n{cleaned_result}"
    print(warning_msg)
    return status, warning_msg


@mcp.tool()
def create_organization(
    org_name: str,
    org_description: str = "",
    org_galaxy_credentials: str = "",
    org_default_environment: str = "",
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    Create a new organization in Ansible Automation Platform

    Input Requirements
    1. org_name (REQUIRED)
    - Type: String 
    - Description: Name of the organization to create
    
    2. org_description (OPTIONAL)
    - Type: String
    - Description: Description of the organization
    
    3. org_galaxy_credentials (OPTIONAL)
    - Type: String
    - Description: Name of galaxy credential to associate with the organization
    
    4. org_default_environment (OPTIONAL)
    - Type: String
    - Description: Default execution environment for the organization

    Args:
        org_name: Name of the organization to create (required)
        org_description: Description of the organization (optional)
        org_galaxy_credentials: Galaxy credentials to associate (optional)
        org_default_environment: Default execution environment (optional)
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        Result of the organization creation operation
    """
    try:
        print(f"[create_organization] Using {auth_type} authentication for user: {username}")
        print(f"Creating organization: {org_name}")
        
        # Build extra_vars with required and optional parameters
        extra_vars = {"org_name": org_name}
        
        if org_description:
            extra_vars["org_description"] = org_description
        else:
            extra_vars["org_description"] = ""
            
        if org_galaxy_credentials:
            extra_vars["org_galaxy_credentials"] = org_galaxy_credentials
        else:
            extra_vars["org_galaxy_credentials"] = ""
            
        if org_default_environment:
            extra_vars["org_default_environment"] = org_default_environment
        else:
            extra_vars["org_default_environment"] = ""
        
        data = {"extra_vars": extra_vars}
        job_id = aap_call(35, data, aap_token, auth_type, aap_base_url)
        print(f"Launched create organization job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"Organization creation failed:\n{result}"
            
    except Exception as e:
        return f"Organization creation error: {str(e)}"

@mcp.tool()
def create_credential(
    credential_name: str,
    credential_organization: str,
    credential_type: str,
    credential_description: str = "",
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    Create a new credential in Ansible Automation Platform

    Input Requirements
    1. credential_name (REQUIRED)
    - Type: String 
    - Description: Name of the credential to create
    
    2. credential_organization (REQUIRED)
    - Type: String
    - Description: Organization to associate the credential with
    
    3. credential_type (REQUIRED)
    - Type: String
    - Description: Type of credential to create
    - Valid values:
      * Machine
      * Source Control
      * Network
      * Amazon Web Services
      * OpenStack
      * VMware vCenter
      * Red Hat Satellite 6
      * Red Hat Virtualization
      * Red Hat Ansible Automation Platform
      * GitHub Personal Access Token
      * GitLab Personal Access Token
      * Microsoft Azure Resource Manager
      * Google Compute Engine
      * Ansible Galaxy/Automation Hub API Token
      * Container Registry
      * HashiCorp Vault Secret Lookup
      * HashiCorp Vault Signed SSH
      * CyberArk Central Credential Provider Lookup
      * CyberArk Conjur Secret Lookup
      * Thycotic DevOps Secrets Vault
      * Thycotic Secret Server
      * Centrify Vault Credential Provider Lookup
      * Microsoft Azure Key Vault
      * OpenShift or Kubernetes API Bearer Token
      * GPG Public Key
      * Insights
      * Vault
    
    4. credential_description (OPTIONAL)
    - Type: String
    - Description: Description of the credential

    Args:
        credential_name: Name of the credential to create (required)
        credential_organization: Organization to associate with (required)
        credential_type: Type of credential (required)
        credential_description: Description of the credential (optional)
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        Result of the credential creation operation
    """
    try:
        print(f"[create_credential] Using {auth_type} authentication for user: {username}")
        print(f"Creating credential: {credential_name} (Type: {credential_type})")
        
        # Valid credential types
        valid_types = [
            "Machine", "Source Control", "Network", "Amazon Web Services",
            "OpenStack", "VMware vCenter", "Red Hat Satellite 6",
            "Red Hat Virtualization", "Red Hat Ansible Automation Platform",
            "GitHub Personal Access Token", "GitLab Personal Access Token",
            "Microsoft Azure Resource Manager", "Google Compute Engine",
            "Ansible Galaxy/Automation Hub API Token", "Container Registry",
            "HashiCorp Vault Secret Lookup", "HashiCorp Vault Signed SSH",
            "CyberArk Central Credential Provider Lookup",
            "CyberArk Conjur Secret Lookup", "Thycotic DevOps Secrets Vault",
            "Thycotic Secret Server", "Centrify Vault Credential Provider Lookup",
            "Microsoft Azure Key Vault", "OpenShift or Kubernetes API Bearer Token",
            "GPG Public Key", "Insights", "Vault"
        ]
        
        # Validate credential type
        if credential_type not in valid_types:
            return (f"Invalid credential_type: '{credential_type}'\n"
                   f"Valid types are: {', '.join(valid_types)}")
        
        # Build extra_vars with required and optional parameters
        extra_vars = {
            "credential_name": credential_name,
            "credential_organization": credential_organization,
            "credential_type": credential_type
        }
        
        if credential_description:
            extra_vars["credential_description"] = credential_description
        else:
            extra_vars["credential_description"] = ""
        
        data = {"extra_vars": extra_vars}
        job_id = aap_call(36, data, aap_token, auth_type, aap_base_url)
        print(f"Launched create credential job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"Credential creation failed:\n{result}"
            
    except Exception as e:
        return f"Credential creation error: {str(e)}"

@mcp.tool()
def list_organizations(
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    List all organizations in Ansible Automation Platform

    This tool retrieves all organizations configured in AAP, displaying their names and IDs.
    No input parameters are required.

    Args:
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        List of all organizations with their names and IDs
    """
    try:
        print(f"[list_organizations] Using {auth_type} authentication for user: {username}")
        print("Retrieving list of all organizations...")
        
        data = {}
        job_id = aap_call(37, data, aap_token, auth_type, aap_base_url)
        print(f"Launched list organizations job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"List organizations failed:\n{result}"
            
    except Exception as e:
        return f"List organizations error: {str(e)}"

@mcp.tool()
def list_users(
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    List all users in Ansible Automation Platform

    This tool retrieves all users configured in AAP, displaying their usernames, emails, 
    names, and role information (superuser/auditor status).
    No input parameters are required.

    Args:
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        List of all users with their usernames, emails, names, and role information
    """
    try:
        print(f"[list_users] Using {auth_type} authentication for user: {username}")
        print("Retrieving list of all users...")
        
        data = {}
        job_id = aap_call(38, data, aap_token, auth_type, aap_base_url)
        print(f"Launched list users job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"List users failed:\n{result}"
            
    except Exception as e:
        return f"List users error: {str(e)}"

@mcp.tool()
def create_user(
    user_username: str,
    user_password: str,
    user_email: str = "",
    user_first_name: str = "",
    user_last_name: str = "",
    user_organization: str = "",
    user_is_superuser: bool = False,
    user_is_system_auditor: bool = False,
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    Create a new user in Ansible Automation Platform

    Input Requirements
    1. user_username (REQUIRED)
    - Type: String 
    - Description: Username for the new user
    
    2. user_password (REQUIRED)
    - Type: String
    - Description: Password for the new user
    
    3. user_email (OPTIONAL)
    - Type: String
    - Description: Email address for the user
    
    4. user_first_name (OPTIONAL)
    - Type: String
    - Description: First name of the user
    
    5. user_last_name (OPTIONAL)
    - Type: String
    - Description: Last name of the user
    
    6. user_organization (OPTIONAL)
    - Type: String
    - Description: Organization to associate the user with
    
    7. user_is_superuser (OPTIONAL)
    - Type: Boolean
    - Description: Whether the user should be a superuser (default: false)
    
    8. user_is_system_auditor (OPTIONAL)
    - Type: Boolean
    - Description: Whether the user should be a system auditor (default: false)

    Args:
        user_username: Username for the new user (required)
        user_password: Password for the new user (required)
        user_email: Email address (optional)
        user_first_name: First name (optional)
        user_last_name: Last name (optional)
        user_organization: Organization to associate with (optional)
        user_is_superuser: Superuser status (optional, default: False)
        user_is_system_auditor: System auditor status (optional, default: False)
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        Result of the user creation operation
    """
    try:
        print(f"[create_user] Using {auth_type} authentication for user: {username}")
        print(f"Creating user: {user_username}")
        
        # Build extra_vars with required and optional parameters
        extra_vars = {
            "user_username": user_username,
            "user_password": user_password,
            "user_is_superuser": user_is_superuser,
            "user_is_system_auditor": user_is_system_auditor
        }
        
        # Add optional parameters (use empty string for text fields if not provided)
        if user_email:
            extra_vars["user_email"] = user_email
        else:
            extra_vars["user_email"] = ""
            
        if user_first_name:
            extra_vars["user_first_name"] = user_first_name
        else:
            extra_vars["user_first_name"] = ""
            
        if user_last_name:
            extra_vars["user_last_name"] = user_last_name
        else:
            extra_vars["user_last_name"] = ""
            
        if user_organization:
            extra_vars["user_organization"] = user_organization
        else:
            extra_vars["user_organization"] = ""
        
        data = {"extra_vars": extra_vars}
        job_id = aap_call(39, data, aap_token, auth_type, aap_base_url)
        print(f"Launched create user job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"User creation failed:\n{result}"
            
    except Exception as e:
        return f"User creation error: {str(e)}"

@mcp.tool()
def create_inventory(
    inventory_name: str,
    inventory_organization: str,
    inventory_description: str = "",
    inventory_variables: str = "",
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    Create a new inventory in Ansible Automation Platform

    Input Requirements
    1. inventory_name (REQUIRED)
    - Type: String 
    - Description: Name of the inventory to create
    
    2. inventory_organization (REQUIRED)
    - Type: String
    - Description: Organization to associate the inventory with
    
    3. inventory_description (OPTIONAL)
    - Type: String
    - Description: Description of the inventory
    
    4. inventory_variables (OPTIONAL)
    - Type: String
    - Description: YAML or JSON inventory variables

    Args:
        inventory_name: Name of the inventory to create (required)
        inventory_organization: Organization to associate with (required)
        inventory_description: Description of the inventory (optional)
        inventory_variables: YAML or JSON inventory variables (optional)
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        Result of the inventory creation operation
    """
    try:
        print(f"[create_inventory] Using {auth_type} authentication for user: {username}")
        print(f"Creating inventory: {inventory_name} in organization: {inventory_organization}")
        
        # Build extra_vars with required and optional parameters
        extra_vars = {
            "inventory_name": inventory_name,
            "inventory_organization": inventory_organization
        }
        
        if inventory_description:
            extra_vars["inventory_description"] = inventory_description
        else:
            extra_vars["inventory_description"] = ""
            
        if inventory_variables:
            extra_vars["inventory_variables"] = inventory_variables
        else:
            extra_vars["inventory_variables"] = ""
        
        data = {"extra_vars": extra_vars}
        job_id = aap_call(40, data, aap_token, auth_type, aap_base_url)
        print(f"Launched create inventory job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"Inventory creation failed:\n{result}"
            
    except Exception as e:
        return f"Inventory creation error: {str(e)}"

@mcp.tool()
def list_inventories(
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    List all inventories in Ansible Automation Platform

    This tool retrieves all inventories configured in AAP, displaying their names, 
    organizations, host/group counts, and descriptions.
    No input parameters are required.

    Args:
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        List of all inventories with their details (name, organization, hosts, groups, description)
    """
    try:
        print(f"[list_inventories] Using {auth_type} authentication for user: {username}")
        print("Retrieving list of all inventories...")
        
        data = {}
        job_id = aap_call(41, data, aap_token, auth_type, aap_base_url)
        print(f"Launched list inventories job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"List inventories failed:\n{result}"
            
    except Exception as e:
        return f"List inventories error: {str(e)}"

@mcp.tool()
def list_credentials(
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    List all credentials in Ansible Automation Platform

    This tool retrieves all credentials configured in AAP, displaying their names, 
    types, organizations, and descriptions.
    No input parameters are required.

    Args:
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        List of all credentials with their details (name, type, organization, description)
    """
    try:
        print(f"[list_credentials] Using {auth_type} authentication for user: {username}")
        print("Retrieving list of all credentials...")
        
        data = {}
        job_id = aap_call(42, data, aap_token, auth_type, aap_base_url)
        print(f"Launched list credentials job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"List credentials failed:\n{result}"
            
    except Exception as e:
        return f"List credentials error: {str(e)}"

@mcp.tool()
def create_project(
    project_name: str,
    project_organization: str,
    project_scm_type: str,
    project_description: str = "",
    project_scm_url: str = "",
    project_scm_branch: str = "",
    project_scm_credential: str = "",
    project_scm_update_on_launch: bool = True,
    project_scm_delete_on_update: bool = False,
    project_scm_clean: bool = False,
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    Create a new project in Ansible Automation Platform

    Input Requirements
    1. project_name (REQUIRED)
    - Type: String 
    - Description: Name of the project to create
    
    2. project_organization (REQUIRED)
    - Type: String
    - Description: Organization to associate the project with
    
    3. project_scm_type (REQUIRED)
    - Type: String
    - Description: Source control type
    - Valid values: git, manual
    
    4. project_description (OPTIONAL)
    - Type: String
    - Description: Description of the project
    
    5. project_scm_url (OPTIONAL)
    - Type: String
    - Description: SCM URL (required for git type)
    
    6. project_scm_branch (OPTIONAL)
    - Type: String
    - Description: Specific branch, tag, or commit
    
    7. project_scm_credential (OPTIONAL)
    - Type: String
    - Description: Credential name for private repos
    
    8. project_scm_update_on_launch (OPTIONAL)
    - Type: Boolean
    - Description: Update project before running job (default: true)
    
    9. project_scm_delete_on_update (OPTIONAL)
    - Type: Boolean
    - Description: Delete repo before update (default: false)
    
    10. project_scm_clean (OPTIONAL)
    - Type: Boolean
    - Description: Discard local changes before update (default: false)

    Args:
        project_name: Name of the project to create (required)
        project_organization: Organization to associate with (required)
        project_scm_type: Source control type - "git" or "manual" (required)
        project_description: Description of the project (optional)
        project_scm_url: SCM repository URL (optional)
        project_scm_branch: Branch, tag, or commit (optional)
        project_scm_credential: Credential for private repos (optional)
        project_scm_update_on_launch: Update on launch (optional, default: True)
        project_scm_delete_on_update: Delete on update (optional, default: False)
        project_scm_clean: Clean local changes (optional, default: False)
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        Result of the project creation operation
    """
    try:
        print(f"[create_project] Using {auth_type} authentication for user: {username}")
        print(f"Creating project: {project_name} (Type: {project_scm_type})")
        
        # Validate SCM type
        valid_scm_types = ["git", "manual"]
        if project_scm_type not in valid_scm_types:
            return (f"Invalid project_scm_type: '{project_scm_type}'\n"
                   f"Valid types are: {', '.join(valid_scm_types)}")
        
        # Build extra_vars with required and optional parameters
        extra_vars = {
            "project_name": project_name,
            "project_organization": project_organization,
            "project_scm_type": project_scm_type,
            "project_scm_update_on_launch": project_scm_update_on_launch,
            "project_scm_delete_on_update": project_scm_delete_on_update,
            "project_scm_clean": project_scm_clean
        }
        
        # Add optional string parameters
        if project_description:
            extra_vars["project_description"] = project_description
        else:
            extra_vars["project_description"] = ""
            
        if project_scm_url:
            extra_vars["project_scm_url"] = project_scm_url
        else:
            extra_vars["project_scm_url"] = ""
            
        if project_scm_branch:
            extra_vars["project_scm_branch"] = project_scm_branch
        else:
            extra_vars["project_scm_branch"] = ""
            
        if project_scm_credential:
            extra_vars["project_scm_credential"] = project_scm_credential
        else:
            extra_vars["project_scm_credential"] = ""
        
        data = {"extra_vars": extra_vars}
        job_id = aap_call(43, data, aap_token, auth_type, aap_base_url)
        print(f"Launched create project job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"Project creation failed:\n{result}"
            
    except Exception as e:
        return f"Project creation error: {str(e)}"

@mcp.tool()
def list_projects(
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    List all projects in Ansible Automation Platform

    This tool retrieves all projects configured in AAP, displaying their names, 
    SCM types, URLs, branches, organizations, and statuses.
    No input parameters are required.

    Args:
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        List of all projects with their details (name, SCM type, URL, branch, organization, status)
    """
    try:
        print(f"[list_projects] Using {auth_type} authentication for user: {username}")
        print("Retrieving list of all projects...")
        
        data = {}
        job_id = aap_call(46, data, aap_token, auth_type, aap_base_url)
        print(f"Launched list projects job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"List projects failed:\n{result}"
            
    except Exception as e:
        return f"List projects error: {str(e)}"

@mcp.tool()
def list_job_templates(
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    List all job templates in Ansible Automation Platform

    This tool retrieves all job templates configured in AAP, displaying their names, 
    types, inventories, projects, playbooks, and descriptions.
    No input parameters are required.

    Args:
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        List of all job templates with their details (name, type, inventory, project, playbook, description)
    """
    try:
        print(f"[list_job_templates] Using {auth_type} authentication for user: {username}")
        print("Retrieving list of all job templates...")
        
        data = {}
        job_id = aap_call(51, data, aap_token, auth_type, aap_base_url)
        print(f"Launched list job templates job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"List job templates failed:\n{result}"
            
    except Exception as e:
        return f"List job templates error: {str(e)}"

@mcp.tool()
def create_job_template(
    job_template_name: str,
    job_template_job_type: str,
    job_template_inventory: str,
    job_template_project: str,
    job_template_playbook: str,
    job_template_description: str = "",
    job_template_credentials: str = "",
    job_template_verbosity: int = 0,
    job_template_limit: str = "",
    job_template_extra_vars: str = "",
    job_template_tags: str = "",
    job_template_skip_tags: str = "",
    job_template_ask_variables_on_launch: bool = False,
    job_template_ask_limit_on_launch: bool = False,
    job_template_ask_tags_on_launch: bool = False,
    job_template_ask_skip_tags_on_launch: bool = False,
    job_template_ask_inventory_on_launch: bool = False,
    job_template_ask_credential_on_launch: bool = False,
    aap_token: str = None,
    auth_type: str = "token",
    aap_base_url: str = None,
    username: str = None
) -> str:
    """
    Create a new job template in Ansible Automation Platform

    Input Requirements
    1. job_template_name (REQUIRED)
    - Type: String 
    - Description: Name of the job template to create
    
    2. job_template_job_type (REQUIRED)
    - Type: String
    - Description: Type of job
    - Valid values: run, check
    
    3. job_template_inventory (REQUIRED)
    - Type: String
    - Description: Inventory name to use for the job
    
    4. job_template_project (REQUIRED)
    - Type: String
    - Description: Project name containing the playbook
    
    5. job_template_playbook (REQUIRED)
    - Type: String
    - Description: Path to playbook file in the project (e.g., hello_world.yml)
    
    6. job_template_description (OPTIONAL)
    - Type: String
    - Description: Description of the job template
    
    7. job_template_credentials (OPTIONAL)
    - Type: String
    - Description: Comma-separated list of credential names (e.g., "Cred1,Cred2")
    
    8. job_template_verbosity (OPTIONAL)
    - Type: Integer
    - Description: Verbosity level (0=Normal, 1=Verbose, 2=More Verbose, 3=Debug, 4=Connection Debug)
    - Default: 0
    
    9. job_template_limit (OPTIONAL)
    - Type: String
    - Description: Limit to specific hosts
    
    10. job_template_extra_vars (OPTIONAL)
    - Type: String
    - Description: Extra variables in YAML or JSON format
    
    11. job_template_tags (OPTIONAL)
    - Type: String
    - Description: Run specific tags
    
    12. job_template_skip_tags (OPTIONAL)
    - Type: String
    - Description: Skip specific tags
    
    13-18. job_template_ask_*_on_launch (OPTIONAL)
    - Type: Boolean
    - Description: Prompt for variables/limit/tags/inventory/credentials on launch
    - Default: False

    Args:
        job_template_name: Name of the job template (required)
        job_template_job_type: Job type - "run" or "check" (required)
        job_template_inventory: Inventory name (required)
        job_template_project: Project name (required)
        job_template_playbook: Playbook path (required)
        job_template_description: Description (optional)
        job_template_credentials: Comma-separated credential names (optional)
        job_template_verbosity: Verbosity level 0-4 (optional, default: 0)
        job_template_limit: Host limit (optional)
        job_template_extra_vars: Extra variables (optional)
        job_template_tags: Tags to run (optional)
        job_template_skip_tags: Tags to skip (optional)
        job_template_ask_variables_on_launch: Prompt for variables (optional, default: False)
        job_template_ask_limit_on_launch: Prompt for limit (optional, default: False)
        job_template_ask_tags_on_launch: Prompt for tags (optional, default: False)
        job_template_ask_skip_tags_on_launch: Prompt for skip tags (optional, default: False)
        job_template_ask_inventory_on_launch: Prompt for inventory (optional, default: False)
        job_template_ask_credential_on_launch: Prompt for credentials (optional, default: False)
        aap_token: AAP authentication token (automatically injected)
        auth_type: Authentication type - "token" or "basic" (automatically injected)
        aap_base_url: AAP base URL (automatically injected)
        username: AAP username for audit trail (automatically injected)

    Returns:
        Result of the job template creation operation
    """
    try:
        print(f"[create_job_template] Using {auth_type} authentication for user: {username}")
        print(f"Creating job template: {job_template_name} (Type: {job_template_job_type})")
        
        # Validate job type
        valid_job_types = ["run", "check"]
        if job_template_job_type not in valid_job_types:
            return (f"Invalid job_template_job_type: '{job_template_job_type}'\n"
                   f"Valid types are: {', '.join(valid_job_types)}")
        
        # Validate verbosity
        if not (0 <= job_template_verbosity <= 4):
            return f"Invalid job_template_verbosity: {job_template_verbosity}. Must be between 0 and 4."
        
        # Build extra_vars with required parameters
        extra_vars = {
            "job_template_name": job_template_name,
            "job_template_job_type": job_template_job_type,
            "job_template_inventory": job_template_inventory,
            "job_template_project": job_template_project,
            "job_template_playbook": job_template_playbook,
            "job_template_verbosity": job_template_verbosity,
            "job_template_ask_variables_on_launch": job_template_ask_variables_on_launch,
            "job_template_ask_limit_on_launch": job_template_ask_limit_on_launch,
            "job_template_ask_tags_on_launch": job_template_ask_tags_on_launch,
            "job_template_ask_skip_tags_on_launch": job_template_ask_skip_tags_on_launch,
            "job_template_ask_inventory_on_launch": job_template_ask_inventory_on_launch,
            "job_template_ask_credential_on_launch": job_template_ask_credential_on_launch
        }
        
        # Add optional string parameters
        if job_template_description:
            extra_vars["job_template_description"] = job_template_description
        else:
            extra_vars["job_template_description"] = ""
            
        if job_template_credentials:
            # Convert comma-separated string to list for Ansible
            creds_list = [c.strip() for c in job_template_credentials.split(',') if c.strip()]
            extra_vars["job_template_credentials"] = creds_list
        else:
            extra_vars["job_template_credentials"] = []
            
        if job_template_limit:
            extra_vars["job_template_limit"] = job_template_limit
        else:
            extra_vars["job_template_limit"] = ""
            
        if job_template_extra_vars:
            extra_vars["job_template_extra_vars"] = job_template_extra_vars
        else:
            extra_vars["job_template_extra_vars"] = ""
            
        if job_template_tags:
            extra_vars["job_template_tags"] = job_template_tags
        else:
            extra_vars["job_template_tags"] = ""
            
        if job_template_skip_tags:
            extra_vars["job_template_skip_tags"] = job_template_skip_tags
        else:
            extra_vars["job_template_skip_tags"] = ""
        
        data = {"extra_vars": extra_vars}
        job_id = aap_call(48, data, aap_token, auth_type, aap_base_url)
        print(f"Launched create job template job: {job_id}")
        
        status, result = wait_for_job_completion(job_id, 60, aap_token, auth_type, aap_base_url)
        
        if status == "success":
            return result
        else:
            return f"Job template creation failed:\n{result}"
            
    except Exception as e:
        return f"Job template creation error: {str(e)}"

@app.get("/test")
async def test():
    """
    Test endpoint to verify the server is running.

    Returns:
        dict: A simple hello world message.
    """
    return {"message": "Hello, world!"}
