import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import session_viewer as core


def format_time(value):
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M")


class AISessionViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Session Viewer")
        self.geometry("1180x720")
        self.minsize(960, 580)

        self.viewer = core.SessionViewer()
        self.parser_by_tool = {parser.get_tool_key(): parser for parser in self.viewer.parsers}
        self.sessions = []
        self.selected_session = None
        self.match_ranges = []
        self.current_match_index = -1

        self.tool_var = tk.StringVar(value="all")
        self.limit_var = tk.StringVar(value="50")
        self.search_var = tk.StringVar()
        self.project_var = tk.StringVar()
        self.detail_find_var = tk.StringVar()
        self.match_status_var = tk.StringVar(value="0 matches")
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self.detail_find_var.trace_add("write", lambda *_args: self.highlight_detail_matches(reset_index=True))
        self.refresh_sessions()

    def _build_ui(self):
        controls = ttk.Frame(self, padding=10)
        controls.pack(fill=tk.X)

        ttk.Label(controls, text="Tool").pack(side=tk.LEFT)
        tool_box = ttk.Combobox(
            controls,
            textvariable=self.tool_var,
            values=("all", "claude", "codex"),
            width=10,
            state="readonly",
        )
        tool_box.pack(side=tk.LEFT, padx=(6, 14))

        ttk.Label(controls, text="Limit").pack(side=tk.LEFT)
        ttk.Entry(controls, textvariable=self.limit_var, width=8).pack(side=tk.LEFT, padx=(6, 14))

        ttk.Label(controls, text="Search").pack(side=tk.LEFT)
        search_entry = ttk.Entry(controls, textvariable=self.search_var, width=28)
        search_entry.pack(side=tk.LEFT, padx=(6, 14))
        search_entry.bind("<Return>", lambda _event: self.refresh_sessions())

        ttk.Label(controls, text="Project").pack(side=tk.LEFT)
        project_entry = ttk.Entry(controls, textvariable=self.project_var, width=28)
        project_entry.pack(side=tk.LEFT, padx=(6, 14))
        project_entry.bind("<Return>", lambda _event: self.refresh_sessions())

        ttk.Button(controls, text="Refresh", command=self.refresh_sessions).pack(side=tk.LEFT)
        ttk.Button(controls, text="Copy Resume Command", command=self.copy_resume_command).pack(side=tk.LEFT, padx=(8, 0))

        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        list_frame = ttk.Frame(body)
        body.add(list_frame, weight=3)

        columns = ("tool", "last_time", "messages", "model", "project", "title")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("tool", text="Tool")
        self.tree.heading("last_time", text="Last Activity")
        self.tree.heading("messages", text="Messages")
        self.tree.heading("model", text="Model")
        self.tree.heading("project", text="Project")
        self.tree.heading("title", text="Title")
        self.tree.column("tool", width=80, stretch=False)
        self.tree.column("last_time", width=140, stretch=False)
        self.tree.column("messages", width=80, stretch=False, anchor=tk.E)
        self.tree.column("model", width=170, stretch=False)
        self.tree.column("project", width=260)
        self.tree.column("title", width=360)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_session_selected)

        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=list_scroll.set)

        detail_frame = ttk.Frame(body)
        body.add(detail_frame, weight=2)

        self.summary_var = tk.StringVar()
        ttk.Label(detail_frame, textvariable=self.summary_var, font=("", 10, "bold")).pack(fill=tk.X, pady=(0, 6))

        find_controls = ttk.Frame(detail_frame)
        find_controls.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(find_controls, text="Find in chat").pack(side=tk.LEFT)
        find_entry = ttk.Entry(find_controls, textvariable=self.detail_find_var, width=28)
        find_entry.pack(side=tk.LEFT, padx=(6, 8))
        find_entry.bind("<Return>", lambda _event: self.highlight_detail_matches(reset_index=True))

        ttk.Button(find_controls, text="Prev", command=self.find_previous_match).pack(side=tk.LEFT)
        ttk.Button(find_controls, text="Next", command=self.find_next_match).pack(side=tk.LEFT, padx=(6, 8))
        ttk.Label(find_controls, textvariable=self.match_status_var).pack(side=tk.LEFT)

        self.detail_text = ScrolledText(detail_frame, wrap=tk.WORD, height=20)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.tag_configure("search_match", background="#fff59d")
        self.detail_text.tag_configure("search_match_active", background="#ffb74d")

        status = ttk.Label(self, textvariable=self.status_var, anchor=tk.W, padding=(10, 0))
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def refresh_sessions(self):
        try:
            limit = int(self.limit_var.get().strip() or "50")
            if limit < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid limit", "Limit must be a positive integer.")
            return

        session_filter = core.SessionFilter(
            search=self.search_var.get().strip(),
            project=self.project_var.get().strip(),
        )

        try:
            tool = self.tool_var.get()
            if tool == "all":
                sessions_by_tool = self.viewer.get_all_sessions(limit, session_filter)
            else:
                label = "Claude Code" if tool == "claude" else "Codex"
                sessions_by_tool = {label: self.viewer.get_sessions_by_tool(tool, limit, session_filter)}
        except Exception as error:
            messagebox.showerror("Load failed", str(error))
            return

        self.sessions = []
        for tool_name, tool_sessions in sessions_by_tool.items():
            for session in tool_sessions:
                self.sessions.append((tool_name, session))

        self.sessions.sort(
            key=lambda item: item[1].last_time.timestamp() if item[1].last_time else 0,
            reverse=True,
        )

        self.tree.delete(*self.tree.get_children())
        for index, (tool_name, session) in enumerate(self.sessions):
            title = session.first_message.replace("\n", " ").strip() if session.first_message else "(no title)"
            self.tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    tool_name,
                    format_time(session.last_time),
                    session.message_count,
                    session.model,
                    session.project_path,
                    title[:160],
                ),
            )

        total_messages = sum(session.message_count for _tool, session in self.sessions)
        self.summary_var.set(f"{len(self.sessions)} sessions, {total_messages} messages")
        self.status_var.set("Loaded sessions from ~/.claude and ~/.codex")
        self.selected_session = None
        self.match_ranges = []
        self.current_match_index = -1
        self.match_status_var.set("0 matches")
        self.detail_text.delete("1.0", tk.END)

    def on_session_selected(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        index = int(selection[0])
        _tool_name, session = self.sessions[index]
        self.selected_session = session
        self.show_session_detail(session)

    def show_session_detail(self, session):
        resume_command = self.viewer.get_resume_command(session)
        transcript = self.get_searchable_transcript(session)
        lines = [
            f"Title: {session.first_message or '(no title)'}",
            f"Session ID: {session.session_id}",
            f"Last activity: {format_time(session.last_time)}",
            f"Start time: {format_time(session.start_time)}",
            f"Messages: {session.message_count}",
            f"Model: {session.model or '(unknown)'}",
            f"Project: {session.project_path or '(none)'}",
            f"File: {session.file_path}",
            f"Resume command: {resume_command}",
            "",
            "Transcript:",
        ]

        if transcript:
            lines.append(transcript)
        else:
            lines.append("(no searchable transcript)")

        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, "\n".join(lines))
        if not self.detail_find_var.get().strip() and self.search_var.get().strip():
            self.detail_find_var.set(self.search_var.get().strip())
        else:
            self.highlight_detail_matches(reset_index=True)

    def get_searchable_transcript(self, session):
        parser = self.parser_by_tool.get(session.tool)
        transcript = ""
        if parser is not None:
            transcript = parser.extract_search_text(session.file_path)
        if transcript:
            return transcript
        return "\n\n".join(message.strip() for message in session.user_messages if message.strip())

    def highlight_detail_matches(self, reset_index=True):
        self.detail_text.tag_remove("search_match", "1.0", tk.END)
        self.detail_text.tag_remove("search_match_active", "1.0", tk.END)
        self.match_ranges = []
        self.current_match_index = -1

        query = self.detail_find_var.get().strip()
        if not query:
            self.match_status_var.set("0 matches")
            return

        count = tk.IntVar()
        search_from = "1.0"
        while True:
            match_start = self.detail_text.search(query, search_from, stopindex=tk.END, nocase=True, count=count)
            if not match_start:
                break
            match_end = f"{match_start}+{count.get()}c"
            self.match_ranges.append((match_start, match_end))
            self.detail_text.tag_add("search_match", match_start, match_end)
            search_from = match_end

        if not self.match_ranges:
            self.match_status_var.set("0 matches")
            return

        if reset_index or self.current_match_index < 0:
            self.current_match_index = 0
        else:
            self.current_match_index %= len(self.match_ranges)
        self.focus_current_match()

    def focus_current_match(self):
        self.detail_text.tag_remove("search_match_active", "1.0", tk.END)
        if not self.match_ranges or self.current_match_index < 0:
            self.match_status_var.set("0 matches")
            return

        match_start, match_end = self.match_ranges[self.current_match_index]
        self.detail_text.tag_add("search_match_active", match_start, match_end)
        self.detail_text.mark_set(tk.INSERT, match_start)
        self.detail_text.see(match_start)
        self.match_status_var.set(f"{self.current_match_index + 1}/{len(self.match_ranges)} matches")

    def move_match(self, step):
        if not self.match_ranges:
            self.highlight_detail_matches(reset_index=True)
            return
        self.current_match_index = (self.current_match_index + step) % len(self.match_ranges)
        self.focus_current_match()

    def find_previous_match(self):
        self.move_match(-1)

    def find_next_match(self):
        self.move_match(1)

    def copy_resume_command(self):
        if self.selected_session is None:
            messagebox.showinfo("No session selected", "Select a session first.")
            return

        command = self.viewer.get_resume_command(self.selected_session)
        self.clipboard_clear()
        self.clipboard_append(command)
        self.status_var.set(f"Copied: {command}")


if __name__ == "__main__":
    app = AISessionViewerApp()
    app.mainloop()
