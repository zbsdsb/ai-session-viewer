#!/usr/bin/env python3
"""
AI Session Viewer - 获取 Codex, Claude Code 的会话记录

支持的 AI CLI 工具:
- Claude Code: ~/.claude/projects/<project>/*.jsonl
- Codex: ~/.codex/sessions/<year>/<month>/<day>/*.jsonl

功能:
1. 列出所有会话记录
2. 查看会话详情和摘要
3. 生成恢复对话的命令
4. 使用 LLM 智能总结会话内容
5. 支持搜索与项目/时间过滤
"""

import json
import os
import sys
import hashlib
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import argparse


def ensure_utf8_stdio():
    """Use UTF-8 for Windows console output so emoji/CJK text do not crash."""
    if sys.platform != "win32":
        return

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


# ============================================================
# LLM 总结器配置
# ============================================================

@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "openai"      # openai, anthropic, google
    model: str = ""               # 模型名称，为空则使用默认
    api_key: str = ""             # API Key
    base_url: str = ""            # 自定义 API 地址
    max_tokens: int = 200         # 最大输出 token

    # 各提供商的默认模型
    DEFAULT_MODELS = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "google": "gemini-2.0-flash",
    }

    def get_model(self) -> str:
        """获取模型名称"""
        if self.model:
            return self.model
        return self.DEFAULT_MODELS.get(self.provider, "gpt-4o-mini")

    def get_api_key(self) -> str:
        """获取 API Key（优先使用配置，否则从环境变量读取）"""
        if self.api_key:
            return self.api_key

        env_keys = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        env_key = env_keys.get(self.provider, "OPENAI_API_KEY")
        return os.environ.get(env_key, "")


