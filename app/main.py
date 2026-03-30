import logging
import hmac
import hashlib
import json
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
    title="GitLab/GitHub AI Code Review Agent",
    description="智能代码审查服务，支持 GitLab 和 GitHub Webhook",
    version="1.1.0",
    lifespan=lifespan
)


def verify_gitlab_webhook_token(secret: str, received_token: str) -> bool:
    """验证 GitLab Webhook Token"""
    if not secret:
        return True
    return hmac.compare_digest(secret, received_token)


def verify_github_webhook_signature(secret: str, payload: bytes, signature: str) -> bool:
    """验证 GitHub Webhook 签名 (HMAC-SHA256)"""
    if not secret:
        return True
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhook/gitlab")
async def handle_gitlab_webhook(request: Request, background_tasks: BackgroundTasks):
    """处理 GitLab Merge Request Webhook"""
    try:
        payload = await request.body()
        token = request.headers.get("X-Gitlab-Token", "")

        # 验证 Token
        if settings.GITLAB_WEBHOOK_SECRET:
            if not verify_gitlab_webhook_token(settings.GITLAB_WEBHOOK_SECRET, token):
                logger.warning("GitLab Webhook Token 验证失败")
                raise HTTPException(401, "Invalid webhook token")

        data = json.loads(payload)

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

        logger.info(f"收到 GitLab MR #{mr_iid} ({action}): {mr_title}")

        # 后台异步执行审查
        background_tasks.add_task(run_gitlab_review_task, project_id, mr_iid)

        return JSONResponse({
            "status": "accepted",
            "platform": "gitlab",
            "message": f"审查任务已启动: MR #{mr_iid}",
            "project_id": project_id,
            "mr_iid": mr_iid
        })

    except Exception as e:
        logger.error(f"处理 GitLab Webhook 失败: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, 500)


@app.post("/webhook/github")
async def handle_github_webhook(request: Request, background_tasks: BackgroundTasks):
    """处理 GitHub Pull Request Webhook"""
    try:
        payload = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")

        # 验证签名
        if settings.GITHUB_WEBHOOK_SECRET:
            if not verify_github_webhook_signature(settings.GITHUB_WEBHOOK_SECRET, payload, signature):
                logger.warning("GitHub Webhook 签名验证失败")
                raise HTTPException(401, "Invalid webhook signature")

        data = json.loads(payload)

        # 只处理 PR 事件
        event_type = request.headers.get("X-GitHub-Event", "")
        if event_type != "pull_request":
            logger.debug(f"跳过非 PR 事件: {event_type}")
            return JSONResponse({"status": "skipped", "reason": "not_pull_request"})

        # 只处理 opened/reopened/synchronize 事件
        action = data.get("action", "")
        if action not in ["opened", "reopened", "synchronize"]:
            logger.debug(f"跳过 PR action: {action}")
            return JSONResponse({"status": "skipped", "reason": f"action_{action}"})

        # 获取仓库和 PR 信息
        pr_data = data.get("pull_request", {})
        repo = data.get("repository", {})
        owner = repo.get("owner", {}).get("login")
        repo_name = repo.get("name")
        pr_number = pr_data.get("number")
        pr_title = pr_data.get("title", "")

        if not owner or not repo_name or not pr_number:
            logger.error("缺少仓库或 PR 信息")
            return JSONResponse({"status": "error", "reason": "missing_data"}, 400)

        logger.info(f"收到 GitHub PR #{pr_number} ({action}): {pr_title} - {owner}/{repo_name}")

        # 后台异步执行审查
        background_tasks.add_task(run_github_review_task, owner, repo_name, pr_number)

        return JSONResponse({
            "status": "accepted",
            "platform": "github",
            "message": f"审查任务已启动: PR #{pr_number}",
            "owner": owner,
            "repo": repo_name,
            "pr_number": pr_number
        })

    except Exception as e:
        logger.error(f"处理 GitHub Webhook 失败: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, 500)


async def run_gitlab_review_task(project_id: int, mr_iid: int):
    """后台执行 GitLab 代码审查任务"""
    try:
        reviewer = CodeReviewer()
        result = await reviewer.review_gitlab_mr(project_id, mr_iid)
        logger.info(f"GitLab 审查完成: {result.get('status')}, 问题数: {len(result.get('reviews', []))}")
    except Exception as e:
        logger.error(f"GitLab 审查任务失败: {e}")


async def run_github_review_task(owner: str, repo: str, pr_number: int):
    """后台执行 GitHub 代码审查任务"""
    try:
        reviewer = CodeReviewer()
        result = await reviewer.review_github_pr(owner, repo, pr_number)
        logger.info(f"GitHub 审查完成: {result.get('status')}, 问题数: {len(result.get('reviews', []))}")
    except Exception as e:
        logger.error(f"GitHub 审查任务失败: {e}")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "platforms": {
            "gitlab": {
                "enabled": bool(settings.GITLAB_TOKEN),
                "url": settings.GITLAB_URL
            },
            "github": {
                "enabled": bool(settings.GITHUB_TOKEN)
            }
        }
    }


@app.get("/")
async def root():
    """服务根信息"""
    return {
        "name": "GitLab/GitHub AI Code Review Agent",
        "version": "1.1.0",
        "description": "智能代码审查服务，支持 GitLab 和 GitHub",
        "endpoints": {
            "gitlab_webhook": "/webhook/gitlab",
            "github_webhook": "/webhook/github",
            "health": "/health"
        },
        "supported_llm": ["deepseek", "qwen", "zhipu", "doubao"]
    }


@app.post("/review/gitlab/{project_id}/{mr_iid}")
async def manual_gitlab_review(project_id: int, mr_iid: int, background_tasks: BackgroundTasks):
    """手动触发 GitLab MR 审查"""
    logger.info(f"手动触发 GitLab 审查: 项目 {project_id}, MR #{mr_iid}")
    background_tasks.add_task(run_gitlab_review_task, project_id, mr_iid)
    return {
        "status": "accepted",
        "platform": "gitlab",
        "message": f"审查任务已启动: MR #{mr_iid}"
    }


@app.post("/review/github/{owner}/{repo}/{pr_number}")
async def manual_github_review(owner: str, repo: str, pr_number: int, background_tasks: BackgroundTasks):
    """手动触发 GitHub PR 审查"""
    logger.info(f"手动触发 GitHub 审查: {owner}/{repo} PR #{pr_number}")
    background_tasks.add_task(run_github_review_task, owner, repo, pr_number)
    return {
        "status": "accepted",
        "platform": "github",
        "message": f"审查任务已启动: PR #{pr_number}"
    }