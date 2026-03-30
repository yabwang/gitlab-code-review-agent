"""
LLM Agent - 统一的 LLM 调用服务
"""
import logging
from typing import Dict, Any

from .base import BaseAgent
from .protocol import AgentCapability, AgentRequest, AgentResponse, LLMChatPayload, CodeFixPayload

logger = logging.getLogger(__name__)


class LLMAgent(BaseAgent):
    """LLM 服务 Agent"""

    agent_id = "llm-001"
    name = "LLMAgent"
    capabilities = [
        AgentCapability.LLM_CHAT,
        AgentCapability.CODE_FIX,
        AgentCapability.SUMMARY_GENERATE
    ]
    port = 8082

    def __init__(self):
        super().__init__()
        self.llm_client = None

    async def initialize(self, config: Dict[str, Any]) -> bool:
        result = await super().initialize(config)

        # 初始化 LLM 客户端
        from app.llm_client import LLMClient
        self.llm_client = LLMClient()

        return result

    async def handle_request(self, request: AgentRequest) -> AgentResponse:
        """处理 LLM 请求"""
        try:
            capability = request.capability
            payload = request.payload

            if capability == AgentCapability.LLM_CHAT.value:
                result = await self._handle_chat(payload)
            elif capability == AgentCapability.CODE_FIX.value:
                result = await self._handle_code_fix(payload)
            elif capability == AgentCapability.SUMMARY_GENERATE.value:
                result = await self._handle_summary_generate(payload)
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
            logger.error(f"LLM 处理失败: {e}")
            return AgentResponse(
                sender_id=self.agent_id,
                task_id=request.task_id,
                success=False,
                error=str(e)
            )

    async def _handle_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理聊天请求"""
        chat_payload = LLMChatPayload(**payload) if isinstance(payload, dict) else payload

        result = await self.llm_client.chat(
            system_prompt=chat_payload.system_prompt,
            user_message=chat_payload.user_message
        )

        return {"content": result}

    async def _handle_code_fix(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理代码修复请求"""
        fix_payload = CodeFixPayload(**payload) if isinstance(payload, dict) else payload

        fixed_code = await self.llm_client.fix_code(
            file_path=fix_payload.file_path,
            issue_type=fix_payload.issue_type,
            issue_description=fix_payload.issue_description,
            original_code=fix_payload.original_code,
            start_line=fix_payload.start_line,
            end_line=fix_payload.end_line
        )

        return {
            "fixed_code": fixed_code,
            "success": fixed_code is not None
        }

    async def _handle_summary_generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理总结生成请求"""
        from app.utils.prompt_templates import SUMMARY_PROMPT

        title = payload.get("title", "")
        changes = payload.get("changes", [])
        reviews = payload.get("reviews", [])

        # 构建输入
        user_message = f"""
MR 标题: {title}
变更数量: {len(changes)}
审查结果数量: {len(reviews)}

审查详情:
{chr(10).join([str(r) for r in reviews[:5]])}
"""

        summary = await self.llm_client.chat(SUMMARY_PROMPT, user_message)

        return {"summary": summary}

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        base_health = await super().health_check()

        # 检查 LLM 配置
        from app.config import get_settings
        settings = get_settings()

        base_health["llm_config"] = {
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL,
            "configured": bool(settings.LLM_API_KEY)
        }

        return base_health