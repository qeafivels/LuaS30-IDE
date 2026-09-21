# LuaS30 Studio Guide

## Layout

Studio uses the VXPEngine chrome (1:1 port in `studio/app/vxpui/`), keeping only
the Lua build/emulator/project/AI core underneath:

```text
CustomTitleBar (31px, frameless) — logo · brand · embedded menu · min/max/close
Home page (QStackedWidget#MainStack page 0) — project cards
Editor page (page 1):
  Toolbar (Run/Stop/Check/Build/Designer)
  ActivityBar (46px rail: Explorer · Search · Console · Chat AI · Cài đặt)
  Explorer ("EXPLORER - <PROJECT>") | Editor tabs + Bottom panel
  StatusBar (path, cursor, Lua 5.1, UTF-8, Spaces: 4, profile, screen, App ID, version)
Modal dialog "THIẾT BỊ · VXPEMU" (Devices + Chat AI panels)
Frameless window "TÀI NGUYÊN · UI DESIGNER" (designer fills it; AssetsView is
the second tab of the designer's left THÀNH PHẦN dock)
```

Facts that are easy to break:

- The window is frameless (`Qt.Window | FramelessWindowHint`, translucent,
  manual 6px edge resize); the menu bar is a real `QMenuBar#MainMenuBar`
  embedded inside `CustomTitleBar` and hidden on the Home page.
- Menu look comes ONLY from `app/vxpui/resources/dark_theme.qss`. The old
  generic `QMenuBar { min-height: 26px }` rules in `app/ui/theme.py` were
  removed on purpose: Qt propagates `min-height` to `::item`, and with
  `APP_STYLE + dark_theme.qss` merged as one sheet every menu item grew to
  36px > the 31px bar, so ALL menus collapsed into an unpainted ">>" overflow.
- Global stylesheet = `APP_STYLE + "\n" + dark_theme.qss` (APP_STYLE keeps
  objectName rules for reused views; dark_theme wins generic selectors).
- Bottom panel is ALWAYS hidden at startup (VXPEngine parity); its remembered
  height/active tab and all splitter sizes persist via
  `workspace_session.json` (`WorkspaceSessionStore`).
- `_enter_editor()` refuses without an open project — Home is the only
  project-less surface; tool tabs (Settings, Project Hub, doctors) live on the
  editor page.
- The workspace splitter has 3 children: project column, editor+console
  column, and the CHAT AI dock (`_build_ai_dock()` →
  `PanelFrame("CHAT AI", show_header=False)` holding `AIChatView`) — a
  VS Code-style right column, toggled by "Công cụ → Chat AI" (Ctrl+Alt+I),
  the title-bar AI button, or `_set_ai_visible()` ("Ask AI" from the console).
  It starts hidden; `_set_ai_visible(True)` guarantees a ~380px width on
  first reveal.
- Editor-region chrome (mockup parity): `_build_editor_page()` puts a 46px
  `QFrame#ActivityBar` rail left of the workspace splitter — Explorer /
  Search / Console / Chat AI buttons on top, Settings at the bottom
  (`QToolButton#ActivityButton`, checked = cyan left indicator). Explorer and
  Search share the left `PanelFrame` whose header title is set dynamically to
  `EXPLORER - <PROJECT>` in `_apply_project()` (reset to `EXPLORER` in
  `_clear_project_chrome()`); the inner `ExplorerPanel` header shows only the
  uppercased project name (elided with `…` on narrow columns, full text in
  its tooltip) plus the new-file/folder/collapse/refresh buttons. Clicking
  the active rail icon hides the column (VS Code semantics); panel state is
  read via `isHidden()`, never `isVisible()`, because child widgets report
  False before the window is shown. Editor tabs carry per-file-type icons
  (`file_tab_icon()` in `app/editor/editor_tabs.py`, colors from
  `app.ui.palette`) and the active tab gets a 2px `@ACCENT` top border via
  the `QTabWidget#EditorTabs QTabBar::tab` rules in `theme.py` (that
  specificity is required to beat the generic `QTabBar::tab` rules appended
  from `dark_theme.qss`). The status bar always shows `UTF-8` and
  `Spaces: 4` badges (they are the first dropped when the window goes
  <1000px wide).
- `AIChatView` renders its own assistant chrome (no PanelFrame header):
  header "AI Agent" + sessions/new/settings/close buttons, a segmented
  Chat / Context / Tools tab bar over a `QStackedWidget`, and on the Chat tab
  a welcome card (avatar, model badge, Vietnamese greeting) with a 2×3 grid
  of quick-action buttons that prefill the prompt — the card and the empty
  transcript swap visibility once a session has messages. A persistent
  "Ngữ cảnh" card (project chip, open-file chip refreshed by a 1.5s timer,
  "Tự động" checkbox = `auto_context`) sits above the rounded composer whose
  footer carries attach / access-mode / model-pill (opens provider settings)
  / cyan send. Context tab = read-only context facts; Tools tab = the
  AI ACTIVITY reasoning-summary frame + agent tool notes. Because
  `dark_theme.qss` sets `QWidget { background:#0F1115 }`, labels placed on
  lighter cards MUST get `background: transparent` in their own QSS rule.
