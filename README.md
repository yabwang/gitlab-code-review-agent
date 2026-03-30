# GitLab/GitHub AI Code Review Agent

智能代码审查服务，支持 GitLab 和 GitHub Webhook 自动触发 AI 代码审查，具备代码自动修复和多 Agent 协作能力。

## 功能特性

- 🤖 **AI 代码审查**: 使用国内大模型（DeepSeek、通义千问、智谱、GLM）进行代码分析
- 🔍 **多维度审查**: 代码质量、安全漏洞、变更总结
- 🔗 **双平台支持**: GitLab MR 和 GitHub PR
- 📍 **行级评论**: 问题定位到具体代码行
- 🔧 **自动修复建议**: 生成可一键应用的修复代码
- 🔐 **安全脱敏**: 自动过滤敏感信息
- 🤝 **多 Agent 架构**: 支持分布式部署和 Agent 间协作

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
| 自定义 | `custom` | 自定义模型 |

## API 接口

### 审查接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/webhook/gitlab` | POST | GitLab Webhook 入口 |
| `/webhook/github` | POST | GitHub Webhook 入口 |
| `/review/gitlab/{project_id}/{mr_iid}` | POST | 手动触发 GitLab 审查 |
| `/review/github/{owner}/{repo}/{pr_number}` | POST | 手动触发 GitHub 审查 |

### 修复接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/fix/gitlab/{project_id}/{mr_iid}` | POST | 生成 GitLab MR 修复建议 |
| `/fix/github/{owner}/{repo}/{pr_number}` | POST | 生成 GitHub PR 修复建议 |

### 其他接口

| 接口 | 方法 | 说明 |
|------|------|------|
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
| `LLM_API_URL` | LLM API 地址（自定义时使用） |
| `LLM_MODEL` | LLM 模型名称 |
| `MAX_DIFF_SIZE` | 最大 diff 大小（字节） |
| `REVIEW_TIMEOUT` | 审查超时时间（秒） |

### Agent 配置

| 配置项 | 说明 |
|--------|------|
| `AGENT_MODE` | Agent 模式：single（单进程）/ multi（多 Agent） |
| `COORDINATOR_PORT` | 协调器 Agent 端口 |
| `SECURITY_AGENT_PORT` | 安全扫描 Agent 端口 |
| `LLM_AGENT_PORT` | LLM 服务 Agent 端口 |

## GitHub Token 权限要求

创建 GitHub Personal Access Token 时需要以下权限:
- `repo` - 读取仓库内容和发布 PR 评论
- `pull_requests:write` - 创建 PR Review

## 工作流程

```
开发者提交 MR/PR → 平台发送 Webhook → Agent 获取代码变更
    → LLM 分析代码 → 发布审查评论 → 开发者在 MR/PR 界面查看
    → 可选：生成修复建议 → 用户一键应用修复
```

## 多 Agent 架构

项目支持多 Agent 协作部署，每个 Agent 独立运行并通过 HTTP 互相调用。

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ Coordinator   │     │  Security     │     │     LLM       │
│   Agent       │────▶│   Agent       │     │    Agent      │
│  端口: 8080   │     │  端口: 8081   │     │  端口: 8082   │
├───────────────┤     ├───────────────┤     ├───────────────┤
│ - Webhook接收 │     │ - SQL注入检测 │     │ - LLM调用     │
│ - 任务编排    │     │ - XSS检测     │     │ - 代码修复    │
│ - 结果汇总    │     │ - 命令注入    │     │ - 总结生成    │
└───────────────┘     └───────────────┘     └───────────────┘
```

### 启动多 Agent

```bash
# 列出所有 Agent
python scripts/start_agents.py --list

# 启动所有 Agent
python scripts/start_agents.py --all

# 启动单个 Agent
python scripts/start_agents.py --agent coordinator --port 8080
python scripts/start_agents.py --agent security --port 8081
python scripts/start_agents.py --agent llm --port 8082
```

### Agent 能力

| Agent | 能力 | 说明 |
|-------|------|------|
| CoordinatorAgent | code_review, task_orchestration | 任务编排和审查流程控制 |
| SecurityAgent | security_scan | SQL注入、XSS、命令注入检测 |
| LLMAgent | llm_chat, code_fix, summary_generate | LLM 调用服务 |

## 目录结构

```
gitlab-code-review-agent/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── gitlab_client.py     # GitLab API
│   ├── github_client.py     # GitHub API
│   ├── llm_client.py        # LLM API
│   ├── reviewer.py          # 审查核心
│   ├── fixer.py             # 修复核心
│   ├── agents/              # 多 Agent 模块
│   │   ├── protocol.py      # 通信协议
│   │   ├── registry.py      # 注册中心
│   │   ├── client.py        # Agent 客户端
│   │   ├── base.py          # Agent 基类
│   │   ├── coordinator.py   # 协调器 Agent
│   │   ├── security_agent.py # 安全扫描 Agent
│   │   └── llm_agent.py     # LLM 服务 Agent
│   └── utils/               # 工具模块
│       ├── code_parser.py   # Diff 解析
│       ├── sanitizer.py     # 敏感信息脱敏
│       └── prompt_templates.py # 提示词模板
├── scripts/
│   ├── setup_gitlab_webhook.sh # GitLab Webhook 配置
│   └── start_agents.py      # Agent 启动脚本
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

## 示例：调用修复接口

```bash
# 生成 GitHub PR 修复建议
curl -X POST "http://localhost:8080/fix/github/yabwang/yabwang.github.io/1"

# 结果会在 PR 中显示可一键应用的修复建议
```

## 许可证

MIT