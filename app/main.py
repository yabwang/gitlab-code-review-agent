import logging
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import get_settings
from app.reviewer import CodeReviewer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    logger.info(f"服务启动，LLM Provider: {settings.LLM_PROVIDER}")
    yield
    logger.info("服务关闭")


app = FastAPI(
    title="GitLab AI Code Review Agent",
    description="智能代码审查服务，集成 GitLab Webhook",
    version="1.0.0",
    lifespan=lifespan
)


def verify_webhook_token(secret: str, received_token: str) -> bool:
    """验证 Webhook Token（GitLab 直接传递 token，不是签名）"""
    if not secret:
        return True  # 未配置 secret 时跳过验证
    return hmac.compare_digest(secret, received_token)


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """处理 GitLab Merge Request Webhook"""
    try:
        payload = await request.body()
        token = request.headers.get("X-Gitlab-Token", "")

        # 验证 Token
        if settings.GITLAB_WEBHOOK_SECRET:
            if not verify_webhook_token(settings.GITLAB_WEBHOOK_SECRET, token):
                logger.warning("Webhook Token 验证失败")
                raise HTTPException(401, "Invalid webhook token")

        data = await request.json()

        # 只处理 MR 事件
        object_kind = data.get("object_kind", "")
        if object_kind != "merge_request":
            logger.debug(f"跳过非 MR 事件: {object_kind}")
            return JSONResponse({"status": "skipped", "reason": "not_merge_request"})

        # 只处理 open/reopen/update 事件
        attrs = data.get("object_attributes", {})
        action = attrs.get("action", "")
        if action not in ["open", "reopen", "update"]:
            logger.debug(f"跳过 MR action: {action}")
            return JSONResponse({"status": "skipped", "reason": f"action_{action}"})

        # 获取项目和 MR 信息
        project_id = data.get("project", {}).get("id")
        mr_iid = attrs.get("iid")
        mr_title = attrs.get("title", "")

        if not project_id or not mr_iid:
            logger.error("缺少项目或 MR 信息")
            return JSONResponse({"status": "error", "reason": "missing_data"}, 400)

        logger.info(f"收到 MR #{mr_iid} ({action}): {mr_title}")

        # 后台异步执行审查
        background_tasks.add_task(run_review_task, project_id, mr_iid)

        return JSONResponse({
            "status": "accepted",
            "message": f"审查任务已启动: MR #{mr_iid}",
            "project_id": project_id,
            "mr_iid": mr_iid
        })

    except Exception as e:
        logger.error(f"处理 Webhook 失败: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, 500)


async def run_review_task(project_id: int, mr_iid: int):
    """后台执行代码审查任务"""
    try:
        reviewer = CodeReviewer()
        result = await reviewer.review_mr(project_id, mr_iid)
        logger.info(f"审查完成: {result.get('status')}, 问题数: {len(result.get('reviews', []))}")
    except Exception as e:
        logger.error(f"审查任务失败: {e}")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "gitlab_url": settings.GITLAB_URL
    }


@app.get("/")
async def root():
    """服务根信息"""
    return {
        "name": "GitLab AI Code Review Agent",
        "version": "1.0.0",
        "description": "智能代码审查服务",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health"
        },
        "supported_llm": ["deepseek", "qwen", "zhipu", "doubao"]
    }


@app.post("/review/{project_id}/{mr_iid}")
async def manual_review(project_id: int, mr_iid: int, background_tasks: BackgroundTasks):
    """手动触发审查接口"""
    logger.info(f"手动触发审查: 项目 {project_id}, MR #{mr_iid}")
    background_tasks.add_task(run_review_task, project_id, mr_iid)
    return {
        "status": "accepted",
        "message": f"审查任务已启动: MR #{mr_iid}"
    }