- The device panel is NOT a workspace column: `_build_device_dialog()` packs
  only the THIẾT BỊ · VXPEMU `PanelFrame` (EmulatorView + Project Doctor row)
  into an application-modal `CustomDialog` opened from the "Công cụ" menu
  ("Thiết bị · VXPEmu", Ctrl+Alt+D). The dialog's X hides it
  (`set_close_handler(dialog.hide)`) so the embedded EmulatorView is never
  destroyed. The old `RightWorkspaceColumn` splitter and its
  `workspace.right` session key were removed (session restore guards on
  `len(sizes) != splitter.count()`, so old files simply skip).
- The TÀI NGUYÊN panel is NOT in the left column anymore either:
  `app/vxpui/assets_studio_window.py` defines `AssetsStudioWindow`, a separate
  frameless top-level window (own `CustomTitleBar`, own menu bar
  "Tài nguyên / Thiết kế / Cửa sổ", own `WindowStateController` geometry keys
  under `vxpui/assets_studio/`, 6px edge resize). The UI Designer fills the
  whole window — its own "THÀNH PHẦN" palette is the left column. `AssetsView`
  lives in an application-modal `CustomDialog` picker ("TÀI NGUYÊN · ASSETS",
  opened from the studio window's "Tài nguyên → Chọn / quản lý tài nguyên…",
  Ctrl+Alt+R): pick an image and "Chèn vào giữa màn hình" places it on the
  canvas via `designer.place_project_image()` and hides the dialog; importing
  new files syncs them into the palette immediately
  (`_PickerAssetsView.changed` → `sync_project_assets`) so drag-drop from
  "THÀNH PHẦN" is one step away. The two-tab `QTabWidget` dock that used to
  squeeze this panel was removed — it rendered clipped in the real app. The
  window is opened by the "Công cụ" menu
  ("Tài nguyên · UI Designer", Ctrl+Alt+U) or the toolbar Designer button
  (`_open_designer()` no longer creates a tool tab). Closing the window hides
  it so unsaved designs survive; app exit still auto-saves via `closeEvent`
  reading `self.assets_studio.designer`.

## Explorer

Explorer là filesystem tree thật.

Hỗ trợ:

- expand/collapse folder;
- New File;
- New Folder;
- Rename;
- Delete;
- Open;
- Copy Path;
- Copy Relative Path;
- Reveal in File Explorer;
- Refresh;
- hide/show generated folders.

Ẩn mặc định:

```text
.git
.venv
__pycache__
.idea
.pytest_cache
```

Generated folders có thể ẩn:

```text
build
release
dist
```

## Code Editor

- multi-tab;
- dirty marker;
- save/save as/save all;
- Lua syntax highlighting;
- autocomplete Lua / `engine.*`;
- Find/Replace;
- minimap;
- inline diagnostics;
- Problems;
- Go to Definition;
- project-wide search;
- status line/column.

## Build

Build panel dùng pipeline thật qua `tools/build.py`. Build log được đưa vào bottom panel.

## Emulator

Run action phải mở đúng final VXP vừa build. Build/Run workflow dùng hash để giảm nguy cơ
emulator chạy nhầm artifact cũ.

## Assets

Asset workflow dùng để quản lý resource của project. Với S30+ nên ưu tiên:

- atlas;
- ảnh nhỏ;
- RGB565-friendly art;
- audio ngắn/mono;
- asset reuse.

## UI Designer

Designer tập trung màn hình nhỏ 240×320 (QVGA của Nokia S30+). Bố cục:

```text
[toolbar]  màn hình mới · lưu+xuất Lua · hoàn tác/đi lại · nhập ảnh · nhập âm thanh · hít dính · zoom
[MÀN HÌNH] combo chọn màn hình · [+] tạo mới · [⋮] đổi tên / nhân bản / xoá / mở thư mục
[breadcrumb]
[THÀNH PHẦN]  [canvas 240×320]  [INSPECTOR]  [LỚP · ID]
```

- **Canvas** — khung điện thoại 240×320, kéo-thả thành phần, hít dính căn chỉnh
  (đường xanh = thẳng hàng thành phần, đường vàng = thẳng với khung), zoom tới
  4× bằng `Ctrl +/−` (đặt lại `Ctrl+0`), giữ `Alt` khi kéo để tạm tắt hít dính.
  Khi đang kéo từ palette: khung màn hình sáng lên (nét liền — nơi sẽ nhận thành
  phần), bóng thành phần hiện ở đúng vị trí sắp rơi (nét gạch) kèm nhãn
  `x, y  w×h`. Thả ở đâu thành phần cũng bị kẹp nằm trọn trong khung.
- **Chỉnh sửa kiểu Canva**:
  - *Hoàn tác / đi lại* (`Ctrl+Z` / `Ctrl+Shift+Z` hoặc `Ctrl+Y`) theo từng bước,
    giữ tối đa 60 trạng thái; kéo thả, resize, sửa chữ, khoá lớp… đều vào lịch sử.
  - *Chọn nhiều* bằng khung cao-su (giữ chuột trái kéo trên nền) hoặc `Shift`+click;
    `Ctrl+A` chọn tất cả.
  - *Resize 8 tay nắm* (4 góc + 4 cạnh) — kéo mép nào đổi mép đó, tối thiểu 4px,
    luôn kẹp trong màn hình.
  - *Tinh chỉnh* bằng phím mũi tên (1px, `Shift` = 10px).
  - *Sao chép/dán* (`Ctrl+C` / `Ctrl+V`) — bản dán tự cấp ID duy nhất.
  - *Căn chỉnh / phân bố* trong menu chuột phải: trái/giữa/phải, trên/giữa/dưới
    (1 thành phần thì dóng theo khung màn hình), phân bố đều theo hàng/cột (≥3).
  - *Khoá lớp* (menu chuột phải hoặc nút trong menu) — thành phần bị khoá không
    kéo/resize/nudge/Xoá được, viền chọn thành nét chấm; trạng thái khoá lưu
    xuống `ui_design.json` (khoá `lock`).
  - *Sửa chữ ngay trên canvas* — kích đúp thành phần có chữ (Button/Label/…)
    mở ô nhập tại chỗ, Enter chốt, Escape huỷ.
  - *Kéo vùng nhìn*: giữ `Space` + chuột trái, hoặc con lăn chuột giữa.
  - Nhãn `x, y  w×h` hiện live khi đang kéo di chuyển hoặc resize.
- **THÀNH PHẦN** — 18 loại chia 3 nhóm (GIAO DIỆN / BỐ CỤC / ĐỒ HỌA) + ảnh và
  âm thanh quét từ `assets/` của project. Kéo vào canvas hoặc bấm để thêm.
- **INSPECTOR** — ID, vị trí, kích thước, màu tô, góc xoay, nội dung chữ.
- **LỚP · ID** — thứ tự lớp (trên cùng vẽ sau), đổi ID bằng kích đúp, nhân bản
  (`Ctrl+D`), xoay (`Ctrl+Shift+R`), đưa ra trước / ra sau (`Ctrl+Shift+↑/↓`).
- **Đa màn hình** — màn hình khởi động luôn là `main`, không đổi tên và không
  xoá được.

Tệp do designer ghi:

```text
<project>/.luas30/ui_design.json   nguồn sự thật — mọi màn hình (JSON)
<project>/ui_design.lua            sinh ra khi bấm "Lưu + xuất Lua"
```

`ui_design.lua` chứa cả dữ liệu lẫn bộ vẽ dùng API LuaS30, nên game dùng được ngay:

```lua
local ui = require("ui_design")

function engine.draw()
    ui.draw("main")
end

-- tra cứu thành phần theo ID; hit() dành cho cảm ứng
local item = ui.get("main", "btn_start")
local top = ui.hit("main", touch_x, touch_y)
```

Tài nguyên nhập qua designer được copy vào `assets/` của project (xem
`asset_import.py`) để engine nạp bằng đường dẫn tương đối project.

Giới hạn: `engine` của LuaS30 chỉ vẽ hình chữ nhật trục thẳng, không có phép
xoay. Thành phần có `rot` 90/270 được vẽ với chiều rộng/cao hoán đổi; góc khác
được vẽ như không xoay.

Cỡ icon của designer gom về một chỗ — `icons_compat.ICON` (16px),
`ICON_TOOLBAR` (20px), `BTN` (22px) — theo mật độ của VS Code: hàng palette
24px, hàng LỚP 20px, nút nhỏ 22×22. Pixmap glyph được render đúng cỡ hiển thị,
nên đổi cỡ ở đâu thì phải truyền cỡ đó xuống hàm `icons.icon_*` (render 16px
rồi để Qt phóng lên 20px sẽ ra icon nhoè).

## Settings

Settings nên chứa đường dẫn, target profile và build preferences; project-specific setting
nên ở `project.json`, không hard-code trong Studio.

## About

Top menu **About** có:

- About LuaS30 IDE;
- Environment;
- Credits;
- Paths.

Mục Credits phải đồng bộ với `doc/legal/THIRD_PARTY_NOTICES.md`.


## Theme & palette

Chuẩn thiết kế của Studio lấy từ hộp thoại **Cấu hình MediaTek MRE SDK**
(`studio/app/ui/mediatek_mre_dialog.py` + khối QSS `MREDialog*`): nền slate xanh
đêm (`#07101f` lõm / `#111827` mặt phẳng), viền `#273449`–`#334155`, chữ sáng
`#f8fafc`, accent **cam** `#f59e0b`, bo góc 8–12px, ô nhập cao 34px. Mọi bề mặt
khác của Studio được kéo về cùng bảng màu đó.

### Một nguồn màu duy nhất

```text
studio/app/ui/palette.py      <- nguồn sự thật, khai báo mọi màu
studio/app/ui/theme.py        <- QSS dùng @TOKEN, KHÔNG viết hex trực tiếp
```

`theme.py` viết QSS với placeholder `@TEN_TOKEN`; `_substitute()` thay bằng giá
trị trong `palette.py` ngay lúc import. Token lạ thì **raise lỗi ngay** — cố ý
fail-loud, vì Qt gặp khai báo sai sẽ âm thầm bỏ **toàn bộ** rule đó và giao diện
hỏng mà không có thông báo nào.

