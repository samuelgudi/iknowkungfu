"""Sanitization rule data for sanitize.py."""

RULES = [
    {
        "id": "HOME-POSIX",
        "pattern": r"/(?:home|Users)/[A-Za-z0-9_.-]+/",
        "placeholder": "/$HOME/",
        "description": "Local user home path",
    },
    {
        "id": "HOME-WIN",
        "pattern": r"[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+\\",
        "placeholder": "%USERPROFILE%\\",
        "description": "Windows user profile path",
    },
    {
        "id": "GITHUB-PAT",
        "pattern": r"\bghp_[A-Za-z0-9]{36}\b",
        "placeholder": "<GITHUB_PAT>",
        "description": "GitHub Personal Access Token",
    },
    {
        "id": "OPENAI-KEY",
        "pattern": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b",
        "placeholder": "<OPENAI_API_KEY>",
        "description": "OpenAI API key",
    },
    {
        "id": "ANTHROPIC-KEY",
        "pattern": r"\bsk-ant-[A-Za-z0-9_-]{32,}\b",
        "placeholder": "<ANTHROPIC_API_KEY>",
        "description": "Anthropic API key",
    },
    {
        "id": "AWS-ACCESS-KEY",
        "pattern": r"\bAKIA[0-9A-Z]{16}\b",
        "placeholder": "<AWS_ACCESS_KEY_ID>",
        "description": "AWS access key id",
    },
    {
        "id": "LAN-IP-192",
        "pattern": r"\b192\.168\.\d{1,3}\.\d{1,3}\b",
        "placeholder": "<LAN_IP>",
        "description": "RFC 1918 192.168.0.0/16 address",
    },
    {
        "id": "LAN-IP-10",
        "pattern": r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "placeholder": "<LAN_IP>",
        "description": "RFC 1918 10.0.0.0/8 address",
    },
    {
        "id": "LAN-IP-172",
        "pattern": r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b",
        "placeholder": "<LAN_IP>",
        "description": "RFC 1918 172.16.0.0/12 address",
    },
    {
        "id": "PROMPT-INJECTION",
        "pattern": r"(?i)\b(?:ignore (?:all )?previous instructions|your new instructions are|disregard the above)\b",
        "placeholder": "[REDACTED-PROMPT-INJECTION]",
        "description": "Prompt-injection trigger phrase in SKILL.md body",
        "skill_md_only": True,
    },
]
