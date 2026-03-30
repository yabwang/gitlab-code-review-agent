package com.github.review.agent.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * GitHub 配置
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "github")
public class GithubConfig {

    private String token;

    private String webhookSecret;
}