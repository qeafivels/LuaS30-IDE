"""
palette.py — Bảng màu DUY NHẤT của LuaS30 Studio.

Chuẩn thiết kế: ĐỒNG BỘ theo UAGet Desktop
(`D:\\UAGet\\uaget\\src\\uaget\\desktop\\styles\\dark.qss`) — nền indigo-navy
`#111122`/`#19192e`, viền `#24243d`–`#303049`, accent cam `#ff8a00`.

Quy ước:
- Mọi màu chrome (nền, viền, chữ, nút, selection) phải lấy từ đây. Không viết
  hex trực tiếp trong `theme.py` hay trong code Python.
  `tools/studio_theme_check.py` kiểm tra điều này.
- Màu cú pháp (SYN_*) là ngoại lệ có chủ ý: giữ bảng VS Code dark+ để code dễ
  đọc.
- Thang nền: INK (chrome sâu) → SURFACE/ALT (editor, nội dung) → RAISED
  (menu, popup) → HOVER → PRESSED.
"""

# ---------------------------------------------------------------- nền (UAGet Desktop)
BG_INK = "#111122"        # activity bar, side bar, title, menu bar — sâu nhất
BG_ALT = "#1c1c33"        # editor mặc định, tab chưa chọn, hàng xen kẽ
BG_SURFACE = "#19192e"    # mặt nội dung chính: panel, card, dialog
BG_RAISED = "#202038"     # menu, popup, command center, card nổi
BG_HOVER = "#23233c"      # hover hàng / nút
BG_PRESSED = "#2c2c4e"    # nút phụ, trạng thái nhấn
BG_SELECT = "#1c2a3b"     # mục đang chọn trong list / menu (UAGet TopTab active)
BG_SELECT_SOFT = "#41415b"  # vùng chọn chữ trong editor

# ---------------------------------------------------------------- viền
BORDER = "#303049"        # viền mảnh, đường phân cách
BORDER_STRONG = "#3a3a56"  # viền ô nhập / nút / khung
BORDER_HOVER = "#575774"  # viền khi hover
SCROLL = "#41415b"        # tay cuộn
SCROLL_HOVER = "#5b5f77"

# ---------------------------------------------------------------- chữ
TEXT = "#f1f2f7"          # tiêu đề, chữ nhấn
TEXT_2 = "#d8dbe7"        # chữ thường
TEXT_3 = "#9ca2bb"        # nhãn
TEXT_4 = "#8b91aa"        # chữ mờ
TEXT_5 = "#9297ad"        # chữ rất mờ, ghi chú nhỏ

# ---------------------------------------------------------------- accent (UAGet cam)
ACCENT = "#ff8a00"
ACCENT_HOVER = "#ff9a22"
ACCENT_LIGHT = "#ffb14d"
ACCENT_DEEP = "#e87a00"
ON_ACCENT = "#1a1a2c"     # chữ trên nền accent

# ---------------------------------------------------------------- status bar
STATUS_BG = "#151527"
STATUS_FG = "#9ca2bb"
STATUS_HOVER = "#24243d"

# ---------------------------------------------------------------- trạng thái
GREEN = "#56c990"
GREEN_LIGHT = "#7bd8ad"
GREEN_BORDER = "#2f6b4f"
RED = "#ff6375"
RED_LIGHT = "#ff8f9a"
RED_DEEP = "#c94b5b"
RED_BORDER = "#6e2f36"
AMBER = "#ff9b32"
AMBER_DEEP = "#5c3a1a"
AMBER_BORDER = "#5c3a1a"
INFO = "#64a7ff"
INFO_BG = "#141b2e"
INFO_BORDER = "#2c4a66"

# ---------------------------------------------------------------- diff (AI review)
DIFF_ADDED_BG = "#1b2b28"      # nền dòng được thêm
DIFF_REMOVED_BG = "#331f27"    # nền dòng bị xoá

