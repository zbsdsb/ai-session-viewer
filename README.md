# AI Session Viewer

AI 会话记录查看器 - 支持 Claude Code、Codex 两大 AI CLI 工具的会话历史管理。

## ✨ 功能特性

- 📋 **多平台支持**：一键查看 Claude Code、Codex 的所有会话
- 🎯 **智能过滤**：自动排除系统注入消息，只显示真实的用户对话
- 🔍 **智能显示**：查看单个工具时自动显示更多会话（20个），查看所有工具时显示5个
- 💬 **会话标题**：使用用户第一句话作为会话标题，快速识别对话内容
- 📊 **详细信息**：显示项目路径、时间、消息数、文件大小、使用模型等
- 🔄 **快速恢复**：直接提供可复制的恢复命令
- 🤖 **交互模式**：可选择会话查看完整对话历史
- 📤 **多格式输出**：支持文本、JSON、摘要三种输出格式
- 🧭 **全局搜索**：支持用户+助手消息的关键词检索
- 🗂️ **项目/时间筛选**：按项目路径与开始时间筛选会话
- 🧠 **LLM总结**（可选）：使用 AI 生成智能会话摘要

## 📦 安装

```bash
# 克隆或下载项目
cd /path/to/ai-session-viewer

# 添加执行权限
chmod +x aisv

# （可选）创建软链接到系统路径
ln -s $(pwd)/aisv /usr/local/bin/aisv
```

## 🚀 快速开始

### 基本使用

```bash
# 查看所有工具的会话（默认每个显示5个）
aisv

# 只显示摘要统计
aisv --summary

# 查看详细信息（包括文件路径）
aisv -d
```

### 单个工具查看

```bash
# 只查看 Claude Code 的会话（默认显示20个）
aisv -t claude

# 只查看 Codex 的会话
aisv -t codex
```

### 自定义显示数量

```bash
# 查看最近10个会话
aisv -l 10

# 查看 Claude 的 50 个会话
aisv -t claude -l 50

# 查看所有工具，每个显示15个
aisv -t all -l 15
```

### 交互模式

```bash
# 进入交互模式，可选择会话查看详情
aisv -i

# 单个工具 + 交互模式
aisv -t claude -i
```

在交互模式中：
- 输入会话序号查看详细对话记录
- 输入 `q` 退出交互模式

## 📋 输出格式示例

### 默认文本输出

```
============================================================
🔍 AI 会话记录总结
============================================================

📦 Claude Code: 20 个会话, 3136 条消息
   └─ 最近会话: 2026-01-14 07:12

📦 Codex: 0 个会话, 0 条消息

📊 总计: 20 个会话, 3136 条消息
============================================================

────────────────────────────────────────────────────────────
🛠️  Claude Code 会话列表
────────────────────────────────────────────────────────────

📌 [1] 帮我开发一个工具，要求可以获取codex，claude code，gemini的会话记录...
   ⏰ 2026-01-14 07:12 | 💬 160 条消息 | 📊 2.5 MB
   📁 Users/zbs/projectwork/ai/sessions
   🤖 claude-opus-4-5-20251101
   🔄 claude -r ea2398ad-b755-45fe-b568-bbf663b1a120

📌 [2] CVE-2024-38816这个漏洞需要升级Spring Framework版本...
   ⏰ 2026-01-13 08:16 | 💬 120 条消息 | 📊 1.4 MB
   📁 Users/zbs/projectwork/ghkyy/code/em/business/parent
   🤖 claude-opus-4-5-20251101
   🔄 claude -r 8cb11b5c-2f1b-4dda-9b7e-01bb3dedc669
```

### JSON 输出

```bash
# 输出为 JSON 格式
aisv --json

# 保存到文件
aisv --json > sessions.json

# 只保存 Claude 的会话
aisv -t claude --json > claude_sessions.json
```

JSON 格式包含的字段：
- `session_id`：会话唯一标识
- `project_path`：项目路径
- `start_time`：开始时间（ISO 8601格式）
- `last_time`：最后活动时间
- `message_count`：消息数量
- `first_message`：第一条用户消息
- `file_path`：会话文件路径
- `file_size`：文件大小（字节）
- `model`：使用的模型
- `resume_command`：恢复命令