Thang nền đi từ lõm ra nổi:

```text
BG_INK -> BG_ALT -> BG_SURFACE -> BG_RAISED -> BG_HOVER -> BG_PRESSED
```

Muốn một vùng "sâu hơn" thì lùi về `BG_INK`, muốn "nổi hơn" thì tiến tới
`BG_PRESSED`. Ô nhập, editor, terminal, canvas dùng `BG_INK`; panel và dialog
dùng `BG_SURFACE`; menu/popup/toolbar dùng `BG_RAISED`.

Bo góc chỉ có **ba** giá trị: 6px (ô điều khiển), 8px (card), 12px (dialog).

### Màu chrome và màu nội dung — không được lẫn

Đây là quy tắc dễ vi phạm nhất khi sửa theme:

- **Màu chrome** là màu của chính IDE (nền, viền, chữ, nút, viền chọn thành
  phần, tay cuộn). Bắt buộc lấy từ `palette.py`.
- **Màu nội dung** là màu của *game* mà Studio đang vẽ hộ hoặc đang mô phỏng.
  Không được theo bảng màu IDE.

Các chỗ là màu nội dung, cố ý nằm ngoài palette:

```text
studio/app/editor/lua_highlighter.py     bảng màu cú pháp Lua
studio/app/views/ui_designer/lua_export.py   bảng màu game (sinh ra Lua)
studio/app/views/ui_designer/items.py    xem trước thành phần trong khung 240x320
studio/app/views/ui_designer/color_button.py  dữ liệu swatch màu
studio/app/views/ui_designer/properties_panel.py  DEFAULT_FILL của thành phần mới
```

Ví dụ cụ thể: `items.C_ACCENT = #007acc` là màu của nút/checkbox/progress/slider
**bên trong khung game**, phải khớp `lua_export.ACCENT`. Viền chọn thành phần,
tay nắm và ô xem trước thả thì dùng accent chrome `palette.ACCENT` (cam). Đổi
`C_ACCENT` sang cam là đổi màu game thật, không phải đổi theme.

Kiểm chứng nhanh quy tắc này: xuất `ui_design.lua` rồi soi màu trong đó — không
được có `#f59e0b`.

Trong `theme.py` và code Python, hex trực tiếp chỉ được phép nằm trong
`palette.py`. Ngoại lệ có chủ ý là bảng màu cú pháp `SYN_*` (giữ bảng VS Code
dark+ để code dễ đọc, đã đối chiếu đủ tương phản trên `BG_INK`).

### Đối tượng do Qt tự tạo

Một số điểm trên giao diện **không** do Studio vẽ ra, nên QSS không chạm tới
được. Ví dụ nút đóng tab: mặc định Qt dùng pixmap chuẩn
`QStyle::SP_TabCloseButton` — một dấu X nền đỏ, xuất hiện kể cả khi không nạp
stylesheet nào. Cách xử lý là **tự sở hữu widget** chứ không tô lại: xem
`StudioTabBar` / `_TabCloseButton` trong `studio/app/editor/editor_tabs.py`, tạo
nút riêng rồi `setTabButton()`, và style qua `QToolButton#TabCloseButton`.

Đừng cố sửa bằng `QTabBar::close-button { background: transparent; }` — nó xoá
được nền đỏ nhưng đồng thời làm mất vùng bấm và làm biến mất glyph.

### Nền của CHÍNH widget, không chỉ của subcontrol

QSS chỉ tô những gì được khai báo. Với widget có subcontrol, rất dễ chỉ style
phần tử con rồi tưởng đã xong:

```css
QHeaderView::section { background: @BG_INK; }   /* chỉ các SECTION có thật */
```

Vùng nằm **sau section cuối** (khi các cột cộng lại hẹp hơn bề rộng bảng) do
chính `QHeaderView` vẽ chứ không phải một `::section`, nên nó rơi về palette mặc
định — vốn là màu SÁNG, vì theme này dùng QSS thuần và **không** đặt dark
palette. Kết quả là một dải trắng bên phải hàng tiêu đề. Phải khai báo thêm nền
cho chính widget:

```css
QHeaderView { background: @BG_INK; border: 0; }
```

Đã gặp đúng lỗi này ở Project Hub: 7 cột cộng lại 1075px trong khi header rộng
1152px, thành dải trắng 77px cao 29px. Cùng họ lỗi nên rà cả `QTabBar`,
`QTableView`, `QTreeView`, `QListWidget`, `QScrollArea`: **nếu chỉ thấy
`::subcontrol` mà không có rule cho chính widget thì gần như chắc chắn còn sót
một vùng nền.**

### Kiểm tra

```text
QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
  py -3.12 -u tools/studio_theme_check.py
```

Thêm `--shots <thư_mục>` để lưu ảnh chụp màn hình, `--static-only` để chỉ chạy
phần kiểm tra tĩnh (không cần Qt).

Bốn nhóm kiểm tra:

