package com.github.review.agent.client;

import dev.langchain4j.model.chat.ChatLanguageModel;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * LLM 客户端
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class LlmClient {

    private final ChatLanguageModel chatModel;

    private static final String CODE_QUALITY_PROMPT = """
            你是一个专业的代码审查助手。审查 %s 文件的代码变更。

            请从以下角度审查：
            1. 代码可读性（命名、注释、结构）
            2. 代码逻辑（是否有 bug 或边界情况遗漏）
            3. 代码复杂度（是否有过度复杂的设计）
            4. 重复代码（是否需要提取公共方法）
            5. 最佳实践（是否符合语言/框架最佳实践）

            如果发现问题，用简练的中文指出具体问题和改进建议。
            如果没有明显问题，回复"无问题"。
            """;

    private static final String SECURITY_PROMPT = """
            你是一个安全代码审查专家。检查 %s 文件的代码变更是否存在安全漏洞。

            重点检查：
            1. SQL 注入风险
            2. XSS 跨站脚本攻击
            3. 命令注入
            4. 路径遍历
            5. 敏感信息泄露（密钥、密码、token）
            6. 权限验证缺失

            如果发现安全风险，明确指出风险类型和修复建议。
            如果没有安全风险，回复"无安全风险"。
            """;

    private static final String SUMMARY_PROMPT = """
            你是一个代码变更总结助手。请根据以下 MR 信息生成一份变更总结报告。

            总结要求：
            1. 用简洁的语言描述本次变更的目的和内容
            2. 列出主要变更点
            3. 提示审查者需要注意的重点

            用中文输出，格式清晰。
            """;

    /**
     * 审查代码质量
     */
    public String reviewQuality(String filePath, String code) {
        String prompt = String.format(CODE_QUALITY_PROMPT, filePath);
        String message = "审查代码:\n```\n" + code + "\n```";
        return chat(prompt, message);
    }

    /**
     * 安全扫描
     */
    public String scanSecurity(String filePath, String code) {
        String prompt = String.format(SECURITY_PROMPT, filePath);
        String message = "检查安全漏洞:\n```\n" + code + "\n```";
        return chat(prompt, message);
    }

    /**
     * 生成总结
     */
    public String generateSummary(String title, String description, int changeCount) {
        String message = String.format("""
                MR 标题: %s
                描述: %s
                变更文件数: %d
                """, title, description, changeCount);
        return chat(SUMMARY_PROMPT, message);
    }

    /**
     * 调用 LLM
     */
    public String chat(String systemPrompt, String userMessage) {
        String fullPrompt = systemPrompt + "\n\n" + userMessage;
        try {
            return chatModel.generate(fullPrompt);
        } catch (Exception e) {
            log.error("LLM 调用失败", e);
            return "LLM 调用失败: " + e.getMessage();
        }
    }
}