class LLMSummarizer:
    """LLM 会话总结器"""

    SUMMARY_PROMPT = """请用简洁的中文总结以下 AI 助手会话的主要内容。
要求：
1. 用 1-3 句话概括会话的核心任务或讨论主题
2. 提取关键技术点或操作（如有）
3. 总结字数控制在 100 字以内

用户消息列表：
{messages}

请直接输出总结，不要有任何前缀。"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.cache_dir = Path.home() / ".cache" / "ai-session-viewer"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, messages: list) -> str:
        """生成缓存 key"""
        content = json.dumps(messages, ensure_ascii=False)
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_summary(self, cache_key: str) -> Optional[str]:
        """获取缓存的总结"""
        cache_file = self.cache_dir / f"{cache_key}.txt"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")
        return None

    def _save_cache(self, cache_key: str, summary: str):
        """保存总结到缓存"""
        cache_file = self.cache_dir / f"{cache_key}.txt"
        cache_file.write_text(summary, encoding="utf-8")

    def summarize(self, messages: list) -> str:
        """使用 LLM 总结会话"""
        if not messages:
            return "(无用户消息)"

        # 检查缓存
        cache_key = self._get_cache_key(messages)
        cached = self._get_cached_summary(cache_key)
        if cached:
            return cached

        # 准备消息内容（限制长度）
        msg_text = "\n".join([f"- {m[:200]}" for m in messages[:10]])
        prompt = self.SUMMARY_PROMPT.format(messages=msg_text)

        try:
            summary = self._call_llm(prompt)
            if summary:
                self._save_cache(cache_key, summary)
                return summary
        except Exception as e:
            return f"(LLM 总结失败: {str(e)[:50]})"

        return "(LLM 总结失败)"

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM API"""
        provider = self.config.provider.lower()

        if provider == "openai":
            return self._call_openai(prompt)
        elif provider == "anthropic":
            return self._call_anthropic(prompt)
        elif provider == "google":
            return self._call_google(prompt)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")

    def _call_openai(self, prompt: str) -> str:
        """调用 OpenAI API"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

        api_key = self.config.get_api_key()
        if not api_key:
            raise ValueError("未设置 OPENAI_API_KEY")

        client = OpenAI(
            api_key=api_key,
            base_url=self.config.base_url or None
        )

        response = client.chat.completions.create(
            model=self.config.get_model(),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.config.max_tokens,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    def _call_anthropic(self, prompt: str) -> str:
        """调用 Anthropic API"""
        try:
            import anthropic
        except ImportError:
            raise ImportError("请安装 anthropic: pip install anthropic")

        api_key = self.config.get_api_key()
        if not api_key:
            raise ValueError("未设置 ANTHROPIC_API_KEY")

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=self.config.get_model(),
            max_tokens=self.config.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    def _call_google(self, prompt: str) -> str:
        """调用 Google Gemini API"""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("请安装 google-generativeai: pip install google-generativeai")

        api_key = self.config.get_api_key()
        if not api_key:
            raise ValueError("未设置 GOOGLE_API_KEY")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.config.get_model())

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=self.config.max_tokens,
                temperature=0.3
            )
        )

        return response.text.strip()


# 全局 LLM 总结器实例
_llm_summarizer: Optional[LLMSummarizer] = None


def get_llm_summarizer() -> Optional[LLMSummarizer]:
    """获取全局 LLM 总结器"""
    return _llm_summarizer


def set_llm_summarizer(config: LLMConfig):
    """设置全局 LLM 总结器"""
    global _llm_summarizer
    _llm_summarizer = LLMSummarizer(config)


@dataclass
class SessionInfo:
    """会话信息数据类"""
    tool: str                    # 工具名称: claude, codex
    session_id: str              # 会话 ID
    project_path: str            # 项目路径
    start_time: Optional[datetime] = None  # 开始时间
    last_time: Optional[datetime] = None   # 最后活动时间
    message_count: int = 0       # 消息数量
    first_message: str = ""      # 第一条用户消息（用于摘要）
    file_path: str = ""          # 会话文件路径
    file_size: int = 0           # 文件大小
    model: str = ""              # 使用的模型
    topics: list = field(default_factory=list)  # 主题关键词
    summary: str = ""            # 会话内容总结
    user_messages: list = field(default_factory=list)  # 所有用户消息（用于生成总结）


@dataclass
class SessionFilter:
    """会话过滤条件"""
    search: str = ""                       # 搜索关键词（匹配用户+助手消息）
    project: str = ""                      # 项目路径关键词
    since: Optional[datetime] = None       # 开始时间下限（包含）
    until: Optional[datetime] = None       # 开始时间上限（包含）

    def has_search(self) -> bool:
        return bool(self.search.strip())

    def has_project(self) -> bool:
        return bool(self.project.strip())

    def has_date_range(self) -> bool:
        return self.since is not None or self.until is not None


def build_search_tokens(query: str) -> list[str]:
    """将搜索关键词拆分为 tokens"""
    if not query:
        return []
    return [token.strip().lower() for token in query.split() if token.strip()]


def build_fts_query(query: str) -> str:
    """构建 FTS 查询表达式"""
    tokens = build_search_tokens(query)
    if not tokens:
        return ""
    return " AND ".join(tokens)


def update_search_hits(tokens: list[str], found: set[str], text: str) -> bool:
    """更新命中的搜索 token，命中全部时返回 True"""
    if not tokens or not text:
        return False
    lowered = text.lower()
    for token in tokens:
        if token not in found and token in lowered:
            found.add(token)
    return len(found) == len(tokens)


def _count_significant_chars(text: str) -> int:
    """统计有效字符长度"""
    count = 0
    for ch in text:
        if ch.isspace():
            continue
        category = unicodedata.category(ch)
        if category.startswith(("P", "S")):
            continue
        count += 1
    return count


def is_punctuation_only(text: str) -> bool:
    """判断是否只包含标点或符号"""
    stripped = text.strip()
    if not stripped:
        return False
    return _count_significant_chars(stripped) == 0


def is_separator_line(text: str) -> bool:
    """判断是否为分隔线文本"""
    stripped = text.strip()
    if not stripped:
        return False
    return all(ch in "─=━-_—" for ch in stripped)


def is_short_title(text: str, min_length: int = 3) -> bool:
    """判断标题是否过短"""
    if not text:
        return True
    return _count_significant_chars(text) < min_length


def _get_local_timezone() -> timezone:
    """获取本地时区"""
    return datetime.now().astimezone().tzinfo or timezone.utc


def normalize_datetime(
    value: Optional[datetime],
    assume_local: bool = False
) -> Optional[datetime]:
    """统一时间对比口径为无时区的 UTC"""
    if value is None:
        return None
    if value.tzinfo is None:
        tzinfo = _get_local_timezone() if assume_local else timezone.utc
        value = value.replace(tzinfo=tzinfo)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def format_datetime(
    value: Optional[datetime],
    assume_local: bool = False
) -> Optional[str]:
    """格式化时间为 UTC ISO 字符串"""
    normalized = normalize_datetime(value, assume_local=assume_local)
    if normalized is None:
        return None
    return normalized.isoformat()


def to_local_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """将时间转换为本地时区"""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone()


def format_local_datetime(value: Optional[datetime]) -> str:
    """格式化时间为本地显示字符串"""
    local_value = to_local_datetime(value)
    if local_value is None:
        return "未知"
    return local_value.strftime("%Y-%m-%d %H:%M")


def format_local_iso(value: Optional[datetime]) -> Optional[str]:
    """格式化时间为本地 ISO 字符串"""
    local_value = to_local_datetime(value)
    if local_value is None:
        return None
    return local_value.isoformat()


def parse_datetime_input(value: str, end_of_day: bool = False) -> datetime:
    """解析命令行输入的时间"""
    if not value:
        raise ValueError("时间参数不能为空")
    cleaned = value.strip().replace("T", " ")
    if len(cleaned) == 10:
        parsed = datetime.fromisoformat(cleaned)
        if end_of_day:
            return parsed.replace(hour=23, minute=59, second=59)
        return parsed
    return datetime.fromisoformat(cleaned)


def matches_project_filter(project_path: str, project_query: str) -> bool:
    """判断项目路径是否匹配过滤条件"""
    if not project_query:
        return True
    return project_query.lower() in (project_path or "").lower()


def matches_date_range(start_time: Optional[datetime], since: Optional[datetime], until: Optional[datetime]) -> bool:
    """判断开始时间是否在筛选范围内"""
    if since is None and until is None:
        return True
    if start_time is None:
        return False
    start_cmp = normalize_datetime(start_time)
    since_cmp = normalize_datetime(since)
    until_cmp = normalize_datetime(until)
    if since_cmp and start_cmp < since_cmp:
        return False
    if until_cmp and start_cmp > until_cmp:
        return False
    return True


def extract_text_from_content(content) -> str:
    """从消息内容中提取文本"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") in {"text", "input_text", "output_text"} and item.get("text"):
                    parts.append(item.get("text"))
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(parts).strip()
    return ""


def get_default_index_path() -> Path:
    """获取默认索引数据库路径"""
    return Path.home() / ".cache" / "ai-session-viewer" / "index.db"


class SessionParser(ABC):
    """会话解析器基类"""

    @abstractmethod
    def get_sessions(self, limit: Optional[int] = 10, session_filter: Optional[SessionFilter] = None) -> list[SessionInfo]:
        """获取会话列表"""
        pass

    @abstractmethod
    def get_resume_command(self, session: SessionInfo) -> str:
        """获取恢复会话的命令"""
        pass

    @abstractmethod
    def get_tool_key(self) -> str:
        """获取工具标识"""
        pass

    @abstractmethod
    def get_tool_name(self) -> str:
        """获取工具名称"""
        pass

    @abstractmethod
    def extract_search_text(self, file_path: str) -> str:
        """提取用于搜索的会话文本"""
        pass


