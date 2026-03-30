"""
Agent 注册中心 - 管理 Agent 的注册、发现和状态
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .protocol import AgentInfo, AgentCapability, AgentStatus

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent 注册中心"""

    def __init__(self, heartbeat_timeout: int = 60):
        """
        初始化注册中心

        Args:
            heartbeat_timeout: 心跳超时时间（秒），超过此时间未收到心跳则标记为离线
        """
        self._agents: Dict[str, AgentInfo] = {}
        self._capability_index: Dict[str, List[str]] = {
            cap.value: [] for cap in AgentCapability
        }
        self._heartbeat_timeout = heartbeat_timeout

    async def register(self, agent_info: AgentInfo) -> bool:
        """
        注册 Agent

        Args:
            agent_info: Agent 信息

        Returns:
            是否注册成功
        """
        agent_id = agent_info.agent_id

        # 如果已存在，先注销旧的
        if agent_id in self._agents:
            await self.unregister(agent_id)

        # 注册新 Agent
        self._agents[agent_id] = agent_info

        # 更新能力索引
        for cap in agent_info.capabilities:
            cap_value = cap if isinstance(cap, str) else cap.value
            if cap_value not in self._capability_index:
                self._capability_index[cap_value] = []
            if agent_id not in self._capability_index[cap_value]:
                self._capability_index[cap_value].append(agent_id)

        logger.info(f"Agent 注册成功: {agent_info.name} ({agent_id}), 能力: {agent_info.capabilities}")
        return True

    async def unregister(self, agent_id: str) -> bool:
        """
        注销 Agent

        Args:
            agent_id: Agent ID

        Returns:
            是否注销成功
        """
        if agent_id not in self._agents:
            return False

        agent = self._agents[agent_id]

        # 从能力索引中移除
        for cap in agent.capabilities:
            cap_value = cap if isinstance(cap, str) else cap.value
            if cap_value in self._capability_index:
                if agent_id in self._capability_index[cap_value]:
                    self._capability_index[cap_value].remove(agent_id)

        # 从注册表中移除
        del self._agents[agent_id]

        logger.info(f"Agent 注销成功: {agent.name} ({agent_id})")
        return True

    async def discover(
        self,
        capability: AgentCapability,
        status: Optional[AgentStatus] = AgentStatus.IDLE
    ) -> List[AgentInfo]:
        """
        发现具有特定能力的 Agent

        Args:
            capability: 所需能力
            status: 可选的状态过滤

        Returns:
            符合条件的 Agent 列表
        """
        cap_value = capability if isinstance(capability, str) else capability.value
        agent_ids = self._capability_index.get(cap_value, [])

        agents = []
        for aid in agent_ids:
            if aid in self._agents:
                agent = self._agents[aid]
                if status is None or agent.status == status.value:
                    agents.append(agent)

        return agents

    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """
        获取指定 Agent 信息

        Args:
            agent_id: Agent ID

        Returns:
            Agent 信息，不存在则返回 None
        """
        return self._agents.get(agent_id)

    async def heartbeat(self, agent_id: str) -> bool:
        """
        更新 Agent 心跳

        Args:
            agent_id: Agent ID

        Returns:
            是否更新成功
        """
        if agent_id not in self._agents:
            return False

        self._agents[agent_id].last_heartbeat = datetime.now()
        return True

    async def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        更新 Agent 状态

        Args:
            agent_id: Agent ID
            status: 新状态

        Returns:
            是否更新成功
        """
        if agent_id not in self._agents:
            return False

        self._agents[agent_id].status = status
        logger.debug(f"Agent {agent_id} 状态更新为: {status}")
        return True

    async def check_health(self) -> Dict[str, Any]:
        """
        检查所有 Agent 健康状态

        Returns:
            健康检查结果
        """
        now = datetime.now()
        timeout = timedelta(seconds=self._heartbeat_timeout)

        healthy = []
        unhealthy = []

        for agent_id, agent in self._agents.items():
            if now - agent.last_heartbeat > timeout:
                agent.status = AgentStatus.OFFLINE
                unhealthy.append({
                    "agent_id": agent_id,
                    "name": agent.name,
                    "last_heartbeat": agent.last_heartbeat.isoformat()
                })
            else:
                healthy.append({
                    "agent_id": agent_id,
                    "name": agent.name,
                    "status": agent.status
                })

        return {
            "total": len(self._agents),
            "healthy": len(healthy),
            "unhealthy": len(unhealthy),
            "agents": {
                "healthy": healthy,
                "unhealthy": unhealthy
            }
        }

    async def list_all(self) -> List[AgentInfo]:
        """
        列出所有已注册的 Agent

        Returns:
            Agent 列表
        """
        return list(self._agents.values())

    def get_stats(self) -> Dict[str, Any]:
        """
        获取注册中心统计信息

        Returns:
            统计信息
        """
        status_count = {}
        for agent in self._agents.values():
            status = agent.status if isinstance(agent.status, str) else agent.status.value
            status_count[status] = status_count.get(status, 0) + 1

        capability_count = {}
        for cap, agents in self._capability_index.items():
            capability_count[cap] = len(agents)

        return {
            "total_agents": len(self._agents),
            "status_distribution": status_count,
            "capability_distribution": capability_count
        }


# 全局注册中心实例
_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """获取全局注册中心实例"""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry