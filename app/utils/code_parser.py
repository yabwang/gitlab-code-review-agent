import re


def parse_diff(diff_text: str) -> list:
    """解析 git diff 输出，提取变更块"""
    changes = []

    # 匹配 diff 块
    hunks = re.findall(
        r'@@ -\d+,?\d* \+(\d+),?\d* @@.*?\n([\s\S]*?)(?=@@|$)',
        diff_text
    )

    for line_num, content in hunks:
        # 只保留新增或修改的行
        new_lines = []
        current_line = int(line_num)

        for line in content.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                new_lines.append({
                    "type": "added",
                    "line": current_line,
                    "content": line[1:].strip()
                })
                current_line += 1
            elif line.startswith(' ') and not line.startswith('   '):
                current_line += 1
            elif line.startswith('-') and not line.startswith('---'):
                new_lines.append({
                    "type": "deleted",
                    "line": current_line,
                    "content": line[1:].strip()
                })

        # 合并连续的变更块
        if new_lines:
            changes.append({
                "new_line": new_lines[0]["line"] if new_lines else None,
                "content": '\n'.join([
                    l["content"] for l in new_lines if l["type"] == "added"
                ]),
                "type": "modified"
            })

    return changes


def extract_file_changes(diff_text: str) -> dict:
    """提取文件级别的变更统计"""
    additions = len(re.findall(r'^\+', diff_text, re.MULTILINE)) - \
                len(re.findall(r'^\+\+\+', diff_text, re.MULTILINE))
    deletions = len(re.findall(r'^-', diff_text, re.MULTILINE)) - \
                len(re.findall(r'^---', diff_text, re.MULTILINE))

    return {
        "additions": additions,
        "deletions": deletions,
        "changed_files": len(re.findall(r'^diff --git', diff_text, re.MULTILINE))
    }