class ClaudeSessionParser(SessionParser):
    """Claude Code 会话解析器"""
    _SYSTEM_PREFIXES = (
        "You are a Claude-Mem",
        "You are a specialized",
        "IMPORTANT:",
        "# Claude Code",
        "The user sent the following message",
        "PROGRESS SUMMARY CHECKPOINT",
        "## Progress Update",
        "SessionStart:",
        "UserPromptSubmit hook",
        "Caveat: The messages below",
    )
    _SYSTEM_TAG_PREFIXES = (
        "<observed_from_primary_session>",
        "<what_happened>",
        "<local-command-caveat>",
        "<local-command-stdout>",
        "<local-command-",
        "<command-name>",
        "<system-reminder>",
    )

    def __init__(self):
        self.base_path = Path.home() / ".claude"
        self.projects_path = self.base_path / "projects"
        self.history_path = self.base_path / "history.jsonl"

    def get_tool_name(self) -> str:
        return "Claude Code"

    def get_tool_key(self) -> str:
        return "claude"

    def get_sessions(self, limit: Optional[int] = 10, session_filter: Optional[SessionFilter] = None) -> list[SessionInfo]:
        sessions = []

        if not self.projects_path.exists():
            return sessions

        # 遍历所有项目目录
        for project_dir in self.projects_path.iterdir():
            if not project_dir.is_dir():
                continue

            # 查找 .jsonl 会话文件
            for session_file in project_dir.glob("*.jsonl"):
                if session_file.name.startswith("."):
                    continue

                session = self._parse_session_file(session_file, project_dir.name, session_filter)
                # 只添加有用户输入的会话
                if session and session.first_message:
                    sessions.append(session)

        # 按最后活动时间排序
        sessions.sort(key=lambda s: s.last_time.replace(tzinfo=None) if s.last_time else datetime.min, reverse=True)
        if limit is None:
            return sessions
        return sessions[:limit]

    def _parse_session_file(self, file_path: Path, project_name: str, session_filter: Optional[SessionFilter]) -> Optional[SessionInfo]:
        """解析 Claude 会话文件"""
        try:
            session_id = file_path.stem
            messages = []
            user_messages = []
            first_user_message = ""
            model = ""
            start_time = None
            last_time = None
            search_tokens = build_search_tokens(session_filter.search) if session_filter and session_filter.has_search() else []
            search_found = set()
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg_type = data.get("type", "")

                        # 获取时间戳
                        ts = data.get("timestamp")
                        if ts:
                            try:
                                msg_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                if start_time is None:
                                    start_time = msg_time
                                last_time = msg_time
                            except:
                                pass

                        # 提取用户消息
                        if msg_type == "user":
                            messages.append(data)
                            msg = data.get("message", {})
                            content = msg.get("content", "")
                            msg_text = extract_text_from_content(content)
                            if msg_text:
                                # 判断是否为用户手动输入（非系统注入）
                                is_user_input = self._is_user_manual_input(msg_text)
                                if is_user_input:
                                    user_messages.append(msg_text)
                                    if not first_user_message:
                                        first_user_message = msg_text[:100]
                                    elif is_short_title(first_user_message) and not is_short_title(msg_text):
                                        # 如果首条消息太短，用后续较长消息替换
                                        first_user_message = msg_text[:100]
                                    if search_tokens:
                                        update_search_hits(search_tokens, search_found, msg_text)

                        # 提取模型信息
                        if msg_type == "assistant":
                            msg = data.get("message", {})
                            if msg.get("model") and not model:
                                model = msg.get("model", "")
                            if search_tokens:
                                content = msg.get("content", "")
                                msg_text = extract_text_from_content(content)
                                if msg_text:
                                    update_search_hits(search_tokens, search_found, msg_text)

                    except json.JSONDecodeError:
                        continue

            # 将项目名转换为实际路径
            project_path = project_name.replace("-", "/")
            if project_path.startswith("/"):
                project_path = project_path[1:]

            if session_filter and session_filter.has_project():
                if not matches_project_filter(project_path, session_filter.project.strip()):
                    return None

            if session_filter and session_filter.has_date_range():
                if not matches_date_range(start_time, session_filter.since, session_filter.until):
                    return None

            if search_tokens and len(search_found) != len(search_tokens):
                return None

            # 生成会话总结
            summary = self._generate_summary(user_messages)

            return SessionInfo(
                tool="claude",
                session_id=session_id,
                project_path=project_path,
                start_time=start_time,
                last_time=last_time,
                message_count=len(messages),
                first_message=first_user_message,
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                model=model,
                summary=summary,
                user_messages=user_messages
            )
        except Exception as e:
            return None

    def _is_user_manual_input(self, content: str) -> bool:
        """判断是否为用户手动输入（非系统注入）"""
        stripped = content.strip()
        if not stripped:
            return False

        for prefix in self._SYSTEM_PREFIXES:
            if stripped.startswith(prefix):
                return False

        for tag in self._SYSTEM_TAG_PREFIXES:
            if stripped.startswith(tag):
                return False

        if is_separator_line(stripped) or is_punctuation_only(stripped):
            return False

        return True

    def _generate_summary(self, user_messages: list) -> str:
        """根据用户消息生成会话总结"""
        if not user_messages:
            return "(无用户消息)"

        # 如果配置了 LLM 总结器，使用 LLM 生成总结
        summarizer = get_llm_summarizer()
        if summarizer:
            return summarizer.summarize(user_messages)

        # 否则使用简单的文本提取
        summary_parts = []
        for msg in user_messages[:5]:
            clean_msg = msg.strip()
            if len(clean_msg) > 60:
                clean_msg = clean_msg[:60] + "..."
            if clean_msg:
                summary_parts.append(f"• {clean_msg}")

        if len(user_messages) > 5:
            summary_parts.append(f"  ... 还有 {len(user_messages) - 5} 条消息")

        return "\n".join(summary_parts) if summary_parts else "(无有效消息)"

    def get_resume_command(self, session: SessionInfo) -> str:
        """生成 Claude 恢复命令"""
        # Claude Code 使用 -r <session_id> 恢复指定会话
        return f"claude -r {session.session_id}"

    def extract_search_text(self, file_path: str) -> str:
        """提取 Claude 会话的用户+助手消息文本"""
        parts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg_type = data.get("type", "")
                        msg = data.get("message", {})
                        content = extract_text_from_content(msg.get("content", ""))

                        if msg_type == "user":
                            if content and self._is_user_manual_input(content):
                                parts.append(content)
                        elif msg_type == "assistant":
                            if content:
                                parts.append(content)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            return ""
        return "\n".join(parts)


