import httpx
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API 客户端"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def get_pr_info(self, owner: str, repo: str, pr_number: int) -> dict:
        """获取 PR 基本信息"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list:
        """获取 PR 变更文件列表"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_file_content(self, owner: str, repo: str, path: str, ref: str) -> str:
        """获取文件内容"""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={ref}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("encoding") == "base64":
                import base64
                return base64.b64decode(data["content"]).decode("utf-8")
            return data.get("content", "")

    async def create_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        commit_id: str,
        path: str,
        position: int
    ) -> dict:
        """在 PR 指定位置发布审查评论"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        data = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
            "position": position
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self.headers, json=data)
            resp.raise_for_status()
            return resp.json()

    async def create_issue_comment(self, owner: str, repo: str, pr_number: int, body: str) -> dict:
        """发布 PR 整体评论"""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        data = {"body": body}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self.headers, json=data)
            resp.raise_for_status()
            return resp.json()

    async def create_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        comments: list,
        body: str = ""
    ) -> dict:
        """创建 PR Review（批量评论）"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        data = {
            "commit_id": commit_id,
            "body": body,
            "event": "COMMENT",
            "comments": comments
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self.headers, json=data)
            resp.raise_for_status()
            return resp.json()

    async def get_repo_info(self, owner: str, repo: str) -> dict:
        """获取仓库信息"""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def create_suggestion_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        path: str,
        position: int,
        issue_description: str,
        suggestion_code: str
    ) -> dict:
        """在 PR 发布 suggestion 评论（用户可一键应用）"""
        # GitHub suggestion 格式
        body = f"""**{issue_description}**

```suggestion
{suggestion_code}
```"""

        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        data = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
            "position": position
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self.headers, json=data)
            resp.raise_for_status()
            return resp.json()

    async def create_review_with_suggestions(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        suggestions: list
    ) -> dict:
        """批量创建带 suggestion 的 PR Review"""
        comments = []
        for s in suggestions:
            body = f"""**{s['issue_description']}**

```suggestion
{s['suggestion_code']}
```"""
            comments.append({
                "path": s["path"],
                "position": s["position"],
                "body": body
            })

        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        data = {
            "commit_id": commit_id,
            "body": "🤖 AI 代码修复建议，可逐条应用。",
            "event": "COMMENT",
            "comments": comments
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self.headers, json=data)
            resp.raise_for_status()
            return resp.json()