- **A. tĩnh** — `theme.py` không còn hex trực tiếp; mọi `@TOKEN` đều giải được;
  bo góc chỉ còn 6/8/12; không còn `color: white|black`; mọi hex trong
  `studio/**/*.py` đều thuộc `palette.hex_set()` trừ danh sách `ALLOWLIST` (có
  ghi lý do cho từng file).
- **B. tương phản WCAG** — 14 cặp chữ/nền đạt tỉ lệ >= 4.5:1.
- **C. render offscreen** — dựng thật `MainWindow` và `MediaTekMREConfigDialog`,
  quét "khối sáng" để phát hiện vùng lọt theme sáng, kiểm tra hình học ô nhập và
  chữ trên nút không bị cắt. Nút `MRESaveButton` màu cam là vùng sáng **cố ý**,
  được khai báo miễn trừ bằng `ignore` rect — đừng nới ngưỡng sáng để né nó.
- **D. nút đóng tab** — nút phải là `_TabCloseButton` của Studio, không còn pixel
  X đỏ mặc định của Qt, và bấm vào phải thật sự đóng tab.

Harness chạy với `LUAS30_APPDATA` / `LUAS30_PROJECTS` trỏ vào sandbox tạm nên
không đụng vào cấu hình thật của người dùng.

`ignore` rect ở phần C khai báo theo **toạ độ logic** (hình học widget), còn
`widget.grab()` trả pixmap ở **độ phân giải thiết bị**: trên màn hình scale 125%
(`devicePixelRatio() = 1.25`), hộp thoại 560x509 cho ra pixmap 700x638. Vì vậy
`light_blocks()` phải quy đổi **cả lưới quét lẫn `ignore`** sang pixel thiết bị — nếu
không, vùng miễn trừ lệch khỏi vùng sáng thật và nút cam bị báo nhầm là rò theme sáng.
Lỗi này chỉ lộ ra khi chạy **thiếu** `QT_QPA_PLATFORM=offscreen` (nền tảng thật đọc mức
scale của hệ điều hành); chạy offscreen thì tỉ lệ là 1.0 nên trông vẫn xanh. Đừng "sửa"
bằng cách nới ngưỡng sáng — đó là bịt mắt guard.

Bộ `tools/validate_*.py` cũng phải xanh: các validator không được hard-code hex
(đó chính là nguồn gây lệch màu), mà phải so với `palette.*`.


## Font icons

LuaS30 Studio does not use emoji as toolbar/menu icons.

Icons are created at runtime from Windows system icon fonts through:

```text
studio/app/ui/icons.py
```

Font preference:

```text
Segoe Fluent Icons
Segoe MDL2 Assets
Segoe UI Symbol (fallback)
```

No icon font file is bundled with or exported from the engine package.

Two layers exist. The chrome (`app/vxpui/icons.py`) asks QtAwesome for
`fa5s.*` glyphs; if QtAwesome is missing or its Font Awesome fonts fail to
load (packaged builds), every name falls back through `_FA5_TO_GLYPH` to the
Segoe glyph renderer above, so title-bar/toolbar buttons are never blank.
`tools/validate_icon_fonts.py` pins: all fa names used in source render
non-null both normally AND with `qta` monkeypatched to `None`, every fallback
key exists in `GLYPHS`, and every `GLYPHS` codepoint is present in a real
system font cmap (per-glyph font selection via `_family_for_char`).


## Compact Workbench 1.7

> Historical: describes the pre-VXPEngine QMainWindow shell (deleted
> `studio/app/ui/main_window.py`). The command/service ownership below still
> applies; only the chrome diagram is obsolete.

The workbench removes duplicate pages and commands.

```text
Menu Bar
Compact Command Center
Activity Bar | Editor / Tool View
             | Integrated Bottom Panel
Status Bar
```

Canonical ownership:

- Activity Bar: Explorer, Search, Assets, UI Designer, Emulator, Settings.
- Bottom Panel: OUTPUT, BUILD, PROBLEMS.
- Run menu: build/emulator execution.
- Tools menu: Project Doctor, clean build and folder utilities, rerun first-run setup.
- First-run setup: ~0.8s after launch (first time or new version) Studio shows
  "Thiết lập LuaS30 IDE lần đầu" with per-component status
  (Đã có / Có thể cài tự động / Cần làm thủ công) and Bỏ qua / Kiểm tra lại /
  Tự động cài đặt buttons. Rerun anytime from Tools menu.
  Backed by `studio/app/services/environment_setup.py`; VC++ runtime installs
  via `tools/install_vc_runtime.py`. Never blocks IDE startup.
- Integrated terminal never autostarts: the shell (cmd.exe / sh) only launches
  when the user opens the TERMINAL panel explicitly.
- About menu: documentation, environment and credits.

The former Dashboard, Projects, Build and standalone Console pages are not part of
the v1.7 workbench because they duplicated existing editor/project/build functions.

### Real execution services

`studio/app/services/build_service.py` invokes `tools/build.py` through QProcess,
streams real compiler/packer output into BUILD and reads the generated sync manifest.

`studio/app/services/emulator_service.py` invokes `tools/run_emulator.py` with the
manifest VXP path and expected SHA-256.

The Emulator view displays the actual VXP artifact/hash/process metadata; it no
longer shows a decorative fake device preview.