class CodexSessionParser(SessionParser):
    """Codex 会话解析器"""

    def __init__(self):
        self.base_path = Path.home() / ".codex"
        self.sessions_path = self.base_path / "sessions"
        self.history_path = self.base_path / "history.jsonl"

    def get_tool_name(self) -> str:
        return "Codex"

    def get_tool_key(self) -> str:
        return "codex"

    def get_sessions(self, limit: Optional[int] = 10, session_filter: Optional[SessionFilter] = None) -> list[SessionInfo]:
        sessions = []

        # 然后从 sessions 目录获取详细信息
        if self.sessions_path.exists():
            for year_dir in sorted(self.sessions_path.iterdir(), reverse=True):
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                for month_dir in sorted(year_dir.iterdir(), reverse=True):
                    if not month_dir.is_dir() or not month_dir.name.isdigit():
                        continue
                    for day_dir in sorted(month_dir.iterdir(), reverse=True):
                        if not day_dir.is_dir() or not day_dir.name.isdigit():
                            continue
                        for session_file in day_dir.glob("*.jsonl"):
                            session = self._parse_session_file(session_file, session_filter)
                            # 只添加有用户输入的会话
                            if session and session.first_message:
                                sessions.append(session)
                            if limit is not None and len(sessions) >= limit:
                                break
                        if limit is not None and len(sessions) >= limit:
                            break
                    if limit is not None and len(sessions) >= limit:
                        break
                if limit is not None and len(sessions) >= limit:
                    break

        # 按最后活动时间排序
        sessions.sort(key=lambda s: s.last_time.replace(tzinfo=None) if s.last_time else datetime.min, reverse=True)
        if limit is None:
            return sessions
        return sessions[:limit]

    def _parse_session_file(self, file_path: Path, session_filter: Optional[SessionFilter]) -> Optional[SessionInfo]:
        """解析 Codex 会话文件"""
        try:
            session_id = ""
            cwd = ""
            first_message = ""
            model = ""
            start_time = None
            last_time = None
            message_count = 0
            user_messages = []
            search_tokens = build_search_tokens(session_filter.search) if session_filter and session_filter.has_search() else []
            search_found = set()
            seen_user_messages = set()

            def update_last_time(timestamp: Optional[str]):
                nonlocal last_time
                if not timestamp:
                    return
                try:
                    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except Exception:
                    return
                if last_time is None or parsed > last_time:
                    last_time = parsed

            def add_user_message(message: str):
                nonlocal first_message, message_count
                clean = (message or "").strip()
                if not clean:
                    return
                if clean.startswith("# AGENTS.md instructions") or clean.startswith("<environment_context>"):
                    return
                if clean in seen_user_messages:
                    return

                seen_user_messages.add(clean)
                message_count += 1
                if not first_message:
                    first_message = clean[:100]
                user_messages.append(clean)
                if search_tokens:
                    update_search_hits(search_tokens, search_found, clean)

            def add_assistant_text(message: str):
                clean = (message or "").strip()
                if clean and search_tokens:
                    update_search_hits(search_tokens, search_found, clean)

            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg_type = data.get("type", "")

                        # 获取会话元数据
                        if msg_type == "session_meta":
                            payload = data.get("payload", {})
                            session_id = payload.get("id", "")
                            cwd = payload.get("cwd", "")
                            ts = data.get("timestamp")
                            if ts:
                                try:
                                    start_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                                except:
                                    pass

                        # 获取用户消息
                        if msg_type == "message" and data.get("role") == "user":
                            content = data.get("content", "")
                            add_user_message(extract_text_from_content(content))

                        # 获取模型信息
                        if msg_type == "message" and data.get("role") == "assistant":
                            if data.get("model") and not model:
                                model = data.get("model", "")
                            content = data.get("content", "")
                            add_assistant_text(extract_text_from_content(content))

                        if msg_type == "response_item":
                            payload = data.get("payload", {})
                            if payload.get("type") == "message":
                                role = payload.get("role")
                                msg_text = extract_text_from_content(payload.get("content", ""))
                                if role == "user":
                                    add_user_message(msg_text)
                                elif role == "assistant":
                                    add_assistant_text(msg_text)
                                    if payload.get("model") and not model:
                                        model = payload.get("model", "")

                        if msg_type == "event_msg":
                            payload = data.get("payload", {})
                            event_type = payload.get("type")
                            if event_type == "user_message":
                                add_user_message(payload.get("message", ""))
                            elif event_type == "agent_message":
                                add_assistant_text(payload.get("message", ""))

                    except json.JSONDecodeError:
                        continue

            if not session_id:
                # 从文件名提取 session_id
                session_id = file_path.stem.split("-")[-1] if "-" in file_path.stem else file_path.stem

            if session_filter and session_filter.has_project():
                if not matches_project_filter(cwd, session_filter.project.strip()):
                    return None

            if session_filter and session_filter.has_date_range():
                if not matches_date_range(start_time, session_filter.since, session_filter.until):
                    return None

            if search_tokens and len(search_found) != len(search_tokens):
                return None

            # 生成会话总结
            summary = self._generate_summary(user_messages)

            return SessionInfo(
                tool="codex",
                session_id=session_id,
                project_path=cwd,
                start_time=start_time,
                last_time=last_time or start_time,
                message_count=message_count,
                first_message=first_message,
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                model=model,
                summary=summary,
                user_messages=user_messages
            )
        except Exception as e:
            return None

    def _generate_summary(self, user_messages: list) -> str:
        """根据用户消息生成会话总结"""
        if not user_messages:
            return "(无用户消息)"

        summary_parts = []
        for msg in user_messages[:5]:
            clean_msg = msg.strip()
            if len(clean_msg) > 60:
                clean_msg = clean_msg[:60] + "..."
            if clean_msg:
                summary_parts.append(f"• {clean_msg}")

        if len(user_messages) > 5:
            summary_parts.append(f"  ... 还有 {len(user_messages) - 5} 条消息")

        return "\n".join(summary_parts) if summary_parts else "(无有效消息)"

    def get_resume_command(self, session: SessionInfo) -> str:
        """生成 Codex 恢复命令"""
        return f"codex --resume {session.session_id}"

    def extract_search_text(self, file_path: str) -> str:
        """提取 Codex 会话的用户+助手消息文本"""
        parts = []
        seen = set()

        def add_content(content, *, skip_system=False):
            text = extract_text_from_content(content).strip()
            if not text or text in seen:
                return
            if skip_system and (
                text.startswith("# AGENTS.md instructions")
                or text.startswith("<environment_context>")
            ):
                return
            seen.add(text)
            parts.append(text)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg_type = data.get("type")
                        if msg_type == "message":
                            role = data.get("role", "")
                            if role in ("user", "assistant"):
                                add_content(data.get("content", ""), skip_system=(role == "user"))
                        elif msg_type == "response_item":
                            payload = data.get("payload", {})
                            if payload.get("type") == "message" and payload.get("role") in ("user", "assistant"):
                                add_content(payload.get("content", ""), skip_system=(payload.get("role") == "user"))
                        elif msg_type == "event_msg":
                            payload = data.get("payload", {})
                            if payload.get("type") in ("user_message", "agent_message"):
                                add_content(payload.get("message", ""), skip_system=(payload.get("type") == "user_message"))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            return ""
        return "\n".join(parts)


