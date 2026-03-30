package com.github.review.agent.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.review.agent.client.GitlabClient;
import com.github.review.agent.client.GithubClient;
import com.github.review.agent.config.GithubConfig;
import com.github.review.agent.config.GitlabConfig;
import com.github.review.agent.model.ApiResponse;
import com.github.review.agent.service.ReviewService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;

/**
 * Webhook 控制器
 */
@Slf4j
@RestController
@RequiredArgsConstructor
public class WebhookController {

    private final ReviewService reviewService;
    private final GitlabClient gitlabClient;
    private final GitlabConfig gitlabConfig;
    private final GithubConfig githubConfig;
    private final ObjectMapper objectMapper;

    /**
     * GitLab Webhook
     */
    @PostMapping("/webhook/gitlab")
    public ResponseEntity<ApiResponse<?>> handleGitlabWebhook(
            @RequestHeader(value = "X-Gitlab-Token", required = false) String token,
            @RequestBody JsonNode payload) {

        // 验证 Token
        if (!gitlabClient.validateToken(token)) {
            log.warn("GitLab webhook token 验证失败");
            return ResponseEntity.status(401).body(ApiResponse.error("Invalid token"));
        }

        String objectKind = payload.path("object_kind").asText();
        if (!"merge_request".equals(objectKind)) {
            return ResponseEntity.ok(ApiResponse.accepted("Skipped: not merge request"));
        }

        JsonNode attrs = payload.path("object_attributes");
        String action = attrs.path("action").asText();

        if (!"open".equals(action) && !"reopen".equals(action) && !"update".equals(action)) {
            return ResponseEntity.ok(ApiResponse.accepted("Skipped: action " + action));
        }

        Long projectId = payload.path("project").path("id").asLong();
        Long mrIid = attrs.path("iid").asLong();
        String title = attrs.path("title").asText();

        log.info("收到 GitLab MR #{} ({}): {}", mrIid, action, title);

        reviewService.reviewGitlabMr(projectId, mrIid);

        return ResponseEntity.ok(ApiResponse.accepted("审查任务已启动: MR #" + mrIid));
    }

    /**
     * GitHub Webhook
     */
    @PostMapping("/webhook/github")
    public ResponseEntity<ApiResponse<?>> handleGithubWebhook(
            @RequestHeader(value = "X-Hub-Signature-256", required = false) String signature,
            @RequestHeader("X-GitHub-Event") String eventType,
            @RequestBody String payload) {

        // 验证签名
        if (githubConfig.getWebhookSecret() != null && !githubConfig.getWebhookSecret().isEmpty()) {
            if (!verifyGithubSignature(payload, signature)) {
                log.warn("GitHub webhook 签名验证失败");
                return ResponseEntity.status(401).body(ApiResponse.error("Invalid signature"));
            }
        }

        if (!"pull_request".equals(eventType)) {
            return ResponseEntity.ok(ApiResponse.accepted("Skipped: not pull request"));
        }

        try {
            JsonNode data = objectMapper.readTree(payload);
            String action = data.path("action").asText();

            if (!"opened".equals(action) && !"reopened".equals(action) && !"synchronize".equals(action)) {
                return ResponseEntity.ok(ApiResponse.accepted("Skipped: action " + action));
            }

            JsonNode repo = data.path("repository");
            String owner = repo.path("owner").path("login").asText();
            String repoName = repo.path("name").asText();
            int prNumber = data.path("pull_request").path("number").asInt();
            String title = data.path("pull_request").path("title").asText();

            log.info("收到 GitHub PR #{} ({}): {}/{} - {}", prNumber, action, owner, repoName, title);

            reviewService.reviewGithubPr(owner, repoName, prNumber);

            return ResponseEntity.ok(ApiResponse.accepted("审查任务已启动: PR #" + prNumber));

        } catch (Exception e) {
            log.error("处理 GitHub webhook 失败", e);
            return ResponseEntity.internalServerError().body(ApiResponse.error(e.getMessage()));
        }
    }

    /**
     * 验证 GitHub 签名
     */
    private boolean verifyGithubSignature(String payload, String signature) {
        if (signature == null || !signature.startsWith("sha256=")) {
            return false;
        }

        try {
            String expected = signature.substring(7);
            Mac mac = Mac.getInstance("HmacSHA256");
            SecretKeySpec key = new SecretKeySpec(githubConfig.getWebhookSecret().getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            mac.init(key);
            byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            String actual = bytesToHex(hash);
            return expected.equals(actual);
        } catch (Exception e) {
            log.error("验证签名失败", e);
            return false;
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}