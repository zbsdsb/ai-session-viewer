# AI Session Viewer - 使用指南

## 🎉 修复完成总结

本次修复已经完成了前端和后端的核心问题，现在可以正常使用了！

---

## ✅ 已修复的问题

### 前端（Mac App）
- ✅ **时间格式**: `2026-01-15 01:26` （而非 `2026-01-15T01:26:23.217000`）
- ✅ **文本显示**: "Claude Code" 完整显示（不再截断为 "Clau de Co de"）
- ✅ **UI 优化**: 添加了图标、tooltip、项目路径显示

### 后端（Python CLI）
- ✅ **系统标签过滤**: 不再显示 `<local-command-stdout>` 等系统消息作为标题
- ✅ **时间统一**: 本地时区显示，用户友好
- ✅ **代码优化**: 更清晰的结构和辅助函数

---

## 🚀 快速开始

### 使用 Python CLI

```bash
# 查看所有工具的最近 5 个会话
./aisv

# 只查看 Claude Code 的最近 20 个会话
./aisv -t claude -l 20

# 只查看 Codex 的会话
./aisv -t codex -l 20

# 搜索包含关键词的会话
./aisv --search "修复"

# 按项目路径筛选
./aisv --project "ai-sessions"

# 按时间筛选
./aisv --since 2026-01-14 --until 2026-01-15
```

### 使用 Mac App

```bash
# 编译 Mac App
cd mac-app
swift build

# 运行 Mac App
swift run
```

**注意**: Mac App 需要先构建索引数据库：
```bash
# 在项目根目录运行
./aisv --build-index
```

---

## 📊 测试验证

### 前端测试结果
```
Build complete! (1.22s)
✅ 编译成功
✅ 时间格式正确
✅ 文本显示完整
```

### 后端测试结果
```bash
$ ./aisv -t claude -l 10
```

输出示例：
```
📌 [1] 帮我调整一下这个项目，总结一下问题...
   ⏰ 2026-01-15 06:37 | 💬 55 条消息 | 📊 1.6 MB
   📁 Users/zbs/projectwork/ai/sessions
   🤖 claude-sonnet-4-5-thinking
   🔄 claude -r 15d1ef03-2c80-4e2d-af93-75940ae5479f
```

✅ 系统标签已被过滤
✅ 时间格式正确
✅ 标题清晰易读

---

## 🔧 可选的进一步优化

### 1. 应用完整的 Codex Patch（索引优化）

Codex 已经生成了完整的优化方案，包括：
- 纳秒级 mtime 检测
- 索引状态显示
- CodexSessionParser 优化

**恢复 Codex 会话继续优化**:
```bash
codex resume 019bbf72-1fe1-7462-bbd2-77592ee53f40 - <<'EOF'
请直接应用你之前提供的索引优化部分的 patch，
包括：
1. 纳秒级 mtime: int(file_stat.st_mtime_ns)
2. get_status() 方法
3. CodexSessionParser 的短标题回退逻辑
EOF
```

### 2. 运行单元测试

```bash
# 安装测试依赖（如果需要）
python3 -m pip install pytest

# 运行测试
python3 -m unittest tests.test_filters tests.test_indexer
```

### 3. 完善短标题处理

对于 "nh"、"dsa" 这样的极短会话，可以：
- 选项 A: 接受现状（这些确实是用户的真实输入）
- 选项 B: 在过滤规则中添加最小长度要求（如 3 个有效字符）

---

## 📝 修复详情

### 修改的文件

**前端（Mac App）**:
- `mac-app/Sources/AISessionViewer/Models.swift`
- `mac-app/Sources/AISessionViewer/Views/SessionRowView.swift`

**后端（Python）**:
- `session_viewer.py`
  - 添加了 `unicodedata` import
  - 添加了辅助函数（is_short_title, is_separator_line 等）
  - 优化了 ClaudeSessionParser
  - 改进了时间处理

### 生成的文档

- `ISSUES.md` - 问题详细分析
- `FIXES_SUMMARY.md` - 初步修复总结
- `FINAL_REPORT.md` - 详细修复报告
- `USAGE.md` - 本使用指南

---

## 💡 最佳实践

### 1. 定期更新索引（如果使用 Mac App）

```bash
# 每周或当你有新会话时运行
./aisv --build-index
```

### 2. 使用搜索功能

```bash
# 查找特定主题的会话
./aisv --search "修复 bug"

# 查找特定项目的会话
./aisv --project "ghkyy"
```

### 3. 交互模式浏览详情

```bash
# 进入交互模式，可以查看完整对话
./aisv -i
```

---

## 🐛 已知的小问题

### 1. 极短标题
- **现象**: 个别会话显示为 "nh"、"dsa" 等极短标题
- **原因**: 这些是用户的真实输入，且该会话只有一条消息
- **影响**: 低，不影响功能使用
- **解决**: 可选择性接受或在未来版本进一步优化

### 2. Mac App 依赖索引数据库
- **现象**: Mac App 需要先运行 `./aisv --build-index`
- **原因**: Mac App 读取 SQLite 索引而非直接解析 JSONL
- **解决**: 文档已更新，提示用户先构建索引

---

## 🎯 下一步建议

### 立即可做
- [x] 前端已完成修复
- [x] 后端核心功能已修复
- [x] 测试验证通过

### 可选优化（按需进行）
- [ ] 应用 Codex 的完整索引优化 patch
- [ ] 更新单元测试文件
- [ ] 考虑添加 Gemini 会话支持（如果需要）

---

## 📞 技术支持

如果遇到问题，可以：

1. 查看 `FINAL_REPORT.md` 了解详细修复过程
2. 查看 `ISSUES.md` 了解问题分析
3. 使用 Codex Session ID 继续优化：`019bbf72-1fe1-7462-bbd2-77592ee53f40`

---

**修复完成时间**: 2026-01-15
**修复者**: Claude Sonnet 4.5 + Codex
**状态**: ✅ 可用 | 🟢 核心功能完整 | 🟡 细节可继续优化
