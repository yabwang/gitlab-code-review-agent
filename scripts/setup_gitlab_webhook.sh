#!/bin/bash

# GitLab Webhook 自动配置脚本
# 使用方法: ./setup_gitlab_webhook.sh <PROJECT_ID>

set -e

# 配置
GITLAB_URL="${GITLAB_URL:-https://gitlab.yourcompany.com}"
GITLAB_TOKEN="${GITLAB_TOKEN}"
REVIEW_SERVICE_URL="${REVIEW_SERVICE_URL:-http://your-server:8080/webhook}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-your-secret-token}"

if [ -z "$GITLAB_TOKEN" ]; then
    echo "错误: 请设置 GITLAB_TOKEN 环境变量"
    exit 1
fi

PROJECT_ID=$1
if [ -z "$PROJECT_ID" ]; then
    echo "使用方法: $0 <PROJECT_ID>"
    exit 1
fi

echo "配置 GitLab Webhook..."
echo "项目 ID: $PROJECT_ID"
echo "GitLab URL: $GITLAB_URL"
echo "Webhook URL: $REVIEW_SERVICE_URL"

# 检查是否已存在相同的 webhook
EXISTING=$(curl -s --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    "$GITLAB_URL/api/v4/projects/$PROJECT_ID/hooks" | \
    grep -o "\"url\":\"$REVIEW_SERVICE_URL\"" || true)

if [ -n "$EXISTING" ]; then
    echo "Webhook 已存在，跳过创建"
    exit 0
fi

# 创建 Webhook
RESPONSE=$(curl -s --request POST \
    "$GITLAB_URL/api/v4/projects/$PROJECT_ID/hooks" \
    --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    --data "url=$REVIEW_SERVICE_URL" \
    --data "token=$WEBHOOK_SECRET" \
    --data "merge_requests_events=true" \
    --data "push_events=false" \
    --data "issues_events=false" \
    --data "enable_ssl_verification=false")

if echo "$RESPONSE" | grep -q "\"id\""; then
    echo "✅ Webhook 创建成功!"
    echo "响应: $RESPONSE"
else
    echo "❌ Webhook 创建失败"
    echo "响应: $RESPONSE"
    exit 1
fi