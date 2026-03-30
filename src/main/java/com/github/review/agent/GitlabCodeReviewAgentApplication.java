package com.github.review.agent;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * GitLab/GitHub AI Code Review Agent
 *
 * 智能代码审查服务，支持 GitLab MR 和 GitHub PR 的自动审查
 */
@SpringBootApplication
@EnableAsync
public class GitlabCodeReviewAgentApplication {

    public static void main(String[] args) {
        SpringApplication.run(GitlabCodeReviewAgentApplication.class, args);
    }
}