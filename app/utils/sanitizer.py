import re


def sanitize_code(code: str) -> str:
    """脱敏处理：移除密钥、token、密码等敏感信息"""
    # 移除密码
    code = re.sub(
        r'password\s*=\s*["\'][^"\']+["\']',
        'password="***"',
        code,
        flags=re.IGNORECASE
    )
    # 移除 token/api_key
    code = re.sub(
        r'(api_key|token|secret|access_token)\s*=\s*["\'][^"\']+["\']',
        r'\1="***"',
        code,
        flags=re.IGNORECASE
    )
    # 移除 AWS/云服务密钥格式
    code = re.sub(
        r'AKIA[0-9A-Z]{16}',
        'AKIA***REDACTED***',
        code
    )
    # 移除可能的私钥
    code = re.sub(
        r'-----BEGIN.*PRIVATE KEY-----[\s\S]*?-----END.*PRIVATE KEY-----',
        '-----PRIVATE KEY REDACTED-----',
        code
    )
    return code