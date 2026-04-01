package com.github.review.agent;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * Multi Platform Agent
 *
 * AI-powered multi-platform agent for code review and more
 */
@SpringBootApplication
@EnableAsync
public class MultiPlatformAgentApplication {

    public static void main(String[] args) {
        SpringApplication.run(MultiPlatformAgentApplication.class, args);
    }
}