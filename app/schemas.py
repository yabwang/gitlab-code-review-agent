from pydantic import BaseModel
from typing import Optional, List


class WebhookPayload(BaseModel):
    """GitLab Webhook 数据模型"""
    object_kind: str
    project: dict
    object_attributes: dict
    changes: Optional[dict] = None


class ReviewResult(BaseModel):
    """审查结果模型"""
    file: str
    line: Optional[int]
    comment: str
    type: str = "info"


class MRReviewResponse(BaseModel):
    """MR 审查响应模型"""
    project_id: int
    mr_iid: int
    status: str
    reviews: List[ReviewResult] = []
    summary: Optional[str] = None