# ---------------------------------------------------------------- Chat AI (UAGet Desktop)
# Bảng màu khu vực "AI Agent" — đồng bộ 1:1 với UAGet Desktop (dark.qss +
# chat_area.py). Chrome toàn cục lấy @BG_*/@TEXT_... ở trên; selector
# `AIChat*`/`AIWelcome*`/... lấy @CHAT_.
CHAT_BG = "#19192e"               # nền chính của khung chat (ChatArea)
CHAT_BG_STRONGER = "#18182d"      # header / composer strip / thanh tab (TopBar)
CHAT_SURFACE = "#202039"          # card, tin nhắn, pill model (MessageBubble)
CHAT_PANEL = "#1c1c33"            # panel phụ / input nền (CodeEditorWindow)
CHAT_RAISED = "#272740"           # nút, chip, badge (ModelOptionCard)
CHAT_RAISED_HOVER = "#2c2c4e"     # hover icon trần / nút (ClarifyOption:hover)
CHAT_HOVER = "#1a1a31"            # hover hàng / tab chưa chọn (SessionList:hover)
CHAT_BORDER = "#303049"           # viền chính (ChangeList/EditorTabBar)
CHAT_BORDER_WEAK = "#24243d"      # viền mảnh, phân cách (TitleBar/ActivityBar)
CHAT_TEXT = "#f1f2f7"             # chữ nhấn / tiêu đề (SessionName)
CHAT_TEXT_2 = "#d9dce7"           # chữ nội dung chính (MessagePlainText)
CHAT_TEXT_3 = "#9ca2bb"           # chữ phụ / nhãn mờ (TitleLabel)
CHAT_TEXT_4 = "#5d637c"           # chữ disabled / ghi chú (SessionMeta)
CHAT_ACCENT = "#ff8a00"           # cam nhấn chính
CHAT_ACCENT_HOVER = "#ff9a22"
CHAT_ACCENT_PRESSED = "#e87a00"
CHAT_ACCENT_DEEP = "#3b2a20"      # nền/avatar accent nhạt (tím cam rất tối)
CHAT_ON_ACCENT = "#1a1a2c"        # chữ trên nền cam (DialogBtnPrimary)
CHAT_INPUT = "#15152a"            # nền ô soạn prompt (DialogInput)
CHAT_INPUT_BORDER = "#34345a"     # viền ô soạn prompt (ClarifyOtherInput)
CHAT_TAB_ACTIVE = "#1c2a3b"       # nền tab đang chọn (TopTab[active])
CHAT_ACCESS_BG = "#3b2d32"        # nền pill Full Access (rgba cam 12% trên card)
CHAT_STOP = "#e85d75"             # nút Dừng khi agent chạy (BtnSend spinning)
CHAT_SEND_DISABLED = "#4b566a"    # nền nút Gửi khi rỗng (BtnSend:disabled)
CHAT_ON_SEND_DISABLED = "#8b91aa" # chữ nút Gửi khi rỗng
CHAT_TS = "#b99069"               # timestamp góc phải thẻ tin (MessageTime)
CHAT_AVATAR_USER = "#272743"      # avatar "B" (nền InputBar)
CHAT_SCROLL_THUMB = "#41415b"     # thanh cuộn mảnh
CHAT_SCROLL_THUMB_HOVER = "#5b5f77"
# Khối code trong transcript (render HTML nội bộ, không đụng editor palette):
CHAT_CODE_BG = "#10111a"
CHAT_CODE_BORDER = "#34364b"
CHAT_CODE_GUTTER = "#0d0e16"      # nền cột số dòng
CHAT_CODE_GUTTER_TEXT = "#777d86" # số dòng
CHAT_CODE_LANG = "#858ca4"        # nhãn ngôn ngữ ở header
# 6 màu cú pháp riêng cho code block chat (bảng highlight chat_area.py của UAGet):
CHAT_SYN_KEYWORD = "#ef8fcb"
CHAT_SYN_STRING = "#6bdc91"
CHAT_SYN_NUMBER = "#d7a6ff"
CHAT_SYN_FUNCTION = "#ffad4a"
CHAT_SYN_COMMENT = "#777d86"
CHAT_SYN_VARIABLE = "#d3d7e3"

# ---------------------------------------------------------------- màu cú pháp
# Ngoại lệ có chủ ý — bảng VS Code dark+, KHÔNG đồng bộ theo chrome.
SYN_KEYWORD = "#c586c0"
SYN_STRING = "#ce9178"
SYN_FUNC = "#dcdcaa"
SYN_TYPE = "#4ec9b0"
SYN_VAR = "#9cdcfe"
SYN_NUMBER = "#b5cea8"
SYN_COMMENT = "#6a9955"
SYN_CONST = "#569cd6"

# ---------------------------------------------------------------- UI Designer
DESIGNER_BG_DOT = "#2f2f4d"   # lưới chấm sau khung điện thoại
DESIGNER_FRAME = ACCENT        # khung màn hình + viền thân máy
DESIGNER_BEZEL = "#0d0d1a"     # vỏ máy
GUIDE_ITEM = GREEN             # đường dóng: thẳng hàng thành phần
GUIDE_FRAME = AMBER            # đường dóng: thẳng với khung màn hình


# Tập hợp để kiểm tra "màu lạ" — xem tools/studio_theme_check.py
def values() -> dict[str, str]:
    return {
        name: value
        for name, value in globals().items()
        if name.isupper() and isinstance(value, str) and value.startswith("#")
    }


def hex_set() -> set[str]:
    return {value.lower() for value in values().values()}


def qcolor(token: str, alpha: int | None = None):
    """Tiện dụng: hex -> QColor (kèm alpha tuỳ chọn)."""
    from PySide6.QtGui import QColor

    color = QColor(token)
    if alpha is not None:
        color.setAlpha(alpha)
    return color
