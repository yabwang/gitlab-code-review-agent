from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # GitLab 配置
    GITLAB_URL: str = "https://gitlab.yourcompany.com"
    GITLAB_TOKEN: str = ""  # Access Token
    GITLAB_WEBHOOK_SECRET: str = ""  # Webhook 验证 Token

    # GitHub 配置
    GITHUB_TOKEN: str = ""  # Personal Access Token
    GITHUB_WEBHOOK_SECRET: str = ""  # Webhook 验证 Secret

    # LLM 配置（支持国内模型）
    LLM_PROVIDER: str = "deepseek"  # deepseek / qwen / zhipu
    LLM_API_KEY: str = ""
    LLM_API_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-coder"

    # 服务配置
    SERVER_PORT: int = 8080
    MAX_DIFF_SIZE: int = 50000  # 最大 diff 字节数
    REVIEW_TIMEOUT: int = 120   # 审查超时秒数

    # Agent 配置
    AGENT_MODE: str = "single"  # single / multi - 单进程或多 Agent 模式
    COORDINATOR_PORT: int = 8080
    SECURITY_AGENT_PORT: int = 8081
    LLM_AGENT_PORT: int = 8082
    AGENT_TIMEOUT: int = 120  # Agent 间调用超时

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()