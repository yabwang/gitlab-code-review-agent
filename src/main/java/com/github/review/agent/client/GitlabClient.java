package com.github.review.agent.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.review.agent.config.GitlabConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import jakarta.annotation.PostConstruct;

/**
 * GitLab API 客户端
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class GitlabClient {

    private final GitlabConfig config;
    private final ObjectMapper objectMapper;
    private RestTemplate restTemplate;
    private HttpHeaders headers;

    @PostConstruct
    public void init() {
        if (config.getToken() != null && !config.getToken().isEmpty()) {
            restTemplate = new RestTemplate();
            headers = new HttpHeaders();
            headers.set("PRIVATE-TOKEN", config.getToken());
            log.info("GitLab client initialized: {}", config.getUrl());
        }
    }

    /**
     * 获取 MR 信息
     */
    public JsonNode getMergeRequest(Long projectId, Long mrIid) {
        String url = config.getUrl() + "/api/v4/projects/" + projectId + "/merge_requests/" + mrIid;
        try {
            HttpEntity<String> entity = new HttpEntity<>(headers);
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.GET, entity, String.class);
            return objectMapper.readTree(response.getBody());
        } catch (Exception e) {
            log.error("获取 MR 失败: project={}, mr={}", projectId, mrIid, e);
            throw new RuntimeException("获取 MR 失败: " + e.getMessage());
        }
    }

    /**
     * 获取 MR 变更
     */
    public JsonNode getMergeRequestChanges(Long projectId, Long mrIid) {
        String url = config.getUrl() + "/api/v4/projects/" + projectId + "/merge_requests/" + mrIid + "/changes";
        try {
            HttpEntity<String> entity = new HttpEntity<>(headers);
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.GET, entity, String.class);
            return objectMapper.readTree(response.getBody());
        } catch (Exception e) {
            log.error("获取 MR 变更失败: project={}, mr={}", projectId, mrIid, e);
            throw new RuntimeException("获取 MR 变更失败: " + e.getMessage());
        }
    }

    /**
     * 发布评论
     */
    public void addComment(Long projectId, Long mrIid, String body) {
        String url = config.getUrl() + "/api/v4/projects/" + projectId + "/merge_requests/" + mrIid + "/notes";
        try {
            HttpHeaders postHeaders = new HttpHeaders();
            postHeaders.set("PRIVATE-TOKEN", config.getToken());
            postHeaders.set("Content-Type", "application/json");

            String jsonBody = "{\"body\":\"" + body.replace("\"", "\\\"").replace("\n", "\\n") + "\"}";
            HttpEntity<String> entity = new HttpEntity<>(jsonBody, postHeaders);
            restTemplate.postForEntity(url, entity, String.class);
            log.info("评论已发布: project={}, mr={}", projectId, mrIid);
        } catch (Exception e) {
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