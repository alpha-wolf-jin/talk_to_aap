# Playbook Configuration Guide

## Security Notice

**NEVER commit hard-coded tokens, passwords, or credentials to version control!**

## Recommended Approaches

### Option 1: Use Environment Variables (Recommended)

Playbooks should reference environment variables:

```yaml
---
- name: Example Playbook
  hosts: localhost
  gather_facts: false
  vars:
    controller_hostname: "{{ lookup('env', 'AAP_HOST') }}"
    controller_oauthtoken: "{{ lookup('env', 'AAP_TOKEN') }}"
    controller_validate_certs: false
```

Set the environment variable before running:
```bash
export AAP_TOKEN="your_token_here"
```

### Option 2: Use Ansible Vault

1. Create an encrypted vars file:
```bash
ansible-vault create playbooks/vars/vault.yml
```

2. Add sensitive data:
```yaml
controller_hostname: "192.168.122.20"
controller_oauthtoken: "YOUR_TOKEN_HERE"
controller_validate_certs: false
```

3. Reference in playbooks:
```yaml
---
- name: Example Playbook
  hosts: localhost
  gather_facts: false
  vars_files:
    - vars/vault.yml
  tasks:
    # Your tasks here
```

4. Run with vault password:
```bash
ansible-playbook playbook.yml --ask-vault-pass
```

### Option 3: Runtime Variable Passing

The MCP server passes credentials at runtime. Playbooks receive these via extra_vars:

```yaml
---
- name: Example Playbook
  hosts: localhost
  gather_facts: false
  vars:
    # These will be provided by MCP server at runtime
    controller_hostname: "{{ controller_hostname | default('localhost') }}"
    controller_oauthtoken: "{{ controller_oauthtoken | default('') }}"
    controller_validate_certs: false
```

## Current Implementation

The AAP AI Assistant currently passes credentials via the MCP server:
- Authentication happens at the web login
- Tokens are stored in session
- MCP server injects credentials into job template extra_vars
- Playbooks receive credentials at execution time

## Migration Steps

To remove hard-coded credentials from existing playbooks:

1. **Backup current playbooks**
2. **Replace hard-coded values with variables**:
   ```yaml
   # Before:
   controller_oauthtoken: "EIFnMuewWUVded037eBSNuX4lJlUBX"
   
   # After:
   controller_oauthtoken: "{{ controller_oauthtoken }}"
   ```
3. **Test with the MCP server** (which provides credentials at runtime)
4. **Update job templates in AAP** to accept extra_vars if needed

## Best Practices

1. ✅ Use variables for all sensitive data
2. ✅ Store secrets in Ansible Vault or environment variables
3. ✅ Add `.env` to `.gitignore`
4. ✅ Use the principle of least privilege for credentials
5. ✅ Rotate tokens regularly
6. ❌ Never commit tokens to version control
7. ❌ Never log sensitive data
8. ❌ Never pass secrets in URLs or command-line arguments

## Example: Secure Playbook Template

```yaml
---
- name: Secure AAP Operation
  hosts: localhost
  connection: local
  gather_facts: false
  
  vars:
    # Credentials provided by MCP server at runtime
    controller_hostname: "{{ controller_hostname }}"
    controller_oauthtoken: "{{ controller_oauthtoken }}"
    controller_validate_certs: "{{ controller_validate_certs | default(false) }}"
    
    # Operation-specific variables
    resource_name: "{{ resource_name }}"
    resource_description: "{{ resource_description | default('') }}"
  
  tasks:
    - name: Perform AAP operation
      ansible.controller.resource:
        controller_host: "{{ controller_hostname }}"
        controller_oauthtoken: "{{ controller_oauthtoken }}"
        validate_certs: "{{ controller_validate_certs }}"
        name: "{{ resource_name }}"
        description: "{{ resource_description }}"
        state: present
      no_log: true  # Don't log sensitive data
```

## Notes

- The current playbooks have hard-coded tokens for standalone testing
- In production with the MCP server, these are overridden by runtime variables
- Consider creating a `vars/vault.yml` for local testing
- The MCP server handles authentication and token injection

