package com.github.review.agent.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 代码审查结果
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReviewResult {

    private String platform;

    private String status;

    private List<ReviewComment> comments;

    private String summary;

    /**
     * 审查评论
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ReviewComment {

        private String file;

        private Integer line;

        private String comment;

        private String type;
    }
}