### 全局搜索与筛选

```bash
# 搜索关键词（匹配用户+助手消息）
aisv --search "框架升级"

# 按项目路径筛选
aisv --project "/Users/zbs/projectwork"

# 按开始时间筛选
aisv --since 2026-01-01
aisv --since 2026-01-01 --until 2026-01-14
```

提示：`--until` 仅填日期时按当天 23:59:59 处理。

### 索引数据库（Mac 应用）

```bash
# 构建索引数据库（默认路径）
aisv --build-index

# 指定索引数据库路径
aisv --build-index --db-path "/Users/zbs/projectwork/ai-session-viewer/index.db"

# 使用索引数据库进行查询
aisv --use-index --search "框架升级"
```

默认索引路径：`~/.cache/ai-session-viewer/index.db`

## 🍎 Mac 应用（SwiftUI）

说明：Mac 端应用通过读取索引数据库进行快速检索。

```bash
# 进入 Mac 应用目录
cd "mac-app"

# 构建并运行
swift build
swift run AISessionViewer
```

也可以用 Xcode 打开 `mac-app` 目录进行调试运行。

### 摘要模式

```bash
# 只显示统计摘要
aisv --summary
```

输出示例：
```
============================================================
🔍 AI 会话记录总结
============================================================

📦 Claude Code: 5 个会话, 371 条消息
   └─ 最近会话: 2026-01-14 07:13

📦 Codex: 0 个会话, 0 条消息

📊 总计: 5 个会话, 371 条消息
============================================================
```

## 🤖 LLM 智能总结（可选功能）

支持使用大模型生成会话摘要，需要配置相应的 API Key。

### OpenAI

```bash
# 设置环境变量
export OPENAI_API_KEY="your-api-key"

# 使用 OpenAI 生成总结
aisv --ai-summary

# 指定模型
aisv --ai-summary --model gpt-4o

# 使用自定义 API 地址（兼容 OpenAI 接口）
aisv --ai-summary --base-url https://api.example.com/v1
```

### Anthropic Claude

```bash
# 设置环境变量
export ANTHROPIC_API_KEY="your-api-key"

# 使用 Claude 生成总结
aisv --ai-summary --provider anthropic

# 指定模型
aisv --ai-summary --provider anthropic --model claude-3-5-sonnet-20241022
```

### Google Gemini

```bash
# 设置环境变量
export GOOGLE_API_KEY="your-api-key"

# 使用 Gemini 生成总结
aisv --ai-summary --provider google

# 指定模型
aisv --ai-summary --provider google --model gemini-pro
```

## 🔄 恢复会话

工具会为每个会话生成恢复命令，可以直接复制使用：

### Claude Code

```bash
# 恢复指定会话
claude -r ea2398ad-b755-45fe-b568-bbf663b1a120

# 恢复最近会话
claude --resume
```

### Codex

```bash
# 恢复指定会话
codex --resume d6c58c50-92c0-4d7c-8d43-6d8f78608287

# 恢复最近会话
codex --resume
```

## 📊 常见使用场景

### 场景1：快速查看今天的工作记录

```bash
# 查看 Claude 的所有会话，找到今天的对话
aisv -t claude

# 或使用交互模式查看详情
aisv -t claude -i
```

### 场景2：查找特定项目的会话

```bash
# 查看所有会话，然后搜索项目路径
aisv -l 50 | grep "your-project-name"

# 或使用 JSON 格式进行过滤
aisv --json | jq '.["Claude Code"][] | select(.project_path | contains("your-project"))'
```

### 场景3：导出会话数据用于分析

```bash
# 导出所有会话为 JSON
aisv -t all -l 100 --json > all_sessions.json

# 只导出 Claude 的会话
aisv -t claude -l 100 --json > claude_sessions.json

# 配合 jq 进行数据分析
aisv --json | jq '[.["Claude Code"][] | {title: .first_message, messages: .message_count, size: .file_size}]'
```

