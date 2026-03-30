"""
Agent 协议层 - 定义 Agent 间通信的数据模型
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class AgentCapability(str, Enum):
    """Agent 能力枚举"""
    # 审查相关
    CODE_REVIEW = "code_review"
    SECURITY_SCAN = "security_scan"
    CODE_FIX = "code_fix"
    SUMMARY_GENERATE = "summary_generate"

    # 平台 API
    GITLAB_API = "gitlab_api"
    GITHUB_API = "github_api"

    # LLM 服务
    LLM_CHAT = "llm_chat"

    # 工具类
    DIFF_PARSE = "diff_parse"
    CODE_SANITIZE = "code_sanitize"

    # 编排
    TASK_ORCHESTRATION = "task_orchestration"


class AgentStatus(str, Enum):
    """Agent 状态"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class MessageType(str, Enum):
    """消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class TaskPriority(str, Enum):
    """任务优先级"""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class AgentInfo(BaseModel):
    """Agent 信息模型"""
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    capabilities: List[AgentCapability]
    status: AgentStatus = AgentStatus.IDLE
    endpoint: str  # Agent 服务地址，如 http://localhost:8080
    metadata: Dict[str, Any] = Field(default_factory=dict)
    registered_at: datetime = Field(default_factory=datetime.now)
    last_heartbeat: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class AgentRequest(BaseModel):
    """Agent 请求消息"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.REQUEST
    sender_id: str
    receiver_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # 用于请求-响应关联

    # 请求内容
    capability: str  # 请求的能力
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: TaskPriority = TaskPriority.NORMAL
    payload: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 120
    callback_url: Optional[str] = None  # 异步回调地址
    context: Dict[str, Any] = Field(default_factory=dict)  # 上下文信息

    class Config:
        use_enum_values = True


class AgentResponse(BaseModel):
    """Agent 响应消息"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.RESPONSE
    sender_id: str
    receiver_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

    # 响应内容
    task_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None  # 执行耗时（秒）

    class Config:
        use_enum_values = True


class AgentNotification(BaseModel):
    """Agent 通知消息"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.NOTIFICATION
    sender_id: str
    receiver_id: Optional[str] = None  # None 表示广播
    timestamp: datetime = Field(default_factory=datetime.now)

    # 通知内容
    event: str  # 事件类型
    data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


# ============ 具体任务定义 ============

class CodeReviewPayload(BaseModel):
    """代码审查任务参数"""
    file_path: str
    code: str
    review_type: str = "quality"  # quality / security / all


class SecurityScanPayload(BaseModel):
    """安全扫描任务参数"""
    file_path: str
    code: str
    scan_type: str = "all"  # sql_injection / xss / all


class CodeFixPayload(BaseModel):
    """代码修复任务参数"""
    file_path: str
    issue_type: str
    issue_description: str
    original_code: str
    start_line: int
    end_line: int


class LLMChatPayload(BaseModel):
    """LLM 对话任务参数"""
    system_prompt: str
    user_message: str
    temperature: float = 0.3
    max_tokens: int = 4000


class PlatformActionPayload(BaseModel):
    """平台 API 任务参数"""
    action: str  # get_mr_changes / post_comment / create_review 等
    platform: str  # gitlab / github
    # GitLab 参数
    project_id: Optional[int] = None
    mr_iid: Optional[int] = None
    # GitHub 参数
    owner: Optional[str] = None
    repo: Optional[str] = None
    pr_number: Optional[int] = None
    # 其他参数
    extra: Dict[str, Any] = Field(default_factory=dict)