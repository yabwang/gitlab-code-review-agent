import logging
from typing import Optional, List
from app.github_client import GitHubClient
from app.gitlab_client import GitLabClient
from app.llm_client import LLMClient
from app.utils.code_parser import parse_diff
from app.utils.sanitizer import sanitize_code
from app.config import get_settings

logger = logging.getLogger(__name__)


class CodeFixer:
    """代码自动修复核心逻辑"""

    def __init__(self):
        self.github = GitHubClient()
        self.gitlab = GitLabClient()
        self.llm = LLMClient()
        self.settings = get_settings()

    async def fix_github_pr(self, owner: str, repo: str, pr_number: int) -> dict:
        """执行 GitHub PR 代码修复"""
        logger.info(f"开始修复 GitHub PR #{pr_number} ({owner}/{repo})")

        # 1. 获取 PR 信息
        try:
            pr_info = await self.github.get_pr_info(owner, repo, pr_number)
            pr_files = await self.github.get_pr_files(owner, repo, pr_number)
        except Exception as e:
            logger.error(f"获取 PR 数据失败: {e}")
            return {"status": "error", "message": str(e)}

        head_sha = pr_info.get("head", {}).get("sha", "")
        head_ref = pr_info.get("head", {}).get("ref", "")

        if not pr_files:
            logger.info(f"PR #{pr_number} 无代码变更")
            return {"status": "skipped", "reason": "no_changes"}

        results = {
            "platform": "github",
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
            "status": "completed",
            "fixes": []
        }

        # 2. 处理每个文件变更
        suggestions = []
        position = 1

        for file_data in pr_files:
            file_path = file_data.get("filename")
            patch = file_data.get("patch", "")
            status = file_data.get("status", "modified")

            if not patch or status == "removed" or self._should_skip_file(file_path):
                continue

            # 脱敏处理
            safe_patch = sanitize_code(patch)

            # 解析变更块
            change_blocks = parse_diff(safe_patch)

            for block in change_blocks:
                content = block.get("content", "")
                if not content.strip():
                    continue

                # 分析代码问题
                issues = await self._analyze_issues(file_path, content)

                for issue in issues:
                    if issue.get("can_fix"):
                        # 获取修复代码
                        fixed_code = await self.llm.fix_code(
                            file_path=file_path,
                            issue_type=issue.get("type", "quality"),
                            issue_description=issue.get("description", ""),
                            original_code=content,
                            start_line=block.get("new_line", 1),
                            end_line=block.get("new_line", 1) + content.count('\n')
                        )

                        if fixed_code:
                            suggestions.append({
                                "path": file_path,
                                "position": position,
                                "issue_description": issue.get("description", "代码问题"),
                                "suggestion_code": fixed_code
                            })
                            results["fixes"].append({
                                "file": file_path,
                                "issue": issue.get("description"),
                                "fixed": True
                            })
                        else:
                            results["fixes"].append({
                                "file": file_path,
                                "issue": issue.get("description"),
                                "fixed": False,
                                "reason": "无法自动修复"
                            })

                position += 1

        # 3. 发布修复建议
        if suggestions and head_sha:
            try:
                await self.github.create_review_with_suggestions(
                    owner, repo, pr_number, head_sha, suggestions
                )
                logger.info(f"发布 {len(suggestions)} 个修复建议到 PR #{pr_number}")
            except Exception as e:
                logger.warning(f"发布修复建议失败: {e}")

        # 4. 发布总结
        summary = self._generate_fix_summary(results)
        await self.github.create_issue_comment(owner, repo, pr_number, summary)

        logger.info(f"GitHub PR #{pr_number} 修复完成，生成 {len(suggestions)} 个建议")
        return results

    async def fix_gitlab_mr(self, project_id: int, mr_iid: int) -> dict:
        """执行 GitLab MR 代码修复"""
        logger.info(f"开始修复 GitLab MR #{mr_iid} (项目 {project_id})")

        # 1. 获取 MR 信息
        try:
            mr_data = await self.gitlab.get_mr_changes(project_id, mr_iid)
        except Exception as e:
            logger.error(f"获取 MR 数据失败: {e}")
            return {"status": "error", "message": str(e)}

        diff_refs = mr_data.get("diff_refs", {})
        changes = mr_data.get("changes", [])

        if not changes:
            logger.info(f"MR #{mr_iid} 无代码变更")
            return {"status": "skipped", "reason": "no_changes"}

        results = {
            "platform": "gitlab",
            "project_id": project_id,
            "mr_iid": mr_iid,
            "status": "completed",
            "fixes": []
        }

        # 2. 处理每个文件变更
        for change in changes:
            file_path = change.get("new_path") or change.get("old_path")
            diff = change.get("diff", "")

            if not diff or self._should_skip_file(file_path):
                continue

            safe_diff = sanitize_code(diff)
            change_blocks = parse_diff(safe_diff)

            for block in change_blocks:
                content = block.get("content", "")
                if not content.strip():
                    continue

                issues = await self._analyze_issues(file_path, content)

                for issue in issues:
                    if issue.get("can_fix"):
                        fixed_code = await self.llm.fix_code(
                            file_path=file_path,
                            issue_type=issue.get("type", "quality"),
                            issue_description=issue.get("description", ""),
                            original_code=content,
                            start_line=block.get("new_line", 1),
                            end_line=block.get("new_line", 1) + content.count('\n')
                        )

                        if fixed_code and diff_refs:
                            try:
                                # GitLab 使用 discussions API 发布建议
                                await self.gitlab.post_line_comment(
                                    project_id, mr_iid,
                                    file_path,
                                    block.get("new_line", 1),
                                    f"**{issue.get('description')}**\n\n建议修改:\n```\n{fixed_code}\n```",
                                    diff_refs
                                )
                                results["fixes"].append({
                                    "file": file_path,
                                    "issue": issue.get("description"),
                                    "fixed": True
                                })
                            except Exception as e:
                                logger.warning(f"发布修复建议失败: {e}")

        # 3. 发布总结
        summary = self._generate_fix_summary(results)
        await self.gitlab.post_summary_comment(project_id, mr_iid, summary)

        logger.info(f"GitLab MR #{mr_iid} 修复完成")
        return results

    async def _analyze_issues(self, file_path: str, code: str) -> List[dict]:
        """分析代码问题，判断是否可自动修复"""
        from app.utils.prompt_templates import CODE_QUALITY_PROMPT, SECURITY_PROMPT
        from app.reviewer import CodeReviewer

        reviewer = CodeReviewer()

        # 复用审查逻辑
        quality_review = await self.llm.chat(
            CODE_QUALITY_PROMPT.format(file_path=file_path),
            f"审查代码:\n```\n{code}\n```"
        )

        issues = []

        # 检查是否有可修复的问题
        fixable_patterns = [
            ("命名问题", ["命名", "变量名", "函数名", "命名不规范"]),
            ("格式问题", ["缩进", "空格", "格式", "缺少空格", "多余空格"]),
            ("注释问题", ["缺少注释", "注释不清晰", "需要注释"]),
            ("简单逻辑", ["缺少判断", "边界检查", "空值检查", "缺少 return"]),
        ]

        for issue_type, keywords in fixable_patterns:
            if any(kw in quality_review for kw in keywords):
                issues.append({
                    "type": "quality",
                    "description": quality_review.split('\n')[0][:100],
                    "can_fix": True
                })

        if reviewer._is_no_issue(quality_review) and not issues:
            pass  # 无问题

        return issues

    def _generate_fix_summary(self, results: dict) -> str:
        """生成修复总结"""
        fixes = results.get("fixes", [])
        fixed_count = sum(1 for f in fixes if f.get("fixed"))
        unfixed_count = len(fixes) - fixed_count

        return f"""## 🤖 AI 代码修复建议

**修复模型**: {self.settings.LLM_PROVIDER} / {self.settings.LLM_MODEL}

---

**统计**:
- ✅ 可修复: {fixed_count} 个问题
- ❌ 无法自动修复: {unfixed_count} 个问题

---

> 💡 修复建议可在 PR 界面一键应用。请审查后确认是否采纳。
"""

    def _should_skip_file(self, file_path: str) -> bool:
        """判断是否跳过该文件"""
        skip_extensions = [
            ".md", ".txt", ".json", ".yaml", ".yml",
            ".lock", ".toml", ".ini", ".conf",
            ".svg", ".png", ".jpg", ".gif", ".ico",
            ".pdf", ".doc", ".xls"
        ]
        return any(file_path.endswith(ext) for ext in skip_extensions)