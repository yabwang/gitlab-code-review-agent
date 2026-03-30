# GitLab/GitHub AI Code Review Agent

智能代码审查服务，支持 GitLab 和 GitHub Webhook 自动触发 AI 代码审查。

## 功能特性

- 🤖 **AI 代码审查**: 使用国内大模型（DeepSeek、通义千问、智谱）进行代码分析
- 🔍 **多维度审查**: 代码质量、安全漏洞、变更总结
- 🔗 **双平台支持**: GitLab MR 和 GitHub PR
- 📍 **行级评论**: 问题定位到具体代码行
- 🔐 **安全脱敏**: 自动过滤敏感信息

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际配置
```

### 2. 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 8080
```

### 3. Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 4. 配置 Webhook

#### GitLab

```bash
# 使用脚本自动配置
export GITLAB_URL="https://gitlab.yourcompany.com"
export GITLAB_TOKEN="your-token"

./scripts/setup_gitlab_webhook.sh <PROJECT_ID>
```

或在 GitLab 项目设置中手动配置:
- URL: `http://your-server:8080/webhook/gitlab`
- Secret Token: 设置一个随机字符串
- Trigger: Merge Request events

#### GitHub

在 GitHub 仓库 Settings → Webhooks 中配置:
- URL: `http://your-server:8080/webhook/github`
- Secret: 设置一个随机字符串
- Content type: `application/json`
- Trigger: Pull Request events

**注意**: GitHub Webhook 需要公网可访问的地址，可使用 ngrok 等工具进行本地测试。

## 支持的 LLM 提供商

| 提供商 | 配置值 | 模型 |
|--------|--------|------|
| DeepSeek | `deepseek` | deepseek-coder |
| 通义千问 | `qwen` | qwen-coder-plus |
| 智谱 GLM | `zhipu` | glm-4 |
| 豆包 | `doubao` | doubao-pro-32k |

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/webhook/gitlab` | POST | GitLab Webhook 入口 |
| `/webhook/github` | POST | GitHub Webhook 入口 |
| `/review/gitlab/{project_id}/{mr_iid}` | POST | 手动触发 GitLab 审查 |
| `/review/github/{owner}/{repo}/{pr_number}` | POST | 手动触发 GitHub 审查 |
| `/health` | GET | 健康检查 |
| `/` | GET | 服务信息 |

## 配置说明

| 配置项 | 说明 |
|--------|------|
| `GITLAB_URL` | GitLab 服务器地址 |
| `GITLAB_TOKEN` | GitLab Access Token |
| `GITLAB_WEBHOOK_SECRET` | GitLab Webhook 验证密钥 |
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `GITHUB_WEBHOOK_SECRET` | GitHub Webhook 验证密钥 |
| `LLM_PROVIDER` | LLM 提供商 |
| `LLM_API_KEY` | LLM API Key |
| `MAX_DIFF_SIZE` | 最大 diff 大小（字节） |
| `REVIEW_TIMEOUT` | 审查超时时间（秒） |

## GitHub Token 权限要求

创建 GitHub Personal Access Token 时需要以下权限:
- `repo` - 读取仓库内容和发布 PR 评论
- `pull_requests:write` - 创建 PR Review

## 工作流程

```
开发者提交 MR/PR → 平台发送 Webhook → Agent 获取代码变更
    → LLM 分析代码 → 发布审查评论 → 开发者在 MR/PR 界面查看
```

## 目录结构

```
gitlab-code-review-agent/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 配置管理
│   ├── gitlab_client.py # GitLab API
│   ├── github_client.py # GitHub API
│   ├── llm_client.py    # LLM API
│   ├── reviewer.py      # 审查核心
│   └── utils/           # 工具模块
├── scripts/             # 部署脚本
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 本地测试 GitHub Webhook

```bash
# 使用 ngrok 暴露本地服务
ngrok http 8080

# 将 ngrok 地址配置到 GitHub Webhook
# URL: https://xxx.ngrok.io/webhook/github
```

## 许可证

MIT