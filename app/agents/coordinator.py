"""
协调器 Agent - 负责任务编排和 Webhook 接收
"""
import logging
from typing import Dict, Any, List
import uuid

from .base import BaseAgent
from .protocol import AgentCapability, AgentRequest, AgentResponse
from .client import get_client

logger = logging.getLogger(__name__)


class CoordinatorAgent(BaseAgent):
    """协调器 Agent - 编排代码审查流程"""

    agent_id = "coordinator-001"
    name = "CoordinatorAgent"
    capabilities = [
        AgentCapability.CODE_REVIEW,
        AgentCapability.TASK_ORCHESTRATION
    ]
    port = 8080

    def __init__(self):
        super().__init__()
        self.client = None

    async def initialize(self, config: Dict[str, Any]) -> bool:
        result = await super().initialize(config)
        self.client = get_client()
        return result

    async def handle_request(self, request: AgentRequest) -> AgentResponse:
        """处理请求"""
        try:
            capability = request.capability
            payload = request.payload

            if capability == AgentCapability.CODE_REVIEW.value:
                result = await self._orchestrate_review(payload)
            elif capability == AgentCapability.TASK_ORCHESTRATION.value:
                result = await self._orchestrate_task(payload)
            else:
                return AgentResponse(
                    sender_id=self.agent_id,
                    task_id=request.task_id,
                    success=False,
                    error=f"Unsupported capability: {capability}"
                )

            return AgentResponse(
                sender_id=self.agent_id,
                task_id=request.task_id,
                success=True,
                result=result
            )

        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return AgentResponse(
                sender_id=self.agent_id,
                task_id=request.task_id,
                success=False,
                error=str(e)
            )

    async def _orchestrate_review(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        编排代码审查流程

        流程:
        1. 调用 LLM Agent 进行代码质量审查
        2. 调用 Security Agent 进行安全扫描
        3. 汇总结果
        """
        results = {
            "status": "completed",
            "reviews": [],
            "security_issues": [],
            "summary": None
        }

        code = payload.get("code", "")
        file_path = payload.get("file_path", "unknown")

        # 1. 代码质量审查
        quality_response = await self.client.call(
            AgentCapability.LLM_CHAT,
            {
                "system_prompt": f"你是代码审查专家，审查 {file_path} 文件",
                "user_message": f"审查以下代码的质量:\n```\n{code}\n```"
            }
        )

        if quality_response.success:
            results["reviews"].append({
                "type": "quality",
                "file": file_path,
                "result": quality_response.result
            })

        # 2. 安全扫描
        security_response = await self.client.call(
            AgentCapability.SECURITY_SCAN,
            {
                "file_path": file_path,
                "code": code
            }
        )

        if security_response.success:
            results["security_issues"] = security_response.result.get("issues", [])

        # 3. 生成总结
        summary_response = await self.client.call(
            AgentCapability.LLM_CHAT,
            {
                "system_prompt": "你是代码审查总结助手，根据审查结果生成简洁的总结报告",
                "user_message": f"根据以下审查结果生成总结:\n质量审查: {results['reviews']}\n安全问题: {results['security_issues']}"
            }
        )

        if summary_response.success:
            results["summary"] = summary_response.result

        return results

    async def _orchestrate_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        编排通用任务

        支持指定多个能力调用
        """
        tasks = payload.get("tasks", [])
        results = []

        for task in tasks:
            capability = task.get("capability")
            task_payload = task.get("payload", {})

            response = await self.client.call(capability, task_payload)
            results.append({
                "capability": capability,
                "success": response.success,
                "result": response.result if response.success else None,
                "error": response.error if not response.success else None
            })

        return {"tasks": results}

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        base_health = await super().health_check()

        # 检查依赖的 Agent 状态
        client = get_client()
        llm_agents = await client.registry.discover(AgentCapability.LLM_CHAT)
        security_agents = await client.registry.discover(AgentCapability.SECURITY_SCAN)

        base_health["dependencies"] = {
            "llm_agents": len(llm_agents),
            "security_agents": len(security_agents)
        }

        return base_health