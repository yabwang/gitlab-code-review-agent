import httpx
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

# 支持的国内 LLM 提供商配置
PROVIDERS = {
    "deepseek": {
        "url": "https://api.deepseek.com/v1",
        "model": "deepseek-coder"
    },
    "qwen": {
        "url": "https://dashscope.aliyuncs.com/api/v1",
        "model": "qwen-coder-plus"
    },
    "zhipu": {
        "url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4"
    },
    "doubao": {
        "url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-pro-32k"
    }
}


class LLMClient:
    """LLM API 客户端（支持国内多种模型）"""

    def __init__(self):
        self.settings = get_settings()
        provider_config = PROVIDERS.get(self.settings.LLM_PROVIDER, PROVIDERS["deepseek"])
        self.api_url = self.settings.LLM_API_URL or provider_config["url"]
        self.model = self.settings.LLM_MODEL or provider_config["model"]
        self.api_key = self.settings.LLM_API_KEY

    async def chat(self, system_prompt: str, user_message: str) -> str:
        """调用 LLM 进行对话"""
        if not self.api_key:
            raise ValueError("LLM API Key 未配置")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }

        timeout = self.settings.REVIEW_TIMEOUT or 120

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                resp.raise_for_status()
                result = resp.json()
                return result["choices"][0]["message"]["content"]
            except httpx.TimeoutException:
                logger.error(f"LLM API 调用超时 ({timeout}s)")
                return "审查超时，请稍后重试"
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM API 错误: {e}")
                return f"API 调用失败: {e.response.status_code}"
            except Exception as e:
                logger.error(f"LLM 调用异常: {e}")
                return f"调用异常: {str(e)}"

    async def batch_review(self, prompts: list) -> list:
        """批量审查多个代码块"""
        results = []
        for system_prompt, user_message in prompts:
            result = await self.chat(system_prompt, user_message)
            results.append(result)
        return results

    async def fix_code(
        self,
        file_path: str,
        issue_type: str,
        issue_description: str,
        original_code: str,
        start_line: int,
        end_line: int
    ) -> str:
        """调用 LLM 生成修复后的代码"""
        from app.utils.prompt_templates import CODE_FIX_PROMPT

        system_prompt = CODE_FIX_PROMPT.format(
            file_path=file_path,
            issue_type=issue_type,
            issue_description=issue_description,
            original_code=original_code,
            start_line=start_line,
            end_line=end_line
        )

        user_message = "请生成修复后的代码。"

        result = await self.chat(system_prompt, user_message)

        # 处理返回结果
        if "CANNOT_FIX" in result:
            logger.info(f"LLM 无法自动修复: {file_path}")
            return None

        # 提取代码块内容
        code = self._extract_code_block(result)
        if code:
            logger.info(f"LLM 生成修复代码成功: {file_path}")
            return code

        # 如果没有代码块，直接返回结果（可能是纯代码）
        if result and not result.startswith("CANNOT_FIX"):
            return result.strip()

        return None

    def _extract_code_block(self, text: str) -> str:
        """从 LLM 返回中提取代码块内容"""
        import re
        # 匹配 ```language 或 ``` 包裹的代码块
        pattern = r'```(?:\w*\n)?(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()
        return None