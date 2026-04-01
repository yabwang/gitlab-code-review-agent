# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Multi Platform Agent - AI-powered multi-platform agent for code review and more.

智能 Spring Boot 服务，通过 Webhook 自动触发 AI 代码审查，支持双平台（GitLab MR 和 GitHub PR）。

## 常用命令

```bash
# 构建（跳过测试）
mvn clean package -DskipTests

# 运行
mvn spring-boot:run
# 或
java -jar target/multi-platform-agent-2.0.0-java.jar

# 运行测试
mvn test

# 运行单个测试类
mvn test -Dtest=ReviewServiceTest

# Docker 部署
docker-compose up -d
```

## 架构

核心流程：Webhook → Controller → Service（异步）→ LLM Client → Git/GitLab Client → 评论发布

**核心组件**：
- `WebhookController` - 接收 GitLab/GitHub Webhook，验证签名/Token
- `ReviewService` - 异步执行审查流程（`@Async`）
- `LlmClient` - LangChain4j ChatLanguageModel，三种审查：代码质量、安全扫描、变更总结
- `GitlabClient` / `GithubClient` - API 客户端，获取变更、发布评论

**配置类**：
- `LlmConfig` - 创建 ChatLanguageModel Bean（OpenAI-compatible API）
- `GitlabConfig` / `GithubConfig` - 平台 Token 和 Webhook Secret
- `ReviewConfig` - max-diff-size、timeout

**依赖**：
- github-api（GitHub API）
- LangChain4j + langchain4j-open-ai（LLM 集成）

## 配置

环境变量（参考 `.env.example`）：
- `GITLAB_URL` / `GITLAB_TOKEN` / `GITLAB_WEBHOOK_SECRET`
- `GITHUB_TOKEN` / `GITHUB_WEBHOOK_SECRET`
- `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_API_URL` / `LLM_MODEL`

默认 LLM 配置：DeepSeek API（`https://api.deepseek.com/v1`，model: `deepseek-coder`）

## API 接口

| 接口 | 说明 |
|------|------|
| `/webhook/gitlab` | GitLab Webhook（object_kind=merge_request） |
| `/webhook/github` | GitHub Webhook（event=pull_request） |
| `/review/gitlab/{projectId}/{mrIid}` | 手动触发 GitLab 审查 |
| `/review/github/{owner}/{repo}/{prNumber}` | 手动触发 GitHub 审查 |

## 审查流程

1. Webhook 触发（action: open/reopen/update）
2. 获取 MR/PR 文件变更
3. 过滤非代码文件（.md/.json/.yaml 等）
4. 对每个文件：`reviewQuality()` + `scanSecurity()`
5. 生成总结 `generateSummary()`
6. 格式化报告发布评论