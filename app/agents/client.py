"""
Agent 客户端 - 用于调用其他 Agent
"""
import httpx
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from .protocol import (
    AgentCapability, AgentRequest, AgentResponse,
    AgentInfo, AgentStatus
)
from .registry import AgentRegistry, get_registry

logger = logging.getLogger(__name__)


class AgentClient:
    """Agent 客户端"""

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        default_timeout: int = 120,
        max_retries: int = 2
    ):
        """
        初始化 Agent 客户端

        Args:
            registry: Agent 注册中心，默认使用全局实例
            default_timeout: 默认超时时间（秒）
            max_retries: 最大重试次数
        """
        self.registry = registry or get_registry()
        self.default_timeout = default_timeout
        self.max_retries = max_retries

    async def call(
        self,
        capability: AgentCapability,
        payload: Dict[str, Any],
        timeout: Optional[int] = None,
        prefer_agent: Optional[str] = None,
        sender_id: str = "client"
    ) -> AgentResponse:
        """
        调用指定能力的 Agent

        Args:
            capability: 所需能力
            payload: 调用参数
            timeout: 超时时间（秒）
            prefer_agent: 优先选择的 Agent ID
            sender_id: 发送者 ID

        Returns:
            Agent 响应
        """
        timeout = timeout or self.default_timeout

        # 1. 发现可用 Agent
        agents = await self.registry.discover(capability, AgentStatus.IDLE)

        if not agents:
            # 尝试不过滤状态
            agents = await self.registry.discover(capability, None)

        if not agents:
            logger.warning(f"没有可用的 Agent 提供能力: {capability}")
            return AgentResponse(
                sender_id="registry",
                task_id="",
                success=False,
                error=f"No available agent for capability: {capability}"
            )

        # 2. 选择 Agent
        agent = None
        if prefer_agent:
            for a in agents:
                if a.agent_id == prefer_agent:
                    agent = a
                    break

        if not agent:
            agent = agents[0]  # 简单轮询，可扩展为更复杂的负载均衡

        # 3. 构建请求
        request = AgentRequest(
            sender_id=sender_id,
            receiver_id=agent.agent_id,
            capability=capability if isinstance(capability, str) else capability.value,
            payload=payload,
            timeout=timeout
        )

        # 4. 更新 Agent 状态
        await self.registry.update_status(agent.agent_id, AgentStatus.BUSY)

        try:
            # 5. 发送请求（支持重试）
            response = await self._send_request_with_retry(agent, request)
            return response
        finally:
            # 6. 恢复 Agent 状态
            await self.registry.update_status(agent.agent_id, AgentStatus.IDLE)

    async def _send_request_with_retry(
        self,
        agent: AgentInfo,
        request: AgentRequest
    ) -> AgentResponse:
        """
        发送请求（支持重试）

        Args:
            agent: 目标 Agent
            request: 请求内容

        Returns:
            Agent 响应
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._send_request(agent.endpoint, request)
                return response
            except Exception as e:
                last_error = e
                logger.warning(f"调用 Agent {agent.name} 失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")

                if attempt < self.max_retries:
                    await asyncio.sleep(1)  # 重试前等待

        return AgentResponse(
            sender_id="client",
            task_id=request.task_id,
            success=False,
            error=f"Failed after {self.max_retries + 1} attempts: {str(last_error)}"
        )

    async def _send_request(
        self,
        endpoint: str,
        request: AgentRequest
    ) -> AgentResponse:
        """
        发送 HTTP 请求到 Agent

        Args:
            endpoint: Agent 端点地址
            request: 请求内容

        Returns:
            Agent 响应
        """
        url = f"{endpoint.rstrip('/')}/invoke"

        async with httpx.AsyncClient(timeout=request.timeout) as client:
            start_time = datetime.now()

            resp = await client.post(
                url,
                json=request.model_dump()
            )
            resp.raise_for_status()

            execution_time = (datetime.now() - start_time).total_seconds()

            data = resp.json()
            response = AgentResponse(**data)
            response.execution_time = execution_time

            return response

    async def call_multiple(
        self,
        calls: list  # List[(capability, payload)]
    ) -> list:  # List[AgentResponse]
        """
        并行调用多个 Agent

        Args:
            calls: 调用列表 [(capability, payload), ...]

        Returns:
            响应列表
        """
        tasks = [
            self.call(capability, payload)
            for capability, payload in calls
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for i, resp in enumerate(responses):
            if isinstance(resp, Exception):
                results.append(AgentResponse(
                    sender_id="client",
                    task_id="",
                    success=False,
                    error=str(resp)
                ))
            else:
                results.append(resp)

        return results

    async def health_check(self, agent_id: str) -> Dict[str, Any]:
        """
        检查指定 Agent 健康状态

        Args:
            agent_id: Agent ID

        Returns:
            健康检查结果
        """
        agent = await self.registry.get_agent(agent_id)
        if not agent:
            return {"status": "not_found", "agent_id": agent_id}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{agent.endpoint}/health")
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            return {
                "status": "error",
                "agent_id": agent_id,
                "error": str(e)
            }


# 全局客户端实例
_client: Optional[AgentClient] = None


def get_client() -> AgentClient:
    """获取全局 Agent 客户端实例"""
    global _client
    if _client is None:
        _client = AgentClient()
    return _client