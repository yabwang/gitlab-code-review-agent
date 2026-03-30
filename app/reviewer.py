from typing import Optional, List
import logging
from app.gitlab_client import GitLabClient
from app.github_client import GitHubClient
from app.llm_client import LLMClient
from app.utils.code_parser import parse_diff
from app.utils.sanitizer import sanitize_code
from app.utils.prompt_templates import CODE_QUALITY_PROMPT, SECURITY_PROMPT, SUMMARY_PROMPT
from app.config import get_settings

logger = logging.getLogger(__name__)


class CodeReviewer:
    """代码审查核心逻辑"""

    def __init__(self):
        self.gitlab = GitLabClient()
        self.github = GitHubClient()
        self.llm = LLMClient()
        self.settings = get_settings()

    # ==================== GitLab 审查 ====================

    async def review_gitlab_mr(self, project_id: int, mr_iid: int) -> dict:
        """执行 GitLab MR 代码审查"""
        logger.info(f"开始审查 GitLab MR #{mr_iid} (项目 {project_id})")

        # 1. 获取 MR 信息和变更
        try:
            mr_data = await self.gitlab.get_mr_changes(project_id, mr_iid)
        except Exception as e:
            logger.error(f"获取 MR 数据失败: {e}")
            return {"status": "error", "message": str(e)}

        mr_title = mr_data.get("title", "")
        mr_description = mr_data.get("description", "")
        author = mr_data.get("author", {}).get("username", "unknown")
        diff_refs = mr_data.get("diff_refs", {})
        changes = mr_data.get("changes", [])

        # 检查变更大小
        total_changes = len(changes)
        if total_changes == 0:
            logger.info(f"MR #{mr_iid} 无代码变更")
            return {"status": "skipped", "reason": "no_changes"}

        # 过滤过大的 diff
        diff_size = sum(len(c.get("diff", "")) for c in changes)
        if diff_size > self.settings.MAX_DIFF_SIZE:
            logger.warning(f"MR #{mr_iid} diff 过大 ({diff_size} bytes)")
            await self.gitlab.post_summary_comment(
                project_id, mr_iid,
                "⚠️ 本次代码变更过大，已跳过自动审查。请人工仔细审查。"
            )
            return {"status": "skipped", "reason": "diff_too_large"}

        results = {
            "platform": "gitlab",
            "project_id": project_id,
            "mr_iid": mr_iid,
            "status": "completed",
            "reviews": []
        }

        # 2. 审查每个文件变更
        file_count = 0
        for change in changes:
            file_path = change.get("new_path") or change.get("old_path")
            diff = change.get("diff", "")

            # 跳过非代码文件
            if not diff or self._should_skip_file(file_path):
                continue

            file_count += 1
            # 脱敏处理
            safe_diff = sanitize_code(diff)

            # 解析变更块
            change_blocks = parse_diff(safe_diff)

            # 审查每个变更块
            for block in change_blocks:
                if not block.get("content"):
                    continue

                review_result = await self._review_code_block(
                    file_path, block, mr_title
                )

                if review_result and review_result.get("comment"):
                    results["reviews"].append(review_result)

                    # 发布行级评论
                    if review_result.get("line") and diff_refs:
                        try:
                            await self.gitlab.post_line_comment(
                                project_id, mr_iid,
                                file_path,
                                review_result["line"],
                                review_result["comment"],
                                diff_refs
                            )
                        except Exception as e:
                            logger.warning(f"发布评论失败: {e}")

        # 3. 生成变更总结
        summary = await self._generate_summary(
            mr_title, mr_description, changes, author, file_count
        )

        await self.gitlab.post_summary_comment(project_id, mr_iid, summary)
        results["summary"] = summary

        logger.info(f"GitLab MR #{mr_iid} 审查完成，发现 {len(results['reviews'])} 个问题")
        return results

    # ==================== GitHub 审查 ====================

    async def review_github_pr(self, owner: str, repo: str, pr_number: int) -> dict:
        """执行 GitHub PR 代码审查"""
        logger.info(f"开始审查 GitHub PR #{pr_number} ({owner}/{repo})")

        # 1. 获取 PR 信息
        try:
            pr_info = await self.github.get_pr_info(owner, repo, pr_number)
            pr_files = await self.github.get_pr_files(owner, repo, pr_number)
        except Exception as e:
            logger.error(f"获取 PR 数据失败: {e}")
            return {"status": "error", "message": str(e)}

        pr_title = pr_info.get("title", "")
        pr_body = pr_info.get("body", "")
        author = pr_info.get("user", {}).get("login", "unknown")
        head_sha = pr_info.get("head", {}).get("sha", "")
        base_ref = pr_info.get("base", {}).get("ref", "")

        # 检查变更大小
        if not pr_files:
            logger.info(f"PR #{pr_number} 无代码变更")
            return {"status": "skipped", "reason": "no_changes"}

        # 过滤过大的 diff
        diff_size = sum(len(f.get("patch", "")) for f in pr_files)
        if diff_size > self.settings.MAX_DIFF_SIZE:
            logger.warning(f"PR #{pr_number} diff 过大 ({diff_size} bytes)")
            await self.github.create_issue_comment(
                owner, repo, pr_number,
                "⚠️ 本次代码变更过大，已跳过自动审查。请人工仔细审查。"
            )
            return {"status": "skipped", "reason": "diff_too_large"}

        results = {
            "platform": "github",
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
            "status": "completed",
            "reviews": []
        }

        # 2. 审查每个文件变更
        review_comments = []
        file_count = 0

        for file_data in pr_files:
            file_path = file_data.get("filename")
            patch = file_data.get("patch", "")
            status = file_data.get("status", "modified")

            # 跳过非代码文件和删除的文件
            if not patch or status == "removed" or self._should_skip_file(file_path):
                continue

            file_count += 1
            # 脱敏处理
            safe_patch = sanitize_code(patch)

            # 解析变更块
            change_blocks = parse_diff(safe_patch)

            # 审查每个变更块
            position = 1
            for block in change_blocks:
                if not block.get("content"):
                    continue

                review_result = await self._review_code_block(
                    file_path, block, pr_title
                )

                if review_result and review_result.get("comment"):
                    results["reviews"].append(review_result)

                    # 收集评论（批量提交）
                    review_comments.append({
                        "path": file_path,
                        "position": position,
                        "body": review_result["comment"]
                    })

                position += 1

        # 3. 批量发布审查评论
        if review_comments and head_sha:
            try:
                await self.github.create_review(
                    owner, repo, pr_number,
                    head_sha,
                    review_comments,
                    body="🤖 AI 代码审查完成，详见下方评论。"
                )
            except Exception as e:
                logger.warning(f"批量发布评论失败: {e}")

        # 4. 生成变更总结
        summary = await self._generate_summary(
            pr_title, pr_body,
            [{"new_path": f.get("filename"), "diff": f.get("patch", "")} for f in pr_files],
            author, file_count
        )

        await self.github.create_issue_comment(owner, repo, pr_number, summary)
        results["summary"] = summary

        logger.info(f"GitHub PR #{pr_number} 审查完成，发现 {len(results['reviews'])} 个问题")
        return results

    async def _review_code_block(
        self,
        file_path: str,
        block: dict,
        mr_title: str
    ) -> Optional[dict]:
        """审查单个代码变更块"""
        code = block.get("content", "")
        line_num = block.get("new_line")
        change_type = block.get("type", "modified")

        if not code.strip():
            return None

        # 代码质量审查
        quality_prompt = CODE_QUALITY_PROMPT.format(file_path=file_path)
        quality_review = await self.llm.chat(
            quality_prompt,
            f"审查以下代码变更（类型: {change_type}）:\n```\n{code}\n```"
        )

        # 安全漏洞审查
        security_prompt = SECURITY_PROMPT.format(file_path=file_path)
        security_review = await self.llm.chat(
            security_prompt,
            f"检查以下代码是否存在安全漏洞:\n```\n{code}\n```"
        )

        # 合并评论
        comment = self._format_comment(quality_review, security_review)

        if comment and comment.strip() and not self._is_no_issue(comment):
            return {
                "file": file_path,
                "line": line_num,
                "comment": comment,
                "type": "warning"
            }

        return None

    async def _generate_summary(
        self,
        title: str,
        description: str,
        changes: list,
        author: str,
        file_count: int
    ) -> str:
        """生成变更总结"""
        files_changed = [
            c.get("new_path") or c.get("old_path")
            for c in changes
            if not self._should_skip_file(c.get("new_path") or c.get("old_path", ""))
        ]

        summary_input = f"""
MR 标题: {title}
作者: {author}
描述: {description or '无'}
变更文件数: {file_count}
主要变更文件: {', '.join(files_changed[:10])}
"""

        summary = await self.llm.chat(SUMMARY_PROMPT, summary_input)

        # 格式化输出
        return f"""## 🤖 AI 代码审查报告

**审查模型**: {self.settings.LLM_PROVIDER} / {self.settings.LLM_MODEL}

---

{summary}

---

> 💡 此报告由 AI 自动生成，建议结合人工审查确认。如有疑问请联系代码作者。
"""

    def _format_comment(self, quality: str, security: str) -> str:
        """格式化审查评论"""
        parts = []

        if quality and not self._is_no_issue(quality):
            parts.append(f"**💡 代码质量**: {quality}")

        if security and not self._is_no_issue(security):
            parts.append(f"**🔒 安全风险**: {security}")

        return "\n\n".join(parts) if parts else ""

    def _is_no_issue(self, text: str) -> bool:
        """判断是否无问题"""
        no_issue_keywords = ["无问题", "无安全风险", "无明显问题", "未发现"]
        return any(kw in text for kw in no_issue_keywords)

    def _should_skip_file(self, file_path: str) -> bool:
        """判断是否跳过该文件"""
        skip_extensions = [
            ".md", ".txt", ".json", ".yaml", ".yml",
            ".lock", ".toml", ".ini", ".conf",
            ".svg", ".png", ".jpg", ".gif", ".ico",
            ".pdf", ".doc", ".xls"
        ]
        return any(file_path.endswith(ext) for ext in skip_extensions)