On Windows, a successful launch also opens the Nokia 225 Dual SIM shell
(`studio/app/widgets/vxp_emu_window.py`, modeled on VXPEngine's VXPEmu chrome):
the real `VXPEmu.exe` window is found by PID and embedded into the 240×320
screen via Win32 `SetParent` (`studio/app/core/native_window.py`). The shell
provides the MRE keypad, run/stop, loading another `.vxp` (re-hashed and
SHA-verified through the same runner), screenshot, MP4 recording when ffmpeg is
on PATH, portrait/landscape rotation and fullscreen. `tools/run_emulator.py`
launches VXPEmu with `--autostart --testapi --screen-only` (same contract as
VXPEngine), so only the bare 240×320 framebuffer window is embedded — the
emulator's own toolbars and title bar never appear inside the shell.

`Project Doctor` validates project.json, entry script, target profile, RAM/FPS
hints, asset payload and the SHA of the previous build.


## Tabbed Workbench 1.9

> Historical chrome diagram (Activity Bar); the tab model itself — one strip
> for files + tool tabs, focus-instead-of-duplicate — is still what
> `EditorGroupManager` implements inside the editor page.

Studio uses one central editor tab strip for both files and tools, matching the behavior
of VS Code custom/editor tabs more closely.

```text
Activity Bar | Explorer/Search | Editor Tabs
                              |  main.lua
                              |  Project Storage
                              |  Assets
                              |  UI Designer
                              |  Emulator
                              |  Project Doctor
                              |  Runtime Compatibility
                              |  Toolchain Doctor
                              |  Settings
                              |
                              +-- OUTPUT / BUILD / PROBLEMS
```

Selecting an Activity Bar tool focuses its existing tab instead of creating duplicates.
Closing a tool tab releases that view; selecting the tool again recreates it.

The `Tools` top menu contains only features that open persistent tabs. Command-only
utilities such as Clean Build are kept under `Run`, while project/build-folder reveal
commands live under `File` or the Command Palette.

### Project Storage

`Project Storage` is backed by `Documents\LuaS30IDE` and provides real filesystem
operations:

- scan managed projects recursively;
- filter by project/path/App ID;
- create a new project through the engine template;
- import an existing LuaS30 project into managed storage;
- open a project;
- duplicate without generated `build/release` data;
- rename the project folder and `project.json` name;
- delete only verified managed LuaS30 project folders;
- reveal the selected project in the OS file explorer;
- show modified time, disk use, file count and latest VXP artifact.

Switching projects closes only source-file tabs after unsaved-change checks. Tool tabs
remain open and refresh their project context.

## Extensions (tiện ích mở rộng)

Any folder under repo-root `extensions/` that carries an `extension.json` is discovered
at startup by `app/services/extension_service.py`, listed dynamically under the
`Công cụ → Tiện ích mở rộng` menu, and opened as a persistent tool tab
(key `extension:<id>`, restored by the workspace session file).

`Công cụ → Tiện ích mở rộng → Cửa hàng tiện ích mở rộng…` opens the marketplace tab
(key `extensions-market`, also persisted): one card per discovered extension — icon
tile, name, two-line description, `from · version · added` footer and a VS Code-style
state button. Discovery ≠ installation: a card starts with **Cài đặt** (Install);
installing records the id in `<appdata>/config/extensions_installed.json`, flips the
card to **Mở** + **Gỡ cài đặt**, and adds the extension's icon to the left activity
bar (rebuilt by `VxpMainWindow._refresh_activity_extensions`). Clicking an activity
bar icon or an installed card opens the extension tab.
`ExtensionMarketView` lives in `app/views/extension_market_view.py`.

Manifest fields (`extension.json`):

- `id` — must equal the folder name;
- `name`, `version`, `description`, `author`;
- `type` — only `"webview"` is supported today;
- `entry` — relative path to the HTML page, confined to the extension folder;
- `icon` — a `fa5s.*` name (Segoe glyph fallback applies);
- `requiresProject` — defaults to `true`; the tool refuses to open without a project.

Folder layout (reference implementation: `extensions/sprite-sheet/`):

```text
extensions/sprite-sheet/
  extension.json     # manifest above
  ui/index.html      # entry page (plain HTML+JS, loaded via file://)
  SKILLS.md          # optional agent doc — exposed to ChatAI as an on-demand skill
```

`ExtensionHostView` (`app/views/extension_host_view.py`) hosts a `QWebEngineView` with a
QWebChannel bridge registered as `luaS30` plus an injected shim (qwebchannel.js is
reused from the Qt resource, so nothing is bundled). The page gets:

- `window.luaS30Ready` / `luas30-bridge-ready` event — bridge availability;
- `window.luaS30.extension(cb)` — manifest info;
- `window.luaS30.project(cb)` — `{root, name}` of the current project;
- `window.luaS30.notify(message, level)` — status-bar line;
- `window.luaS30.writeFiles(list, cb)` — batch write into the project. Items are
  `{path, text}` or `{path, base64}` (data-URL prefix allowed). Writes are confined
  to the project root, capped at 512 files / 8 MB each, and reject `..`, absolute
  paths and blocked names (`.env`, `.git`, …). The result reports per-file errors,
  and the explorer/asset views refresh after a successful batch.

### ChatAI specialization: the project IS the codebase (read + write confinement), SKILLS, `problems`

**Golden rule (Codex-style target):** LuaS30-IDE is only an editor + MRE compiler +
VXPEmu launcher. The "codebase" the agent reads AND writes is the **project the user
created/opened** (`MainWindow.project_root`, e.g. `Documents\LuaS30 Projects\<name>`),
never the IDE's own install/source tree. Every `luas30-edit` block, recovered fenced
code block and `asset`/`ui_design` write resolves against that project root, so
generated code lands in the created project exactly like Codex commits to a repo.

The agent protocol (`TOOL_NAMES`) exposes `read | grep | glob | ui_design | asset |
skill | problems | run_app`. The agent is **confined to the currently open project on
BOTH sides of the boundary**:
- **Read/grep/glob** paths resolve relative to the project root and stay inside it;
  there is no way to read the LuaS30 IDE's own installation/source tree.
- **Write/apply** is guarded by `AIChangeService._safe_target`
  (`app/services/ai_change_service.py`), which rejects absolute paths, drive letters,
  `..`/symlink escapes, protected names, and any target that fails
  `relative_to(project_root)` — so an AI edit can never escape into the IDE install
  dir. New files are created under the project root (`target.parent.mkdir(...)`);
  existing files are backed up under `<project>/.luas30/ai-backups/<stamp>/` before
  overwrite, and `apply_one` / `discard` give per-file Accept/Revert (Codex-style).

**Plain fenced code → real project file (Codex-style).** Models sometimes ignore the
`luas30-edit` protocol and paste complete source in an ordinary Markdown fence. To
still honor "add the code to the project", `_recover_fenced_files`
(`app/services/ai_agent_protocol.py`) turns a fence whose info-string NAMES a file —
` ```lua path=src/menu.lua `, ` ```json file=data.json `, or a bare ` ```src/conf.lua `
header — into a whole-file `CodeEditAction`, so a NEW file is created in the open
project (recovered blocks are stripped from the visible chat text). The path may also
sit on the block's FIRST BODY LINE (```` ```lua ```` then `path=src/menu.lua` on its own
line, a common model habit); that directive line is detected and removed from the file
content, while a real code line that merely contains `path =` is never mistaken for it. It is a fallback
only: an existing `luas30-edit`/XML edit block wins, a language-only fence with no
path still falls back to the active-file recovery, and a short snippet with no path
creates nothing (no false positives). `_extract_fenced_path` pre-rejects absolute,
drive-letter and `..` paths, and `AIChangeService._safe_target` re-confines on write,
so recovery can never land outside the project. The system prompt tells the model to
put the project-relative path in the fence header when it pastes full files.
Validator: `tools/validate_ai_fenced_files.py`.

