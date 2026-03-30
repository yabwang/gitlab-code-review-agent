"""
Agent 基类 - 定义 Agent 的基本接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from fastapi import FastAPI
import logging

from .protocol import AgentCapability, AgentRequest, AgentResponse, AgentInfo, AgentStatus
from .registry import get_registry

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Agent 基类"""

    # 子类需要定义的类属性
    agent_id: str
    name: str
    capabilities: List[AgentCapability]
    port: int = 8080

    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.config: Dict[str, Any] = {}

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化 Agent

        Args:
            config: 配置信息

        Returns:
            是否初始化成功
        """
        self.config = config
        self.app = FastAPI(
            title=f"{self.name} API",
            description=f"Agent: {self.name}",
            version="1.0.0"
        )

        # 注册路由
        self._setup_routes()

        # 注册到注册中心
        await self._register()

        logger.info(f"Agent {self.name} 初始化完成")
        return True

    async def shutdown(self) -> bool:
        """
        关闭 Agent

        Returns:
            是否关闭成功
        """
        # 从注册中心注销
        await self._unregister()
        logger.info(f"Agent {self.name} 已关闭")
        return True

    @abstractmethod
    async def handle_request(self, request: AgentRequest) -> AgentResponse:
        """
        处理请求（子类必须实现）

        Args:
            request: 请求内容

        Returns:
            响应内容
        """
        pass

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            健康状态信息
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": "healthy",
            "capabilities": [c.value for c in self.capabilities],
            "port": self.port
        }

    def _setup_routes(self):
        """设置 API 路由"""

        @self.app.get("/health")
        async def health():
            return await self.health_check()

        @self.app.get("/")
        async def root():
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "capabilities": [c.value for c in self.capabilities],
                "endpoints": {
                    "invoke": "/invoke",
                    "health": "/health"
                }
            }

        @self.app.post("/invoke")
        async def invoke(request: AgentRequest):
            logger.info(f"收到请求: {request.capability}, task_id: {request.task_id}")
            response = await self.handle_request(request)
            return response.model_dump()

    async def _register(self):
        """注册到注册中心"""
        registry = get_registry()
        agent_info = AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            capabilities=self.capabilities,
            status=AgentStatus.IDLE,
            endpoint=f"http://localhost:{self.port}"
        )
        await registry.register(agent_info)

    async def _unregister(self):
        """从注册中心注销"""
        registry = get_registry()
        await registry.unregister(self.agent_id)

    def get_app(self) -> FastAPI:
        """获取 FastAPI 应用实例"""
        if self.app is None:
            raise RuntimeError("Agent 未初始化，请先调用 initialize()")
        return self.app

    async def update_status(self, status: AgentStatus):
        """更新自身状态"""
        registry = get_registry()
        await registry.update_status(self.agent_id, status)

    async def heartbeat(self):
        """发送心跳"""
        registry = get_registry()
        await registry.heartbeat(self.agent_id)