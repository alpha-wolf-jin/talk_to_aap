"""
Centralized configuration management for AAP AI Assistant.
All environment variables and constants should be defined here.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # Application Settings
    APP_NAME: str = "Ansible Automation AI Assistant"
    DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"
    
    # AAP Connection Settings
    AAP_HOST: str = os.environ.get("AAP_HOST", "192.168.122.20")
    AAP_BASE_URL: str = os.environ.get(
        "AAP_BASE_URL", 
        f"https://{AAP_HOST}/api/controller/v2/"
    )
    AAP_VERIFY_SSL: bool = os.environ.get("AAP_VERIFY_SSL", "False").lower() == "true"
    
    # MCP Server Settings
    MCP_HOST: str = os.environ.get("MCP_HOST", "localhost")
    MCP_PORT: str = os.environ.get("MCP_PORT", "8000")
    
    # LLM API Settings
    LLAMA_API_KEY: Optional[str] = os.environ.get("LLMA_KEY")
    LLAMA_MODEL: str = "llama-4-scout-17b-16e-w4a16"
    LLAMA_BASE_URL: str = os.environ.get(
        "LLAMA_BASE_URL",
        "https://llama-4-scout-17b-16e-w4a16-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443/v1"
    )
    
    QWEN_API_KEY: Optional[str] = os.environ.get("QWEN_KEY")
    QWEN_MODEL: str = "r1-qwen-14b-w4a16"
    QWEN_BASE_URL: str = os.environ.get(
        "QWEN_BASE_URL",
        "https://deepseek-r1-qwen-14b-w4a16-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443/v1"
    )
    
    # Agent Settings
    MAX_ITERATIONS: int = int(os.environ.get("MAX_ITERATIONS", "8"))
    RECURSION_LIMIT: int = int(os.environ.get("RECURSION_LIMIT", "300"))
    CONFIRMATION_MESSAGE_ID: str = "confirm_123"
    SEPARATOR_LENGTH: int = 39
    
    # Session Settings
    SESSION_EXPIRY_HOURS: int = int(os.environ.get("SESSION_EXPIRY_HOURS", "24"))
    
    # Job Template IDs (AAP-specific)
    # These should ideally be looked up dynamically, but are hardcoded for now
    JOB_TEMPLATE_IDS = {
        "create_organization": 35,
        "create_credential": 36,
        "list_organizations": 37,
        "list_users": 38,
        "create_user": 39,
        "create_inventory": 40,
        "list_inventories": 41,
        "list_credentials": 42,
        "create_project": 43,
        "list_projects": 46,
        "create_job_template": 48,
        "list_job_templates": 51,
    }
    
    # Logging Settings
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration"""
        errors = []
        
        if not cls.LLAMA_API_KEY:
            errors.append("LLMA_KEY environment variable is required")
        
        if not cls.QWEN_API_KEY:
            errors.append("QWEN_KEY environment variable is required")
        
        if errors:
            raise ValueError(
                f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )
    
    @classmethod
    def get_job_template_id(cls, template_name: str) -> int:
        """Get job template ID by name"""
        if template_name not in cls.JOB_TEMPLATE_IDS:
            raise ValueError(f"Unknown job template: {template_name}")
        return cls.JOB_TEMPLATE_IDS[template_name]


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"Warning: {e}")
    print("Some features may not work correctly.")