The old separate `engine` tool (and its `"scope":"engine"` escape hatch that
let the agent open `templates/`, `sdk/`, `engine/`, `compat/`, `doc/ai/` and
`extensions/`) has been **removed**: `args.scope` is stripped from every call, and a
legacy `{"tool":"engine","args":{"op":…}}` answer from an old model is downgraded by
the parser into a plain project-scoped `read`/`grep`/`glob`. To learn which `engine.*`
APIs are real, the agent reads the project's own `src/engine.lua` (copied into every
new project from the template) or loads a curated skill — never the IDE's C core.

Skills (Cline-style, on-demand): `SkillService`
(`app/services/skill_service.py`) discovers procedure documents with YAML-ish
frontmatter (`name`, `description`) from

```text
<project>/skills/<name>/SKILL.md      (also <project>/.luas30/skills/)
<ide>/doc/ai/skills/<name>/SKILL.md   (also <ide>/skills/)
<extension>/skills/…                  (plus the extension's root SKILLS.md)
```

Only the INDEX (name + description + source) goes into every system prompt as
`<agent_skills>`; the full text is fetched with
`{"tool":"skill","args":{"op":"read","name":"…"}}`. This removed the old
per-turn duplication where every extension `SKILLS.md` was injected in full AND
re-readable through the engine tool. Three starter skills ship with the IDE:
`vxp-build-run`, `s30plus-ui-design`, `problems-autofix` (the old `engine-api-check`
skill was deleted once IDE-internal reading was removed). `/skills` in the chat
composer lists what is discoverable. Project skills win name collisions over IDE
ones. Multiple `luas30-tool` blocks in one answer now run sequentially (all results
return before the conversation continues) instead of only the first one. Always-on
law documents (`SKILLS.md`, `SKILL.md`, `PROMPT.md` at project/engine roots) are
unchanged and still injected in full.

The `problems` tool (`{"tool":"problems","args":{"op":"list"|"count"}}`) reads
the IDE's live PROBLEMS panel: severity, project-relative path, line:column,
message and a numbered code snippet per entry (capped at `ProblemsView.MAX_ITEMS`
rows; `count` reports the true total). Its data lives in the main window, so the
handler is in `AIChatView` and the text comes from
`MainWindow._ai_problems_snapshot` wired through `ai_chat.set_problems_provider`.
The composer's default access mode is now **Edit automatically** (Cline-Act
style): `luas30-edit` blocks are applied straight into the project (with backups
under `.luas30/ai-backups`) and the agent loop continues automatically, so the
recommended fix loop is problems → analyze → edit → re-run problems until clean
→ build (see the `problems-autofix` skill).