class SessionIndexer:
    """会话索引器（SQLite + FTS5）"""

    def __init__(self, db_path: Path, parsers: list[SessionParser]):
        self.db_path = Path(db_path).expanduser()
        self.parsers = {parser.get_tool_key(): parser for parser in parsers}

    def _ensure_schema(self, conn: sqlite3.Connection):
        """初始化数据库结构"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                tool TEXT NOT NULL,
                session_id TEXT NOT NULL,
                project_path TEXT,
                start_time TEXT,
                last_time TEXT,
                message_count INTEGER,
                first_message TEXT,
                summary TEXT,
                file_path TEXT NOT NULL UNIQUE,
                file_size INTEGER,
                model TEXT,
                mtime INTEGER
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_tool ON sessions(tool)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project_path ON sessions(project_path)")
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts
            USING fts5(content, project_path, session_id, tool)
        """)

    def _load_existing(self, conn: sqlite3.Connection) -> dict[str, dict]:
        """加载已有索引记录"""
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, file_path, file_size, mtime FROM sessions").fetchall()
        existing = {}
        for row in rows:
            existing[row["file_path"]] = {
                "id": row["id"],
                "file_size": row["file_size"],
                "mtime": row["mtime"],
            }
        return existing

    def build_index(self, sessions_by_tool: dict[str, list[SessionInfo]]) -> dict[str, int]:
        """构建或增量更新索引"""
        all_sessions = []
        for tool_sessions in sessions_by_tool.values():
            all_sessions.extend(tool_sessions)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        stats = {
            "scanned": len(all_sessions),
            "indexed": 0,
            "skipped": 0,
            "removed": 0,
            "errors": 0,
        }

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema(conn)
        existing = self._load_existing(conn)
        seen_paths = set()

        with conn:
            for session in all_sessions:
                file_path = session.file_path
                if not file_path:
                    stats["errors"] += 1
                    continue
                seen_paths.add(file_path)

                file_stat = None
                try:
                    file_stat = Path(file_path).stat()
                except FileNotFoundError:
                    stats["errors"] += 1
                    continue

                current_size = file_stat.st_size
                current_mtime = int(file_stat.st_mtime)
                existing_entry = existing.get(file_path)

                if existing_entry and existing_entry["file_size"] == current_size and existing_entry["mtime"] == current_mtime:
                    stats["skipped"] += 1
                    continue

                parser = self.parsers.get(session.tool)
                if not parser:
                    stats["errors"] += 1
                    continue

                search_text = parser.extract_search_text(file_path)
                start_time = format_datetime(session.start_time)
                last_time = format_datetime(session.last_time)
                project_path = session.project_path or ""
                first_message = session.first_message or ""
                summary = session.summary or ""

                if existing_entry:
                    session_id = existing_entry["id"]
                    conn.execute("""
                        UPDATE sessions
                        SET tool = ?, session_id = ?, project_path = ?, start_time = ?, last_time = ?,
                            message_count = ?, first_message = ?, summary = ?, file_path = ?, file_size = ?,
                            model = ?, mtime = ?
                        WHERE id = ?
                    """, (
                        session.tool,
                        session.session_id,
                        project_path,
                        start_time,
                        last_time,
                        session.message_count,
                        first_message,
                        summary,
                        file_path,
                        current_size,
                        session.model,
                        current_mtime,
                        session_id,
                    ))
                else:
                    cursor = conn.execute("""
                        INSERT INTO sessions (
                            tool, session_id, project_path, start_time, last_time, message_count,
                            first_message, summary, file_path, file_size, model, mtime
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session.tool,
                        session.session_id,
                        project_path,
                        start_time,
                        last_time,
                        session.message_count,
                        first_message,
                        summary,
                        file_path,
                        current_size,
                        session.model,
                        current_mtime,
                    ))
                    session_id = cursor.lastrowid

                conn.execute("DELETE FROM sessions_fts WHERE rowid = ?", (session_id,))
                conn.execute("""
                    INSERT INTO sessions_fts (rowid, content, project_path, session_id, tool)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_id,
                    search_text,
                    project_path,
                    session.session_id,
                    session.tool,
                ))
                stats["indexed"] += 1

            for file_path, entry in existing.items():
                if file_path not in seen_paths:
                    conn.execute("DELETE FROM sessions WHERE id = ?", (entry["id"],))
                    conn.execute("DELETE FROM sessions_fts WHERE rowid = ?", (entry["id"],))
                    stats["removed"] += 1

        conn.close()
        return stats

    def query(self, session_filter: SessionFilter, tool: str, limit: Optional[int]) -> list[SessionInfo]:
        """从索引数据库查询会话"""
        if not self.db_path.exists():
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        clauses = []
        params = []
        join_fts = False

        fts_query = build_fts_query(session_filter.search)
        if fts_query:
            join_fts = True
            clauses.append("sessions_fts MATCH ?")
            params.append(fts_query)

        if session_filter.has_project():
            clauses.append("s.project_path LIKE ?")
            params.append(f"%{session_filter.project.strip()}%")

        if session_filter.has_date_range():
            if session_filter.since:
                clauses.append("s.start_time >= ?")
                params.append(format_datetime(session_filter.since))
            if session_filter.until:
                clauses.append("s.start_time <= ?")
                params.append(format_datetime(session_filter.until))

        if tool != "all":
            clauses.append("s.tool = ?")
            params.append(tool)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        join_clause = "JOIN sessions_fts ON sessions_fts.rowid = s.id" if join_fts else ""
        limit_clause = "LIMIT ?" if limit is not None else ""
        if limit is not None:
            params.append(limit)

        query = f"""
            SELECT s.*
            FROM sessions s
            {join_clause}
            {where_clause}
            ORDER BY COALESCE(s.last_time, s.start_time) DESC
            {limit_clause}
        """

        rows = conn.execute(query, params).fetchall()
        conn.close()

        sessions = []
        for row in rows:
            start_time = datetime.fromisoformat(row["start_time"]) if row["start_time"] else None
            last_time = datetime.fromisoformat(row["last_time"]) if row["last_time"] else None
            sessions.append(SessionInfo(
                tool=row["tool"],
                session_id=row["session_id"],
                project_path=row["project_path"] or "",
                start_time=start_time,
                last_time=last_time,
                message_count=row["message_count"] or 0,
                first_message=row["first_message"] or "",
                file_path=row["file_path"] or "",
                file_size=row["file_size"] or 0,
                model=row["model"] or "",
                summary=row["summary"] or ""
            ))

        return sessions


