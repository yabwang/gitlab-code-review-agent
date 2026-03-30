package com.github.review.agent.client;

import com.github.review.agent.config.GitlabConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.gitlab4j.api.GitLabApi;
import org.gitlab4j.api.GitLabApiException;
import org.gitlab4j.api.models.MergeRequest;
import org.gitlab4j.api.models.MergeRequestComment;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;

/**
 * GitLab API 客户端
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class GitlabClient {

    private final GitlabConfig config;
    private GitLabApi gitLabApi;

    @PostConstruct
    public void init() {
        if (config.getToken() != null && !config.getToken().isEmpty()) {
            gitLabApi = new GitLabApi(config.getUrl(), config.getToken());
            log.info("GitLab client initialized: {}", config.getUrl());
        }
    }

    /**
     * 获取 MR 信息
     */
    public MergeRequest getMergeRequest(Long projectId, Long mrIid) {
        try {
            return gitLabApi.getMergeRequestApi().getMergeRequest(projectId, mrIid);
        } catch (GitLabApiException e) {
            log.error("获取 MR 失败: project={}, mr={}", projectId, mrIid, e);
            throw new RuntimeException("获取 MR 失败: " + e.getMessage());
        }
    }

    /**
     * 获取 MR 变更
     */
    public MergeRequest getMergeRequestChanges(Long projectId, Long mrIid) {
        try {
            return gitLabApi.getMergeRequestApi().getMergeRequestChanges(projectId, mrIid);
        } catch (GitLabApiException e) {
            log.error("获取 MR 变更失败: project={}, mr={}", projectId, mrIid, e);
            throw new RuntimeException("获取 MR 变更失败: " + e.getMessage());
        }
    }

    /**
     * 发布评论
     */
    public MergeRequestComment addComment(Long projectId, Long mrIid, String body) {
        try {
            return gitLabApi.getNotesApi().createMergeRequestNote(projectId, mrIid, body);
        } catch (GitLabApiException e) {
            log.error("发布评论失败: project={}, mr={}", projectId, mrIid, e);
            throw new RuntimeException("发布评论失败: " + e.getMessage());
        }
    }

    /**
     * 验证 Token
     */
    public boolean validateToken(String token) {
        if (config.getWebhookSecret() == null || config.getWebhookSecret().isEmpty()) {
            return true;
        }
        return config.getWebhookSecret().equals(token);
    }
}