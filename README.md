# GitLab/GitHub AI Code Review Agent (Java)

智能代码审查服务，支持 GitLab 和 GitHub Webhook 自动触发 AI 代码审查。

## 技术栈

- Java 17
- Spring Boot 3.2
- LangChain4j (LLM 集成)
- gitlab4j-api (GitLab API)
- github-api (GitHub API)

## 功能特性

- 🤖 **AI 代码审查**: 使用大模型进行代码分析
- 🔍 **多维度审查**: 代码质量、安全漏洞、变更总结
- 🔗 **双平台支持**: GitLab MR 和 GitHub PR
- 📝 **自动评论**: 审查结果自动发布到 MR/PR

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际配置
```

### 2. 本地运行

```bash
# Maven 构建
mvn clean package -DskipTests

# 运行
java -jar target/gitlab-code-review-agent-2.0.0-java.jar

# 或使用 Maven
mvn spring-boot:run
```

### 3. Docker 部署

```bash
docker-compose up -d
```

## 配置说明

| 配置项 | 环境变量 | 说明 |
|--------|----------|------|
| GitLab URL | GITLAB_URL | GitLab 服务器地址 |
| GitLab Token | GITLAB_TOKEN | GitLab Access Token |
| GitLab Secret | GITLAB_WEBHOOK_SECRET | Webhook 验证密钥 |
| GitHub Token | GITHUB_TOKEN | GitHub Personal Access Token |
| GitHub Secret | GITHUB_WEBHOOK_SECRET | Webhook 验证密钥 |
| LLM Provider | LLM_PROVIDER | LLM 提供商 |
| LLM API Key | LLM_API_KEY | LLM API Key |
| LLM API URL | LLM_API_URL | LLM API 地址 |
| LLM Model | LLM_MODEL | 模型名称 |

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/webhook/gitlab` | POST | GitLab Webhook 入口 |
| `/webhook/github` | POST | GitHub Webhook 入口 |
| `/review/gitlab/{projectId}/{mrIid}` | POST | 手动触发 GitLab 审查 |
| `/review/github/{owner}/{repo}/{prNumber}` | POST | 手动触发 GitHub 审查 |
| `/health` | GET | 健康检查 |
| `/` | GET | 服务信息 |

## 项目结构

```
src/main/java/com/github/review/agent/
├── GitlabCodeReviewAgentApplication.java  # 主类
├── config/           # 配置类
├── controller/       # 控制器
├── service/          # 业务服务
├── client/           # API 客户端
├── model/            # 数据模型
└── exception/        # 异常处理
```

## 分支说明

| 分支 | 说明 |
|------|------|
| `main` | Java 版本（当前） |
| `python-version` | Python 版本 |

## 许可证

MIT