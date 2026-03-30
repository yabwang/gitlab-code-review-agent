import httpx
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


class GitLabClient:
    """GitLab API 客户端"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.GITLAB_URL.rstrip('/')
        self.headers = {"PRIVATE-TOKEN": self.settings.GITLAB_TOKEN}

    async def get_mr_changes(self, project_id: int, mr_iid: int) -> dict:
        """获取 MR 的完整信息和代码变更"""
        url = f"{self.base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_mr_diffs(self, project_id: int, mr_iid: int) -> list:
        """获取 MR diff 详情"""
        url = f"{self.base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/diffs"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def post_line_comment(
        self,
        project_id: int,
        mr_iid: int,
        file_path: str,
        line: int,
        body: str,
        diff_refs: dict
    ) -> dict:
        """在 MR 指定代码行发布评论"""
        url = f"{self.base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/discussions"
        data = {
            "body": body,
            "position": {
                "position_type": "text",
                "base_sha": diff_refs["base_sha"],
                "head_sha": diff_refs["head_sha"],
                "start_sha": diff_refs["start_sha"],
                "new_path": file_path,
                "new_line": line
            }
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self.headers, json=data)
            resp.raise_for_status()
            return resp.json()

    async def post_summary_comment(self, project_id: int, mr_iid: int, body: str) -> dict:
        """发布 MR 整体评论（无位置信息）"""
        url = f"{self.base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/discussions"
        data = {"body": body}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self.headers, json=data)
            resp.raise_for_status()
            return resp.json()

    async def get_project_info(self, project_id: int) -> dict:
        """获取项目信息"""
        url = f"{self.base_url}/api/v4/projects/{project_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()