The `run_app` tool builds the open project, launches it on VXPEmu in headless
`--screen-only` mode and captures one smoke screenshot (written to
`<project>/build/smoke/run-*.png` by `VxpEmuWindow.capture_to_file`) as visual
evidence, then closes the emulator. It is a genuine **asynchronous** pipeline, so
`AIChatView.request_run_app(...)` keeps the send button in its working/stop state
until `MainWindow._report_ai_run` calls back `on_run_app_finished(...)`; on failure
a red "Lỗi" line is shown and the button reverts (it never auto-loops the model on
error). The agent calls it with `{"tool":"run_app","args":{"op":"run"|"stop"},"reason":…}`
(one per turn), and the user can trigger the exact same flow by typing `/run`
(aliases `/test`, `/chạy`) or the **"Chạy thử game/app"** quick action — Plan mode
refuses to run. Handlers/wiring live in `AIChatView` + `MainWindow` (callback set
via `ai_chat.set_run_app` / `set_run_app_stopper`). Validator:
`tools/validate_ai_run_app.py`.

Every applied edit batch also renders a Cursor-style summary card inside the
chat transcript (`AIChatView._change_card_html`): header "Đã sửa N tệp" with
total `+added / −removed` (green/red, from `PreparedChange.added_lines/
removed_lines` passed by `MainWindow._apply_ai_changes` as `files=`), a
`Review` link that reopens the AI Changes diff tab (last applied set is kept in
`_ai_last_applied` and shown with `mark_applied`), per-file rows, and a
`Hiển thị thêm N tệp` collapse after `CARD_VISIBLE_FILES = 3` rows. Links use
`x-luas30://` hrefs handled by `transcript.anchorClicked`
(`setOpenLinks(False)`), and card history entries (`role:"card"`) are filtered
out of provider request payloads. Validator: `tools/validate_ai_change_card.py`.

After every applied edit batch, `MainWindow._apply_ai_changes` schedules
`ai_chat.report_errors_after_change()` (via `QTimer.singleShot(700, …)`). That is the
Antigravity-style error handoff, now a **live, self-updating card** rather than a
frozen snapshot: `AIChatView` keeps ONE live card (`_live_problem_card`) and matches
problems by **signature** (`_problem_row_sig` = severity + project-relative path +
normalized message — deliberately NOT the line number, which shifts on every edit).
When a problem disappears from the panel it flips to `✓ Đã sửa` (green, struck
through); new problems are appended; the header recounts as `⚠ còn N lỗi cần sửa ·
✓ M đã sửa`, and when everything clears it becomes `✓ Đã sửa hết`. `refresh_problem_card()`
is driven from BOTH `_apply_ai_changes` (via `report_errors_after_change`) and the
editor's `diagnostics_changed` path: `MainWindow._diagnostics_changed` pings a throttled
`_ai_problem_timer` (400ms) → `_refresh_ai_problem_card`, so the transcript card tracks
live fixes typed by the user or agent, not just AI applies. Open problems stay clickable
`x-luas30://openfile/<pb_id>:<idx>` anchors (auto-opens the first still-open one). A new
session resets the live card. Validator: `tools/validate_ai_problem_card_live.py`.

Models that ignore the fenced JSON protocol (Gemini/Ling-style) often emit
native XML calls — `<tool_call=read>` or a bare open tag with
`<arg_key>/<arg_value>` pairs. `parse_agent_response` translates those too
(`_xml_tool_calls`/`_xml_to_actions` in `ai_agent_protocol.py`): aliases
(`read_file`, `search_files`, …), nameless calls inferred from their args
(`path`+`start_line` → read, `pattern` → grep/glob, `op` → skill/problems/…),
legacy `engine` calls downgraded to project-scoped `read`/`grep`/`glob` (with any
`scope` stripped), and `write_file`/`edit_file`
turned into `CodeEditAction`s so edits still flow through the auto-apply
pipeline. Source-valued keys (`content`, `find`, `replace`) keep every byte;
XML blocks are stripped from the visible transcript text. Fenced JSON wins on
duplicates. Validator: `tools/validate_ai_tool_call_xml.py`.

`tools/e2e_chat_ai_agent.py` is the automated agent-loop regression test:
headless, no API key — it stubs `AIRequestThread` with an 8-turn scripted model
that mixes fenced JSON and raw XML calls, then drives the REAL `AIChatView`
loop against a temp project (mirroring `MainWindow`'s prepare/apply wiring).
The agent must produce a screen with button/label/image/textbox/card in
`.luas30/ui_design.json`, a real PNG asset, auto-applied `main.lua` write +
find/replace edits (two "Đã sửa N tệp" cards) and a `problems` read — 14
checks; on failure it prints a per-turn diagnosis of where the agent stopped
interacting with the project.

