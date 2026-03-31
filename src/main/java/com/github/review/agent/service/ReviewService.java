package com.github.review.agent.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.review.agent.client.GitlabClient;
import com.github.review.agent.client.GithubClient;
import com.github.review.agent.client.LlmClient;
import com.github.review.agent.config.ReviewConfig;
import com.github.review.agent.model.ReviewResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.kohsuke.github.GHPullRequest;
import org.kohsuke.github.GHPullRequestFileDetail;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * 代码审查服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ReviewService {

    private final GitlabClient gitlabClient;
    private final GithubClient githubClient;
    private final LlmClient llmClient;
    private final ReviewConfig reviewConfig;
    private final ObjectMapper objectMapper;

    /**
     * 审查 GitLab MR
     */
    @Async
    public void reviewGitlabMr(Long projectId, Long mrIid) {
        log.info("开始审查 GitLab MR: project={}, mr={}", projectId, mrIid);

        try {
            JsonNode mr = gitlabClient.getMergeRequestChanges(projectId, mrIid);
            String title = mr.path("title").asText();
            String description = mr.path("description").asText("");

            List<ReviewResult.ReviewComment> comments = new ArrayList<>();

            // 审查文件变更
            JsonNode changes = mr.path("changes");
            if (changes.isArray()) {
                for (JsonNode change : changes) {
                    String filename = change.path("new_path").asText();
                    String diff = change.path("diff").asText();

                    if (diff != null && !diff.isEmpty() && !shouldSkipFile(filename)) {
                        // 审查代码质量
                        String qualityResult = llmClient.reviewQuality(filename, diff);
                        if (!"无问题".equals(qualityResult) && !"无问题。".equals(qualityResult)) {
                            comments.add(ReviewResult.ReviewComment.builder()
                                    .file(filename)
                                    .comment(qualityResult)
                                    .type("quality")
                                    .build());
                        }

                        // 安全扫描
                        String securityResult = llmClient.scanSecurity(filename, diff);
                        if (!"无安全风险".equals(securityResult) && !"无安全风险。".equals(securityResult)) {
                            comments.add(ReviewResult.ReviewComment.builder()
                                    .file(filename)
                                    .comment(securityResult)
                                    .type("security")
                                    .build());
                        }
                    }
                }
            }

            // 生成审查报告
            String summary = llmClient.generateSummary(title, description, comments.size());

            // 发布评论
            String report = formatReport(summary, comments);
            gitlabClient.addComment(projectId, mrIid, report);

            log.info("GitLab MR 审查完成: project={}, mr={}", projectId, mrIid);

        } catch (Exception e) {
            log.error("GitLab MR 审查失败", e);
        }
    }

    /**
     * 审查 GitHub PR
     */
    @Async
    public void reviewGithubPr(String owner, String repo, int prNumber) {
        log.info("开始审查 GitHub PR: {}/{} #{}", owner, repo, prNumber);

        try {
            GHPullRequest pr = githubClient.getPullRequest(owner, repo, prNumber);
            String title = pr.getTitle();
            String body = pr.getBody();

            List<ReviewResult.ReviewComment> comments = new ArrayList<>();

            // 审查文件变更
            for (GHPullRequestFileDetail file : pr.listFiles()) {
                String filename = file.getFilename();
                String patch = file.getPatch();

                if (patch != null && !shouldSkipFile(filename)) {
                    // 审查代码质量
                    String qualityResult = llmClient.reviewQuality(filename, patch);
                    if (!"无问题".equals(qualityResult) && !"无问题。".equals(qualityResult)) {
                        comments.add(ReviewResult.ReviewComment.builder()
                                .file(filename)
                                .comment(qualityResult)
                                .type("quality")
                                .build());
                    }

                    // 安全扫描
                    String securityResult = llmClient.scanSecurity(filename, patch);
                    if (!"无安全风险".equals(securityResult) && !"无安全风险。".equals(securityResult)) {
                        comments.add(ReviewResult.ReviewComment.builder()
                                .file(filename)
                                .comment(securityResult)
                                .type("security")
                                .build());
                    }
                }
            }

            // 生成审查报告
            String summary = llmClient.generateSummary(title, body, comments.size());

            // 发布评论
            String report = formatReport(summary, comments);
            githubClient.addComment(owner, repo, prNumber, report);

            log.info("GitHub PR 审查完成: {}/{}, #{}", owner, repo, prNumber);

        } catch (Exception e) {
            log.error("GitHub PR 审查失败", e);
        }
    }

    /**
     * 格式化审查报告
     */
    private String formatReport(String summary, List<ReviewResult.ReviewComment> comments) {
        StringBuilder sb = new StringBuilder();
        sb.append("## 🤖 AI 代码审查报告\n\n");
        sb.append("---\n\n");
        sb.append(summary).append("\n\n");

        if (!comments.isEmpty()) {
            sb.append("### 📝 发现的问题\n\n");
            for (ReviewResult.ReviewComment comment : comments) {
                sb.append("**").append(comment.getFile()).append("**\n");
                sb.append("- ").append(comment.getComment()).append("\n\n");
            }
        }

        sb.append("---\n\n");
        sb.append("> 💡 此报告由 AI 自动生成，建议结合人工审查确认。\n");
        return sb.toString();
    }

    /**
     * 判断是否跳过文件
     */
    private boolean shouldSkipFile(String filename) {
        String[] skipExtensions = {".md", ".txt", ".json", ".yaml", ".yml", ".lock", ".xml", ".properties"};
        for (String ext : skipExtensions) {
            if (filename.endsWith(ext)) {
                return true;
            }
        }
        return false;
    }
}