class SessionViewer:
    """会话查看器主类"""

    def __init__(self):
        self.parsers = [
            ClaudeSessionParser(),
            CodexSessionParser()
        ]

    def get_all_sessions(self, limit: Optional[int] = 10, session_filter: Optional[SessionFilter] = None) -> dict[str, list[SessionInfo]]:
        """获取所有工具的会话"""
        result = {}
        for parser in self.parsers:
            sessions = parser.get_sessions(limit, session_filter)
            result[parser.get_tool_name()] = sessions
        return result

    def get_sessions_by_tool(self, tool: str, limit: Optional[int] = 10, session_filter: Optional[SessionFilter] = None) -> list[SessionInfo]:
        """获取指定工具的会话"""
        tool_lower = tool.lower()
        for parser in self.parsers:
            if tool_lower in parser.get_tool_name().lower():
                return parser.get_sessions(limit, session_filter)
        return []

    def get_resume_command(self, session: SessionInfo) -> str:
        """获取恢复命令"""
        for parser in self.parsers:
            if session.tool in parser.get_tool_name().lower():
                return parser.get_resume_command(session)
        return ""

    def format_session(self, session: SessionInfo, show_detail: bool = False, index: int = 0) -> str:
        """格式化会话信息"""
        lines = []

        # 基本信息
        time_str = session.last_time.strftime("%Y-%m-%d %H:%M") if session.last_time else "未知"
        size_str = self._format_size(session.file_size)

        # 会话标题（第一条用户消息）
        title = session.first_message[:60] if session.first_message else "(无标题)"
        if len(session.first_message) > 60:
            title += "..."

        lines.append(f"📌 [{index}] {title}")
        lines.append(f"   ⏰ {time_str} | 💬 {session.message_count} 条消息 | 📊 {size_str}")
        lines.append(f"   📁 {session.project_path or '(无项目)'}")

        if session.model:
            lines.append(f"   🤖 {session.model}")

        # 恢复命令
        resume_cmd = self.get_resume_command(session)
        lines.append(f"   🔄 {resume_cmd}")

        if show_detail:
            lines.append(f"   📄 {session.file_path}")

        return "\n".join(lines)

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / 1024 / 1024:.1f} MB"

    def generate_summary(self, sessions: dict[str, list[SessionInfo]]) -> str:
        """生成会话摘要"""
        lines = []
        lines.append("=" * 60)
        lines.append("🔍 AI 会话记录总结")
        lines.append("=" * 60)

        total_sessions = 0
        total_messages = 0

        for tool_name, tool_sessions in sessions.items():
            count = len(tool_sessions)
            total_sessions += count
            msgs = sum(s.message_count for s in tool_sessions)
            total_messages += msgs

            lines.append(f"\n📦 {tool_name}: {count} 个会话, {msgs} 条消息")

            if tool_sessions:
                latest = tool_sessions[0]
                time_str = latest.last_time.strftime("%Y-%m-%d %H:%M") if latest.last_time else "未知"
                lines.append(f"   └─ 最近会话: {time_str}")

        lines.append(f"\n📊 总计: {total_sessions} 个会话, {total_messages} 条消息")
        lines.append("=" * 60)

        return "\n".join(lines)

    def view_session_detail(self, session: SessionInfo):
        """查看会话详细内容"""
        print(f"\n{'=' * 60}")
        print(f"📖 会话详情: {session.session_id[:8]}...")
        print("=" * 60)

        # 基本信息
        time_str = session.last_time.strftime("%Y-%m-%d %H:%M") if session.last_time else "未知"
        start_str = session.start_time.strftime("%Y-%m-%d %H:%M") if session.start_time else "未知"
        print(f"⏰ 时间: {time_str}")
        print(f"🕘 开始: {start_str}")
        print(f"📁 项目: {session.project_path or '(无)'}")
        print(f"🤖 模型: {session.model or '(未知)'}")
        print(f"💬 消息数: {session.message_count}")
        print(f"🔄 恢复命令: {self.get_resume_command(session)}")
        print(f"{'─' * 60}")

        # 显示用户消息
        if session.user_messages:
            print("\n📝 对话记录 (用户消息):\n")
            for i, msg in enumerate(session.user_messages, 1):
                # 清理消息内容
                clean_msg = msg.strip()
                # 跳过系统消息
                if clean_msg.startswith("<") or clean_msg.startswith("You are"):
                    continue
                # 截断过长的消息
                if len(clean_msg) > 200:
                    clean_msg = clean_msg[:200] + "..."
                print(f"  [{i}] {clean_msg}")
                print()
        else:
            print("\n(无用户消息记录)")

        print(f"{'=' * 60}")

    def print_sessions(self, sessions: dict[str, list[SessionInfo]], show_detail: bool = False, interactive: bool = False):
        """打印指定会话列表"""
        # 先打印摘要
        print(self.generate_summary(sessions))

        # 构建全局会话索引
        all_sessions = []
        session_index = 1

        # 打印各工具的会话详情
        for tool_name, tool_sessions in sessions.items():
            print(f"\n{'─' * 60}")
            print(f"🛠️  {tool_name} 会话列表")
            print(f"{'─' * 60}")

            if not tool_sessions:
                print("   (无会话记录)")
                continue

            for session in tool_sessions:
                print(f"\n{self.format_session(session, show_detail, session_index)}")
                all_sessions.append(session)
                session_index += 1

        # 交互式模式
        if interactive and all_sessions:
            print(f"\n{'=' * 60}")
            print("💡 输入序号查看会话详情，输入 q 退出")
            print("=" * 60)

            while True:
                try:
                    choice = input("\n请选择会话序号 (1-{}, q 退出): ".format(len(all_sessions))).strip()

                    if choice.lower() == 'q':
                        print("👋 再见！")
                        break

                    idx = int(choice)
                    if 1 <= idx <= len(all_sessions):
                        self.view_session_detail(all_sessions[idx - 1])
                    else:
                        print(f"⚠️ 请输入 1-{len(all_sessions)} 之间的数字")
                except ValueError:
                    print("⚠️ 请输入有效的数字或 q")
                except KeyboardInterrupt:
                    print("\n👋 再见！")
                    break
        else:
            # 非交互模式，打印恢复命令示例
            print(f"\n{'=' * 60}")
            print("🔄 恢复对话命令示例")
            print("=" * 60)
            print("""
Claude Code:
  claude -r <session_id>           # 恢复指定会话
  claude --resume                  # 恢复最近会话

Codex:
  codex --resume <session_id>      # 恢复指定会话
  codex --resume                   # 恢复最近会话

💡 提示: 使用 -i 参数进入交互模式，可选择查看会话详情
""")

    def print_all(self, limit: int = 5, show_detail: bool = False, interactive: bool = False, session_filter: Optional[SessionFilter] = None):
        """打印所有会话"""
        sessions = self.get_all_sessions(limit, session_filter)
        self.print_sessions(sessions, show_detail, interactive)


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="AI 会话记录查看器 - 支持 Claude Code, Codex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 查看所有工具的最近 5 个会话
  %(prog)s -l 10              # 查看最近 10 个会话（覆盖默认值）
  %(prog)s -t claude          # 只查看 Claude 的会话（默认显示 20 个）
  %(prog)s -t claude -l 50    # 只查看 Claude 的 50 个会话
  %(prog)s -d                 # 显示详细信息（包括文件路径）
  %(prog)s --summary          # 只显示摘要
  %(prog)s --search "关键词"  # 全局搜索（用户+助手消息）
  %(prog)s --project "/path"  # 按项目路径筛选
  %(prog)s --since 2026-01-01 # 按开始时间筛选
  %(prog)s --build-index      # 构建索引数据库（用于 Mac 应用）

