package com.github.review.agent.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * GitLab 配置
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "gitlab")
public class GitlabConfig {

    private String url;

    private String token;

    private String webhookSecret;
}