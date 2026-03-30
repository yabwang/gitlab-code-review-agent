"""
安全扫描 Agent - 专门负责安全漏洞检测
"""
import logging
import re
from typing import Dict, Any, List

from .base import BaseAgent
from .protocol import AgentCapability, AgentRequest, AgentResponse
from .client import get_client

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """安全扫描 Agent"""

    agent_id = "security-001"
    name = "SecurityAgent"
    capabilities = [AgentCapability.SECURITY_SCAN]
    port = 8081

    def __init__(self):
        super().__init__()
        self.client = None

    async def initialize(self, config: Dict[str, Any]) -> bool:
        result = await super().initialize(config)
        self.client = get_client()
        return result

    async def handle_request(self, request: AgentRequest) -> AgentResponse:
        """处理安全扫描请求"""
        try:
            payload = request.payload
            file_path = payload.get("file_path", "unknown")
            code = payload.get("code", "")
            scan_type = payload.get("scan_type", "all")

            issues = await self._scan_security(file_path, code, scan_type)

            return AgentResponse(
                sender_id=self.agent_id,
                task_id=request.task_id,
                success=True,
                result={"issues": issues, "total": len(issues)}
            )

        except Exception as e:
            logger.error(f"安全扫描失败: {e}")
            return AgentResponse(
                sender_id=self.agent_id,
                task_id=request.task_id,
                success=False,
                error=str(e)
            )

    async def _scan_security(
        self,
        file_path: str,
        code: str,
        scan_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        执行安全扫描

        Args:
            file_path: 文件路径
            code: 代码内容
            scan_type: 扫描类型

        Returns:
            发现的安全问题列表
        """
        issues = []

        # SQL 注入检测
        if scan_type in ["all", "sql_injection"]:
            sql_issues = self._detect_sql_injection(file_path, code)
            issues.extend(sql_issues)

        # XSS 检测
        if scan_type in ["all", "xss"]:
            xss_issues = self._detect_xss(file_path, code)
            issues.extend(xss_issues)

        # 命令注入检测
        if scan_type in ["all", "command_injection"]:
            cmd_issues = self._detect_command_injection(file_path, code)
            issues.extend(cmd_issues)

        # 敏感信息泄露检测
        if scan_type in ["all", "sensitive_data"]:
            sensitive_issues = self._detect_sensitive_data(file_path, code)
            issues.extend(sensitive_issues)

        # 如果配置了 LLM Agent，使用 LLM 进行更深入的分析
        if self._should_use_llm(code):
            llm_issues = await self._llm_security_scan(file_path, code)
            issues.extend(llm_issues)

        return issues

    def _detect_sql_injection(self, file_path: str, code: str) -> List[Dict]:
        """检测 SQL 注入风险"""
        issues = []
        patterns = [
            (r'execute\s*\(\s*["\'].*\{.*\}.*["\']', "可能的 SQL 注入：字符串格式化 SQL"),
            (r'f["\'].*SELECT.*\{', "可能的 SQL 注入：f-string 构建 SQL"),
            (r'\+\s*["\'].*SELECT', "可能的 SQL 注入：字符串拼接 SQL"),
        ]

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "type": "sql_injection",
                        "severity": "high",
                        "file": file_path,
                        "line": i,
                        "message": message,
                        "code_snippet": line.strip()[:100]
                    })

        return issues

    def _detect_xss(self, file_path: str, code: str) -> List[Dict]:
        """检测 XSS 风险"""
        issues = []
        patterns = [
            (r'innerHTML\s*=', "可能的 XSS：使用 innerHTML"),
            (r'document\.write\s*\(', "可能的 XSS：使用 document.write"),
            (r'dangerouslySetInnerHTML', "可能的 XSS：React dangerouslySetInnerHTML"),
            (r'\.html\s*\(', "可能的 XSS：jQuery .html() 方法"),
        ]

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "type": "xss",
                        "severity": "high",
                        "file": file_path,
                        "line": i,
                        "message": message,
                        "code_snippet": line.strip()[:100]
                    })

        return issues

    def _detect_command_injection(self, file_path: str, code: str) -> List[Dict]:
        """检测命令注入风险"""
        issues = []
        patterns = [
            (r'os\.system\s*\(', "可能的命令注入：os.system"),
            (r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True', "可能的命令注入：shell=True"),
            (r'eval\s*\(', "可能的代码注入：eval"),
            (r'exec\s*\(', "可能的代码注入：exec"),
        ]

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns:
                if re.search(pattern, line):
                    issues.append({
                        "type": "command_injection",
                        "severity": "critical",
                        "file": file_path,
                        "line": i,
                        "message": message,
                        "code_snippet": line.strip()[:100]
                    })

        return issues

    def _detect_sensitive_data(self, file_path: str, code: str) -> List[Dict]:
        """检测敏感信息泄露"""
        issues = []
        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "敏感信息泄露：硬编码密码"),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "敏感信息泄露：硬编码 API Key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "敏感信息泄露：硬编码 Secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "敏感信息泄露：硬编码 Token"),
        ]

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # 排除明显的变量定义或示例
                    if 'example' not in line.lower() and 'xxx' not in line.lower():
                        issues.append({
                            "type": "sensitive_data",
                            "severity": "medium",
                            "file": file_path,
                            "line": i,
                            "message": message,
                            "code_snippet": "[REDACTED]"
                        })

        return issues

    def _should_use_llm(self, code: str) -> bool:
        """判断是否应该使用 LLM 进行分析"""
        # 如果代码较长且包含敏感操作，使用 LLM
        sensitive_keywords = ['password', 'token', 'secret', 'auth', 'login', 'session']
        return len(code) > 500 and any(kw in code.lower() for kw in sensitive_keywords)

    async def _llm_security_scan(self, file_path: str, code: str) -> List[Dict]:
        """使用 LLM 进行深度安全分析"""
        try:
            response = await self.client.call(
                AgentCapability.LLM_CHAT,
                {
                    "system_prompt": "你是安全专家，分析代码中的安全漏洞。以 JSON 数组格式返回发现的问题：[{\"type\": \"漏洞类型\", \"severity\": \"严重程度\", \"line\": 行号, \"message\": \"描述\"}]",
                    "user_message": f"分析以下代码的安全漏洞:\n文件: {file_path}\n```\n{code}\n```",
                    "temperature": 0.1
                }
            )

            if response.success and response.result:
                # 尝试解析 LLM 返回的 JSON
                import json
                result_text = response.result.get("content", "") if isinstance(response.result, dict) else str(response.result)

                # 提取 JSON 数组
                import re
                json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
                if json_match:
                    issues = json.loads(json_match.group())
                    for issue in issues:
                        issue["source"] = "llm_analysis"
                    return issues

        except Exception as e:
            logger.warning(f"LLM 安全分析失败: {e}")

        return []