LLM 智能总结示例:
  %(prog)s --ai-summary                           # 使用 OpenAI 生成智能总结
  %(prog)s --ai-summary --provider anthropic      # 使用 Anthropic Claude
  %(prog)s --ai-summary --provider google         # 使用 Google Gemini
  %(prog)s --ai-summary --model gpt-4o            # 指定模型

环境变量:
  OPENAI_API_KEY      - OpenAI API Key
  ANTHROPIC_API_KEY   - Anthropic API Key
  GOOGLE_API_KEY      - Google API Key
        """
    )

    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=None,  # 改为None，后面根据tool类型智能设置
        help="每个工具显示的会话数量 (默认: 查看所有工具时为5，单个工具时为20)"
    )

    parser.add_argument(
        "-t", "--tool",
        type=str,
        choices=["claude", "codex", "all"],
        default="all",
        help="指定查看的工具 (默认: all)"
    )

    parser.add_argument(
        "-d", "--detail",
        action="store_true",
        help="显示详细信息"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="交互模式，可选择查看会话详情"
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="只显示摘要"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出"
    )

    parser.add_argument(
        "--build-index",
        action="store_true",
        help="构建索引数据库（SQLite + FTS5）"
    )

    parser.add_argument(
        "--use-index",
        action="store_true",
        help="从索引数据库读取会话"
    )

    parser.add_argument(
        "--db-path",
        type=str,
        default="",
        help="索引数据库路径（默认: ~/.cache/ai-session-viewer/index.db）"
    )

    parser.add_argument(
        "--search",
        type=str,
        default="",
        help="全局搜索关键词（匹配用户+助手消息）"
    )

    parser.add_argument(
        "--project",
        type=str,
        default="",
        help="按项目路径关键词筛选"
    )

    parser.add_argument(
        "--since",
        type=str,
        default="",
        help="按开始时间筛选（如 2026-01-01 或 2026-01-01 10:00）"
    )

    parser.add_argument(
        "--until",
        type=str,
        default="",
        help="按开始时间筛选（结束时间，包含）"
    )

    # LLM 总结相关参数
    parser.add_argument(
        "--ai-summary",
        action="store_true",
        help="使用 LLM 生成智能会话总结"
    )

    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "anthropic", "google"],
        default="openai",
        help="LLM 提供商 (默认: openai)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="",
        help="指定 LLM 模型名称 (默认: 各提供商的默认模型)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="LLM API Key (也可通过环境变量设置)"
    )

    parser.add_argument(
        "--base-url",
        type=str,
        default="",
        help="自定义 API 地址 (用于 OpenAI 兼容接口)"
    )

    args = parser.parse_args()

    # 构建过滤条件
    since_dt = None
    until_dt = None
    if args.since:
        try:
            since_dt = parse_datetime_input(args.since, end_of_day=False)
        except ValueError as exc:
            print(f"⚠️ 无效的 --since 参数: {exc}")
            sys.exit(1)
    if args.until:
        try:
            until_dt = parse_datetime_input(args.until, end_of_day=True)
        except ValueError as exc:
            print(f"⚠️ 无效的 --until 参数: {exc}")
            sys.exit(1)
    session_filter = SessionFilter(
        search=args.search,
        project=args.project,
        since=since_dt,
        until=until_dt
    )

    # 智能设置默认 limit：有过滤时默认不限制
    has_filters = session_filter.has_search() or session_filter.has_project() or session_filter.has_date_range()
    if args.limit is None:
        if args.build_index:
            args.limit = None
        elif has_filters:
            args.limit = None
        else:
            args.limit = 5 if args.tool == "all" else 20

    # 如果启用了 AI 总结，初始化 LLM 总结器
    if args.ai_summary:
        config = LLMConfig(
            provider=args.provider,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url
        )
        set_llm_summarizer(config)
        print(f"🤖 已启用 LLM 智能总结 (提供商: {args.provider}, 模型: {config.get_model()})")
        print()

    viewer = SessionViewer()

    db_path = Path(args.db_path) if args.db_path else get_default_index_path()
    parser_map = {parser.get_tool_key(): parser for parser in viewer.parsers}

    if args.build_index:
        if args.tool == "all":
            sessions = viewer.get_all_sessions(args.limit, session_filter)
        else:
            sessions = {args.tool.capitalize(): viewer.get_sessions_by_tool(args.tool, args.limit, session_filter)}

        indexer = SessionIndexer(db_path, viewer.parsers)
        stats = indexer.build_index(sessions)
        print("🔧 索引构建完成")
        print(f"📦 扫描会话: {stats['scanned']}")
        print(f"✅ 索引更新: {stats['indexed']}")
        print(f"⏭️ 跳过未变: {stats['skipped']}")
        print(f"🧹 清理移除: {stats['removed']}")
        print(f"⚠️ 解析异常: {stats['errors']}")
        print(f"📁 索引路径: {db_path}")
        return

    if args.use_index:
        indexer = SessionIndexer(db_path, viewer.parsers)
        results = indexer.query(session_filter, args.tool, args.limit)
        if args.tool == "all":
            sessions = {parser.get_tool_name(): [] for parser in viewer.parsers}
            for session in results:
                parser = parser_map.get(session.tool)
                tool_name = parser.get_tool_name() if parser else session.tool
                sessions.setdefault(tool_name, []).append(session)
        else:
            parser = parser_map.get(args.tool)
            tool_name = parser.get_tool_name() if parser else args.tool
            sessions = {tool_name: results}
    else:
        if args.tool == "all":
            sessions = viewer.get_all_sessions(args.limit, session_filter)
        else:
            sessions = {args.tool.capitalize(): viewer.get_sessions_by_tool(args.tool, args.limit, session_filter)}

    if args.json:
        # JSON 输出
        output = {}
        for tool, tool_sessions in sessions.items():
            output[tool] = [
                {
                    "session_id": s.session_id,
                    "project_path": s.project_path,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "last_time": s.last_time.isoformat() if s.last_time else None,
                    "message_count": s.message_count,
                    "first_message": s.first_message,
                    "file_path": s.file_path,
                    "file_size": s.file_size,
                    "model": s.model,
                    "resume_command": viewer.get_resume_command(s)
                }
                for s in tool_sessions
            ]
        print(json.dumps(output, indent=2, ensure_ascii=False))
    elif args.summary:
        print(viewer.generate_summary(sessions))
    else:
        viewer.print_sessions(sessions, args.detail, args.interactive)


if __name__ == "__main__":
    main()
