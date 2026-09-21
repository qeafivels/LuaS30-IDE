"""HTML renderer for the AI chat transcript (QTextBrowser subset of CSS).

Tách riêng từ `ai_chat_view.py` theo PROMPT "Modern Dark AI Assistant":
view giữ logic agent, module này chỉ dựng chuỗi HTML cho thẻ tin nhắn —
avatar + tên + timestamp, prose (inline code / đậm), và khối code có
cột số dòng, tô màu cú pháp Lua và nút "Sao chép" (neo x-luas30://copy/<id>).
Mọi màu lấy qua `palette.CHAT_*` để `studio_theme_check.py` quản được.
"""
from __future__ import annotations

import html
import re

from app.ui import palette

_LUA_TOKEN_RE = re.compile(
    r"(--\[\[[\s\S]*?\]\]|--[^\n]*)"
    r"|(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')"
    r"|(\b\d+\.?\d*\b)"
    r"|(\b(?:and|break|do|else|elseif|end|false|for|function|if|in|local|nil|not|or|repeat|return|then|true|until|while)\b)"
    r"|(\b[A-Za-z_]\w*(?=\s*\())"
)
_FENCE_RE = re.compile(r"```([A-Za-z0-9_+-]*)\n?(.*?)```", re.DOTALL)


_CODE_FONT = '"JetBrains Mono","Cascadia Code",Consolas,monospace'


class TranscriptHtmlRenderer:
    def __init__(self) -> None:
        self.copy_blocks: dict[str, str] = {}
        self._copy_seq = 0

    def reset(self) -> None:
        self.copy_blocks = {}
        self._copy_seq = 0

    def avatar_html(self, role: str) -> str:
        if role == "user":
            bg, fg, glyph = palette.CHAT_AVATAR_USER, palette.CHAT_TEXT, "B"
        else:
            bg, fg, glyph = palette.CHAT_ACCENT_DEEP, palette.CHAT_ACCENT, "◆"
        return (
            '<table cellspacing="0" cellpadding="0"><tr>'
            f'<td align="center" width="28" height="28" style="background-color:{bg};'
            f'color:{fg};font-size:13px;font-weight:700;">{glyph}</td></tr></table>'
        )

    def head_html(self, role: str, when: str = "") -> str:
        name = "Bạn" if role == "user" else "AI Agent"
        time_cell = (
            f'<td align="right" style="vertical-align:bottom;color:{palette.CHAT_TS};'
            f'font-size:11px;">{html.escape(when)}</td>'
            if when
            else "<td></td>"
        )
        return (
            '<table width="100%" cellspacing="0" cellpadding="0"><tr>'
            f'<td style="color:{palette.CHAT_TEXT};font-weight:700;font-size:13px;">{name}</td>'
            f"{time_cell}</tr></table>"
        )

    def render_markdown(self, text: str) -> str:
        out: list[str] = []
        pos = 0
        for m in _FENCE_RE.finditer(text):
            out.append(self.render_prose(text[pos:m.start()]))
            out.append(self.render_code_block(m.group(1), m.group(2)))
            pos = m.end()
        out.append(self.render_prose(text[pos:]))
        return "".join(out)

    def render_prose(self, text: str) -> str:
        if not text.strip():
            return ""
        escaped = html.escape(text)
        escaped = re.sub(
            r"`([^`\n]+)`",
            rf'<span style="background-color:{palette.CHAT_RAISED};'
            rf'color:{palette.CHAT_ACCENT};font-family:{_CODE_FONT};">\1</span>',
            escaped,
        )
        escaped = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", escaped)
        escaped = escaped.replace("\n", "<br>")
        return (
            f'<div style="color:{palette.CHAT_TEXT_2};'
            f'line-height:150%;">{escaped}</div>'
        )

    def highlight_lua(self, text: str) -> str:
        out: list[str] = []
        pos = 0
        for m in _LUA_TOKEN_RE.finditer(text):
            out.append(html.escape(text[pos:m.start()]))
            seg = html.escape(m.group(0))
            if m.group(1):
                color = palette.CHAT_SYN_COMMENT
            elif m.group(2):
                color = palette.CHAT_SYN_STRING
            elif m.group(3):
                color = palette.CHAT_SYN_NUMBER
            elif m.group(4):
                color = palette.CHAT_SYN_KEYWORD
            else:
                color = palette.CHAT_SYN_FUNCTION
            out.append(f'<span style="color:{color};">{seg}</span>')
            pos = m.end()
        out.append(html.escape(text[pos:]))
        return "".join(out)

    def render_code_block(self, lang: str, code: str) -> str:
        code = code.rstrip("\n")
        lines = code.split("\n") if code else []
        self._copy_seq += 1
        cid = f"copy{self._copy_seq}"
        self.copy_blocks[cid] = code
        lang_label = html.escape(lang or "code")
        header = (
            '<table width="100%" cellspacing="0" cellpadding="0" style="border-bottom:1px solid '
            f'{palette.CHAT_CODE_BORDER};"><tr>'
            f'<td style="color:{palette.CHAT_CODE_LANG};font-size:11px;padding:10px 12px;">{lang_label}</td>'
            f'<td align="right" style="padding:10px 12px;">'
            f'<a href="x-luas30://copy/{cid}" style="color:{palette.CHAT_TEXT_3};'
            'text-decoration:none;font-size:11px;">Sao chép</a></td></tr></table>'
        )
        rows: list[str] = []
        for n, line in enumerate(lines, 1):
            stripped = line.lstrip(" ")
            indent = "&nbsp;" * (len(line) - len(stripped))
            body = indent + (self.highlight_lua(stripped) if stripped else "&nbsp;")
            rows.append(
                "<tr>"
                f'<td align="right" valign="top" style="color:{palette.CHAT_CODE_GUTTER_TEXT};'
                f'background-color:{palette.CHAT_CODE_GUTTER};'
                f'font-size:12px;padding:1px 7px;font-family:{_CODE_FONT};">'
                f"{n}</td>"
                f'<td valign="top" style="color:{palette.CHAT_SYN_VARIABLE};font-size:12px;'
                f'padding:1px 10px 1px 3px;font-family:{_CODE_FONT};">'
                f"{body}</td></tr>"
            )
        code_table = (
            '<table width="100%" cellspacing="0" cellpadding="0">' + "".join(rows) + "</table>"
        )
        return (
            '<div style="margin:8px 0;">'
            '<table width="100%" cellspacing="0" cellpadding="0" style="'
            f'border:1px solid {palette.CHAT_CODE_BORDER};background-color:{palette.CHAT_CODE_BG};">'
            f'<tr><td style="padding:0;">{header}</td></tr>'
            f'<tr><td style="padding:7px 0;">{code_table}</td></tr>'
            "</table></div>"
        )