### 场景4：恢复上周的某个重要对话

```bash
# 查看最近30个会话
aisv -t claude -l 30

# 在列表中找到对应会话，复制恢复命令
claude -r <session_id>
```

### 场景5：统计工作量

```bash
# 查看本周的所有会话统计
aisv --summary

# 查看详细的消息数和文件大小
aisv -t claude -l 20
```

## 🛠️ 高级用法

### 组合参数

```bash
# Claude + 详细信息 + 交互模式
aisv -t claude -d -i

# 所有工具 + 自定义数量 + JSON输出
aisv -t all -l 10 --json

# 单个工具 + 摘要
aisv -t claude --summary
```

### 与其他工具集成

```bash
# 统计会话数量
aisv --summary | grep "总计"

# 提取所有恢复命令
aisv -t claude -l 100 | grep "🔄" | awk '{print $2, $3}'

# 查找包含特定关键词的会话
aisv --json | jq '.["Claude Code"][] | select(.first_message | contains("bug fix"))'
```

## 📂 会话存储位置

工具从以下位置读取会话数据：

- **Claude Code**: `~/.claude/projects/<project>/*.jsonl`
- **Codex**: `~/.codex/sessions/<year>/<month>/<day>/*.jsonl`

## ⚙️ 配置选项

### 环境变量

```bash
# LLM API Keys（用于智能总结功能）
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"
```

## 🎯 过滤规则

工具会自动过滤以下类型的系统消息：

- Claude-Mem 观察消息
- 进度检查点
- XML 标签消息
- 系统提醒
- 命令输出
- 分隔线
- 空消息

只保留用户真正输入的对话作为会话标题。

## 📝 完整参数列表

```bash
选项:
  -h, --help            显示帮助信息
  -l LIMIT, --limit LIMIT
                        每个工具显示的会话数量
                        (默认: 查看所有工具时为5，单个工具时为20；有过滤时默认不限制)
  -t {claude,codex,all}, --tool {claude,codex,all}
                        指定查看的工具 (默认: all)
  -d, --detail          显示详细信息（包括文件路径）
  -i, --interactive     交互模式，可选择查看会话详情
  --summary             只显示摘要
  --json                以 JSON 格式输出
  --build-index         构建索引数据库（SQLite + FTS5）
  --use-index           从索引数据库读取会话
  --db-path DB_PATH     索引数据库路径（默认: ~/.cache/ai-session-viewer/index.db）
  --search SEARCH       全局搜索关键词（匹配用户+助手消息）
  --project PROJECT     按项目路径关键词筛选
  --since SINCE         按开始时间筛选（如 2026-01-01）
  --until UNTIL         按开始时间筛选（结束时间，包含）
  --ai-summary          使用 LLM 生成智能会话总结
  --provider {openai,anthropic,google}
                        LLM 提供商 (默认: openai)
  --model MODEL         指定 LLM 模型名称
  --api-key API_KEY     LLM API Key
  --base-url BASE_URL   自定义 API 地址
```

## 🔧 故障排查

### 问题1：找不到会话

**检查会话文件是否存在：**
```bash
# Claude Code
ls ~/.claude/projects/

# Codex
ls ~/.codex/sessions/
```

### 问题2：显示"无会话记录"

可能原因：
1. 该工具确实没有会话历史
2. 所有会话都被过滤掉了（只包含系统消息，无用户输入）

**解决方法：**
```bash
# 检查是否有会话文件
ls -la ~/.claude/projects/*/

# 尝试增加显示数量
aisv -t claude -l 100
```

### 问题3：LLM 总结失败

**检查 API Key 是否设置：**
```bash
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
echo $GOOGLE_API_KEY
```

**手动指定 API Key：**
```bash
aisv --ai-summary --api-key "your-api-key"
```

## 📄 许可证

本工具为个人开发项目，供学习和使用。

## 🤝 贡献

欢迎提出建议和改进意见！

---

**开发日期**: 2026-01-14
**版本**: 1.0.0
