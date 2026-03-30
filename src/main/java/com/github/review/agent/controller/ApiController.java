package com.github.review.agent.controller;

import com.github.review.agent.config.LlmConfig;
import com.github.review.agent.model.ApiResponse;
import com.github.review.agent.service.ReviewService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * REST API 控制器
 */
@RestController
@RequiredArgsConstructor
public class ApiController {

    private final ReviewService reviewService;
    private final LlmConfig llmConfig;

    /**
     * 服务信息
     */
    @GetMapping("/")
    public ResponseEntity<ApiResponse<Map<String, Object>>> root() {
        Map<String, Object> info = new HashMap<>();
        info.put("name", "GitLab/GitHub AI Code Review Agent");
        info.put("version", "2.0.0-java");
        info.put("description", "智能代码审查服务，Java 版本");

        Map<String, String> endpoints = new HashMap<>();
        endpoints.put("gitlab_webhook", "/webhook/gitlab");
        endpoints.put("github_webhook", "/webhook/github");
        endpoints.put("gitlab_review", "/review/gitlab/{projectId}/{mrIid}");
        endpoints.put("github_review", "/review/github/{owner}/{repo}/{prNumber}");
        endpoints.put("health", "/health");
        info.put("endpoints", endpoints);

        return ResponseEntity.ok(ApiResponse.success(info));
    }

    /**
     * 健康检查
     */
    @GetMapping("/health")
    public ResponseEntity<ApiResponse<Map<String, Object>>> health() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "healthy");
        health.put("llm_provider", llmConfig.getProvider());
        health.put("llm_model", llmConfig.getModel());
        return ResponseEntity.ok(ApiResponse.success(health));
    }

    /**
     * 手动触发 GitLab MR 审查
     */
    @PostMapping("/review/gitlab/{projectId}/{mrIid}")
    public ResponseEntity<ApiResponse<?>> reviewGitlab(
            @PathVariable Long projectId,
            @PathVariable Long mrIid) {

        reviewService.reviewGitlabMr(projectId, mrIid);
        return ResponseEntity.ok(ApiResponse.accepted("审查任务已启动: MR #" + mrIid));
    }

    /**
     * 手动触发 GitHub PR 审查
     */
    @PostMapping("/review/github/{owner}/{repo}/{prNumber}")
    public ResponseEntity<ApiResponse<?>> reviewGithub(
            @PathVariable String owner,
            @PathVariable String repo,
            @PathVariable int prNumber) {

        reviewService.reviewGithubPr(owner, repo, prNumber);
        return ResponseEntity.ok(ApiResponse.accepted("审查任务已启动: PR #" + prNumber));
    }
}