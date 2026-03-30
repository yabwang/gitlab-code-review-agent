package com.github.review.agent.client;

import com.github.review.agent.config.GithubConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.kohsuke.github.GHIssueComment;
import org.kohsuke.github.GHPullRequest;
import org.kohsuke.github.GHRepository;
import org.kohsuke.github.GitHub;
import org.kohsuke.github.GitHubBuilder;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;
import java.io.IOException;

/**
 * GitHub API 客户端
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class GithubClient {

    private final GithubConfig config;
    private GitHub gitHub;

    @PostConstruct
    public void init() {
        if (config.getToken() != null && !config.getToken().isEmpty()) {
            try {
                gitHub = new GitHubBuilder().withOAuthToken(config.getToken()).build();
                log.info("GitHub client initialized");
            } catch (Exception e) {
                log.error("GitHub client initialization failed", e);
            }
        }
    }

    /**
     * 获取仓库
     */
    public GHRepository getRepository(String owner, String repo) {
        try {
            return gitHub.getRepository(owner + "/" + repo);
        } catch (IOException e) {
            log.error("获取仓库失败: {}/{}", owner, repo, e);
            throw new RuntimeException("获取仓库失败: " + e.getMessage());
        }
    }

    /**
     * 获取 PR
     */
    public GHPullRequest getPullRequest(String owner, String repo, int prNumber) {
        try {
            GHRepository repository = getRepository(owner, repo);
            return repository.getPullRequest(prNumber);
        } catch (IOException e) {
            log.error("获取 PR 失败: {}/{} #{}", owner, repo, prNumber, e);
            throw new RuntimeException("获取 PR 失败: " + e.getMessage());
        }
    }

    /**
     * 发布评论
     */
    public GHIssueComment addComment(String owner, String repo, int prNumber, String body) {
        try {
            GHRepository repository = getRepository(owner, repo);
            return repository.getPullRequest(prNumber).comment(body);
        } catch (IOException e) {
            log.error("发布评论失败: {}/{} #{}", owner, repo, prNumber, e);
            throw new RuntimeException("发布评论失败: " + e.getMessage());
        }
    }
}