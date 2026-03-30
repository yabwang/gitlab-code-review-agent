package com.github.review.agent.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * 审查配置
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "review")
public class ReviewConfig {

    private int maxDiffSize = 50000;

    private int timeout = 120;
}