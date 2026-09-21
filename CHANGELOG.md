# Changelog — LuaS30 IDE

Mọi thay đổi đáng chú ý của IDE, engine và Studio. Dạng tóm tắt
(Keep a Changelog); chi tiết đầy đủ của từng bản nằm trong
[`doc/release/changelog/`](doc/release/changelog/) và
kết quả kiểm tra tương ứng trong [`doc/release/validation/`](doc/release/validation/).

Phiên bản phát hành Studio là `VERSION` (hiện là **1.0.1**); các mốc
1.x bên dưới là dòng tính năng của engine/workbench được giữ nguyên
theo tên tệp tài liệu gốc.

## [1.0.1] — 2026-09-19 · Studio chrome VXPEngine

- Port giao diện VXPEngine 1:1 vào `studio/app/vxpui/`: cửa sổ frameless
  với `CustomTitleBar` (menu bar nhúng), họ `CustomDialog`,
  `WindowStateController`, edge-resize thủ công — lõi Lua giữ nguyên.
- Icon không còn phụ thuộc QtAwesome lúc chạy packaged: fallback glyph
  Segoe MDL2 / Fluent (`app/ui/icons.py` + `app/vxpui/icons.py`).
- Panel THIẾT BỊ · VXPEMU chuyển thành hộp thoại application-modal mở từ
  menu "Công cụ" (Ctrl+Alt+D); đóng = ẩn để EmulatorView không bị phá huỷ.
- `AssetsStudioWindow`: cửa sổ top-level riêng kiểu Photoshop
  (Ctrl+Alt+U) gộp Assets + UI Designer, có title bar/menu/geometry riêng.
- Hộp thoại modal "TÀI NGUYÊN · ASSETS" (Ctrl+Alt+R): chọn ảnh chèn thẳng
  vào canvas hoặc import tệp — palette THÀNH PHẦN đồng bộ ngay để kéo-thả.
- CHAT AI là cột phải của workspace theo đúng mô hình panel Chat của
  VS Code (Ctrl+Alt+I), không còn nằm trong hộp thoại thiết bị.
- `AIChatView` dựng lại theo ảnh mẫu: header "AI Trợ lý", tab đoạn
  Chat/Context/Tools, welcome card + lưới 6 nút hành động nhanh, thẻ
  "Ngữ cảnh" và composer bo góc với pill model + nút gửi cyan.
- Vùng soạn thảo đồng bộ ảnh mẫu: thêm `ActivityBar` 46px bên trái
  (Explorer · Search · Console · Chat AI · Cài đặt), header Explorer
  động "EXPLORER - <TÊN DỰ ÁN>", tab mã có icon theo loại tệp + vạch
  accent cyan trên tab đang mở, status bar thêm badge `UTF-8` và
  `Spaces: 4`.
- Chuẩn tiện ích mở rộng mới: mọi thư mục `extensions/<id>/` có
  `extension.json` được `ExtensionService` tự phát hiện, hiện động trong
  menu "Công cụ → Tiện ích mở rộng", mở thành tab công cụ
  `extension:<id>` (lưu/restore qua workspace session).
- Trang "Cửa hàng tiện ích mở rộng" (`ExtensionMarketView`) dạng card nền
  tối theo ảnh mẫu: ô icon bo góc, tên, mô tả hai dòng, hàng
  "from · version · added"; luồng cài kiểu VS Code — nút "Cài đặt" →
  "Mở"+"Gỡ cài đặt", state lưu `config/extensions_installed.json`, và
  icon tiện ích đã cài xuất hiện trên activity bar trái như VS Code.
- `ExtensionHostView`: host QWebEngineView + cầu nối QWebChannel
  `window.luaS30` (extension/project/notify/writeFiles); ghi tệp bị giới
  hạn trong thư mục dự án, chặn `..`, tên tuyệt đối, tệp bí mật; trang
  nhận sự kiện `luas30-bridge-ready`.
- `sprite-sheet.html` → extension chuẩn đầu tiên
  `extensions/sprite-sheet/` (manifest + `ui/index.html` + `SKILLS.md`),
  bổ sung nút "Ghi vào dự án (PNG + atlas.json)" xuất thẳng sprite vào
  `assets/sprites/` của dự án đang mở.
- ChatAI chuyên Lua S30+ MRE VXP: thêm công cụ đọc-lõi (read/list/glob/grep
  trong templates·sdk·engine·compat·doc/ai·extensions),
  ngữ cảnh nhúng `<installed_extensions>` + `<engine_core>` (ranh giới
  Lua→C thật: `engine.lua` wrapper mỏng quanh bảng `engine` đăng ký trong
  `engine/src/runtime_bridge.c`), SKILLS.md của extension được nạp làm luật
  agent, system prompt yêu cầu kiểm chứng API bằng đường đọc lõi thay vì
  giả định hàm mobile-Lua/love2d.
- Tầng AI Agent dọn trùng lặp + nâng theo hướng Cline, chuyên Lua MRE S30+:
  tool `engine` riêng bị gộp vào read/grep/glob bằng `args.scope="engine"`
  (lời gọi kiểu cũ vẫn được parser tự dịch); SKILLS.md của extension không còn
  nạp toàn văn vào mọi system prompt; một lượt trả lời được phép phát NHIỀU
  khối `luas30-tool` và tất cả chạy lần lượt (trước chỉ chạy tool đầu tiên);
  bản đồ lõi sửa chỗ đăng ký hàm engine về đúng `engine/src/runtime_bridge.c`
  (mảng `luaL_Reg funcs[]` của `luas30_bridge_open`).
- Hệ thống SKILLS mới (`skill_service.py`): skill là tệp `SKILL.md` có
  frontmatter `name`/`description` quét từ `skills/` của project,
  `doc/ai/skills/` của IDE và `skills/` của extension; prompt chỉ mang MỤC LỤC
  `<agent_skills>`, toàn văn nạp theo yêu cầu qua tool `skill`
  (op list|read) — kèm 3 skill trụ cột `vxp-build-run`,
  `s30plus-ui-design`, `problems-autofix` và lệnh `/skills` trong ô chat. Validator mới
  `tools/validate_ai_skills.py`.
- Tool `problems` + mặc định "Edit automatically" (Cline Act):
  `{"tool":"problems","args":{"op":"list"|"count"}}` đọc trực tiếp bảng
  PROBLEMS của IDE (severity, đường dẫn tương đối, dòng:cột, message + snippet
  code) qua provider nối từ `MainWindow._ai_problems_snapshot` sang
  `AIChatView.set_problems_provider`; access mode mặc định nay là
  `edit_auto` — code agent sinh ra tự áp thẳng vào dự án (backup
  `.luas30/ai-backups`), vòng lặp tự tiếp tục sau khi áp, skill
  `problems-autofix` mô tả quy trình full vòng đời sửa lỗi.
- Mỗi đợt áp code của AI in một card tổng hợp kiểu Cline/Cursor ngay trong
  transcript Chat: "Đã sửa N tệp" + tổng `+X −Y` xanh/đỏ, nút **Review** mở lại
  tab AI Changes (kể cả sau khi đã áp — giữ `_ai_last_applied` + `mark_applied`),
  danh sách từng tệp kèm số dòng thêm/bớt, gọn 3 dòng đầu với link
  "Hiển thị thêm N tệp"/"Thu gọn danh sách" (`x-luas30://` anchor trên
  `QTextBrowser`, không lọt vào payload gửi provider). Validator mới
  `tools/validate_ai_change_card.py`.

- Sửa lỗi hiển thị bàn phím vỏ Nokia 225 (`vxp_emu_window.py`): nhãn phím mềm
  không còn bị cắt ("Phím mềm" đầy đủ + tooltip trái/phải, font 8pt, quy tắc
  QSS mới `QPushButton#PhoneKey` bỏ padding rộng thừa), phím điều hướng
  trái/phải có icon chevron (`arrow_left`/`arrow_right` E76B/E76C trong
  `icons.py`) thay vì ô đen rỗng, cột phím rộng 80px (bàn phím 252×186), và
  màn chờ hết cảnh chữ "NOKIA" đè lên "225 DUAL SIM".
- Sửa Chat AI "đứng" khi model không theo protocol: `parse_agent_response`
  nay dịch được tool-call XML gốc kiểu Gemini/Ling (`<tool_call=read>` hoặc
  thẻ trần + cặp `arg_key/arg_value`) — alias tên tool, suy đoán tool từ args
  khi thiếu tên, `engine` cũ hạ cấp thành read/grep/glob TRONG project (mọi
  `scope` bị bỏ), và `write_file`/`edit_file`
  thành `CodeEditAction` nên mã vẫn tự áp thẳng vào dự án như Cline; khối XML
  bị gỡ khỏi chữ hiển thị, value mã nguồn giữ nguyên newline, fenced JSON
  được ưu tiên khi trùng lặp. Validator mới
  `tools/validate_ai_tool_call_xml.py` (12 check).
- E2E tự động cho vòng lặp Chat AI (`tools/e2e_chat_ai_agent.py`, headless,
  không cần API key): 8 lượt model kịch bản xen lẫn fenced JSON + XML được
  phát qua đúng `AIChatView` thật trên dự án tạm — agent phải dựng màn hình
  đủ nút nhấn/label/photo/textbox/card trong `.luas30/ui_design.json`, sinh
  PNG thật, TỰ ÁP 2 đợt sửa `main.lua` (hiện 2 card "Đã sửa N tệp"), đọc
  PROBLEMS và dừng đúng lượt; 14 check, kèm chẩn đoán từng lượt nếu agent
  không tương tác được với dự án.
- `tools/drive_ide_as_user.py` — mô phỏng NGƯỜI DÙNG THẬT trong `VxpMainWindow`
  (appdata/projects tạm, chặn modal SetupDialog): tạo dự án mẫu `DemoApp` qua
  đúng `session.create_project` + `_switch_project`, gõ yêu cầu vào composer
  rồi `send()` thật; chỉ stub lớp mạng bằng kịch bản 8 lượt fenced+XML, còn
  toàn bộ pipeline thật chạy (auto-apply, backup, reload editor, tab AI
  Changes, PROBLEMS) — 14 check + ảnh `build/shots_user_ide/ide_as_user.png`.
- Sửa lỗi THẬT tìm ra nhờ mô phỏng: `AIDiffView` crash
  (`QPlainTextEdit.ExtraSelection` không tồn tại trong PySide6) khi highlight
  dòng thay đổi — chuyển sang `QTextEdit.ExtraSelection`; driver có check hồi
  quy riêng cho lỗi này.
- Sửa Chat AI không tự áp mã (xem [1.0.1] ở trên): đóng gói lại thành công
  `dist/LuaS30IDE-Setup-1.0.1.exe` (duy nhất 1 file, 483 MB, Inno Setup wizard
  + `/SILENT`, SHA-256 kèm theo) — cài đặt im lặng kiểm chứng OK, bản cài mở
  `LuaS30IDE.exe` thật (cửa sổ "LuaS30 IDE", dialog thiết lập lần đầu chạy
  đúng). `build_frozen.py` nay copy `VERSION` vào thư mục frozen: thiếu nó,
  bản đóng băng báo "unknown" và làm nhiễm `setup_state.json`, khiến bản cài
  thật bị hỏi lại thiết lập lần đầu.
- Sửa lỗi giao diện bản đóng gói (nền desktop xuyên qua sidebar trong suốt +
  "Phiên bản unknown"): `LuaS30IDE.spec` có `datas=[]` nên `dark_theme.qss`
  không được bundle — `main._stylesheet()` thiếu tệp này, cửa sổ frameless bật
  `WA_TranslucentBackground` và lộ nền màn hình. Spec nay chèn
  `app/vxpui/resources/dark_theme.qss` vào `datas`, `build_frozen.py` copy
  `VERSION` cạnh exe, và `verify_release.py` thêm chốt chặn bắt buộc tệp qss
  phải có trong stage. Kiểm chứng trên desktop thật: sidebar tối vẽ đúng.
- Sửa UI Designer không hiển thị ảnh do AI tạo (chỉ Panel thủ công hiện, ảnh
  thành placeholder núi, mở lại dự án vẫn hỏng): `DesignerItem.from_dict` chỉ
  tra ảnh trong registry RAM, mà công cụ AI ghi asset + thiết kế thẳng ra đĩa
  rồi — không đăng ký gì. Nay `from_dict` nhận `base_dir` (gốc project) và tự
  `load_image` từ đĩa khi `src` trỏ tới tệp có thật nhưng chưa có trong registry
  (đồng thời đăng ký để palette dùng chung). `set_project` khi cùng project cũng
  `reload_current_screen()` (bỏ qua nếu canvas còn thay đổi chưa lưu), và
  `_apply_ai_changes` gọi designer refresh khi AI vừa ghi `ui_design.json` hoặc
  `assets/`. Thêm 3 check hồi quy vào `ui_designer_check.py`.
- Sửa nút "Dừng" không dừng được khi build/run (hộp thoại kẹt "Đang chạy",
  máy vẫn lag vì compile âm ỉ): `QProcess.kill()` trên Windows chỉ giết tiến
  trình python cha, còn `arm-none-eabi-gcc`/`verify_elf.py`/`VXPEmu.exe` là con
  cháu vẫn giữ tay cầm stdout mở → Qt không phát `finished()`. Thêm
  `kill_process_tree()` (`taskkill /F /T /PID`, POSIX dùng `killpg`) mà
  `BuildService.cancel()` và `EmulatorService.stop()` gọi trước khi `kill()`;
  `stop()` của giả lập thôi `taskkill /IM VXPEmu.exe` toàn cục (tắt nhầm cả
  instance không liên quan) để chuyển sang diệt đúng cây theo PID.
  `LuaRunner.stopped_by_user` phân biệt "Đã dừng" với "thất bại" khi báo kết quả.
- Tối ưu IDE hết giật khi run giả lập: `VxpMainWindow` gom output console vào
  bộ đệm và chỉ repaint console + build log + hộp thoại Run mỗi ~60ms
  (`_flush_console`, thay vì vẽ lại cho TỪNG chunk hàng trăm dòng compile); hộp
  thoại Run giới hạn `setMaximumBlockCount(2000)` để log dài không phình.
- Chat AI hiện "hiệu ứng suy luận" của agent theo ảnh mẫu: mỗi lượt chạy tool
  chèn khối thu gọn `▸ Đã chạy N công cụ` vào transcript (bấm mở ra xem tên tool
  + lý do, giữ nguyên khi chuyển phiên qua `_render_history`), kèm dòng trạng
  thái có icon braille quay `⠿ Đang suy nghĩ… · Bước i` hiện/ẩn theo vòng đời
  agent (`_set_agent_active` bật/tắt `QTimer`, `_set_think_phase` đổi câu theo
  đọc ngữ cảnh · chạy công cụ · soạn code).
- AI Agents luôn trả lời bằng tiếng Việt: `_system_prompt` thêm chỉ dẫn BẮT BUỘC
  dịch `visible_text`, `reasoning_summary` và `reason` của tool sang tiếng Việt,
  đồng thời giữ nguyên mã nguồn, tên hàm/biến, đường dẫn và lệnh shell.
- README: mục "Ghi công" là bảng liệt kê thư viện + nguồn (Python/PSF,
  PySide6·Qt LGPLv3, Lua 5.1.5 MIT-style, GNU Arm Toolchain GPLv3+GCC-exception,
  Unicorn GPLv2, Inno Setup, WiX MS-RL, font Segoe) và KHÔNG tuyên bố bản quyền
  bao trùm. Đã bỏ hẳn câu dẫn "LuaS30 IDE được dựng trên nền rất nhiều dự án…"
  và dòng thông báo `© Qeafivels All rights reserved. · https://qeafivels.com/`
  khỏi README; bản quyền/website giờ chỉ còn ở `LICENSE`, hộp thoại About và
  `doc/legal/THIRD_PARTY_NOTICES.md`. `validate_about_credits.py` cập nhật tương
  ứng: README chỉ cần trỏ `](LICENSE)` và được CHỐT là không chứa lại chuỗi bản
  quyền/website. (Đồng thời dọn nốt khối conflict `<<<<<<< HEAD`/`>>>>>>>` bị commit
  sót từ lần merge `39056b4` — giữ nội dung "Ghi công" phía HEAD.)
- UI Designer nâng cấp chỉnh sửa theo chuẩn Canva: hoàn tác/đi lại theo từng
  bước (`Ctrl+Z`/`Ctrl+Shift+Z`, tối đa 60 trạng thái, chọn lại đúng các thành
  phần cũ), chọn nhiều bằng khung cao-su/`Shift`+click/`Ctrl+A`, resize 8 tay
  nắm (4 góc + 4 cạnh, kẹp trong màn hình, tối thiểu 4px), tinh chỉnh bằng mũi
  tên (1px, `Shift`=10px), sao chép/dán `Ctrl+C`/`Ctrl+V` tự cấp ID duy nhất,
  căn trái/giữa/phải · trên/giữa/dưới + phân bố đều qua menu chuột phải,
  khoá lớp (bỏ kéo/resize/nudge/Xoá, viền chấm, lưu khoá `lock` trong
  `ui_design.json`), sửa chữ tại chỗ bằng kích đúp, pan bằng `Space`+kéo hoặc
  chuột giữa, zoom tới 4× với `Ctrl+0/+/−`, và nhãn `x, y  w×h` trực tiếp khi
  kéo/resize.
- Sửa resolve màu icon, pipeline build UTF-8 và khôi phục đường dẫn
  toolchain (commits 71e0c25, 0cf75b9).
- KHOANH VÙNG AI Agent vào ĐÚNG project đang mở: agent không còn đọc/sửa được
  mã nguồn cài đặt của chính LuaS30 IDE. Đã xoá hẳn tool `engine` và cửa hậu
  `args.scope="engine"` (cùng `ENGINE_ALLOWED_PREFIXES`, `<engine_core>` trong
  context, skill `engine-api-check`); `AIReadOnlyToolService` bỏ mọi `scope`,
  mọi đường dẫn read/grep/glob chỉ resolve theo gốc project và chặn thoát ra
  ngoài; prompt đổi sang "Project scope (STRICT)". Lời gọi `engine` kiểu cũ
  được parser hạ cấp thành read/grep/glob project-scoped. Validator:
  `tools/validate_ai_skills.py` (mục 3–5).
- Sửa AI Agent không thêm được code vào project: trước đây MỘT thao tác `find`
  không khớp làm hỏng cả đợt `prepare()`. Nay `AIChangeService` có
  `EditMatchError` + `_flexible_span` (khớp dòng dung cảm thụt lề/khoảng trắng,
  chỉ khi khớp duy nhất) và bỏ qua mềm từng edit lỗi (vẫn raise với lỗi đường
  dẫn/an toàn), ghi "N edit(s) skipped" vào summary — tệp mới vẫn được tạo.
- Phát hiện lỗi + mở file cần sửa kiểu Antigravity: sau mỗi đợt áp code,
  `MainWindow` gọi `ai_chat.report_errors_after_change()`; `AIChatView` nối
  provider dòng PROBLEMS cấu trúc (`set_problems_rows_provider`) +
  `set_open_location_provider`, dựng thẻ "⚠ N lỗi cần sửa" với mỗi mục là neo
  `x-luas30://openfile/<id>:<idx>` bấm để mở đúng tệp:dòng:cột qua
  `open_location`, và tự mở lỗi đầu tiên. Kiểm chứng live: thẻ render, chỉ
  severity error được ưu tiên, click neo mở đúng tệp. Validator:
  `tools/validate_ai_skills.py` (mục 7).
- Sửa composer Chat AI: dòng `self.prompt.clear()` trước đây kẹt trên cùng dòng
  `return` nên chỉ chạy ở nhánh câu-trống — nay tách dòng riêng để XOÁ HẾT text
  ngay khi bấm Gửi. Đồng thời siết TRẠNG THÁI NÚT send: khi Agent đang chạy, nút
  luôn giữ là nút làm việc (glyph stop + `running`), chỉ hoàn nguyên về send khi
  lượt xong thật (`_response_ready` không còn đặt "Ready" giữa vòng lặp tool) HOẶC
  có LỖI; mỗi lỗi (kết nối/thực hiện, hoặc áp mã vào project thất bại) nay in
  DÒNG LỖI đỏ qua `_append_error_line()` rồi `_set_agent_active(False)` — hết
  cảnh nút kẹt "đang làm việc" mãi. Kiểm chứng live + `drive_ide_as_user.py`,
  `validate_ai_agent_shell.py` đều xanh.
- Chạy thử game/app một phát, cả cho người dùng LẪN AI Agent: thêm tool
  `run_app` (build project → launch VXPEmu `--screen-only` chạy ngầm → chờ khung
  hình ổn định → `VxpEmuWindow.capture_to_file` chụp ảnh khói vào
  `<project>/build/smoke/run-*.png` → tự đóng giả lập). Người dùng gõ `/run`
  (alias `/test`, `/chạy`) hoặc bấm quick-action "Chạy thử game/app"; agent phát
  `{"tool":"run_app","args":{"op":"run"|"stop"}}`. Chuỗi này BẤT ĐỒNG BỘ:
  `request_run_app` giữ nút ở trạng thái làm việc tới khi `MainWindow._report_ai_run`
  gọi lại `on_run_app_finished`; lỗi build/giả lập in dòng LỖI đỏ + hoàn nguyên nút
  (không tự loop model khi fail), Plan mode từ chối chạy. Tài liệu:
  `doc/ai/skills/vxp-build-run/SKILL.md`, `doc/studio/STUDIO_GUIDE.md`. Validator:
  `tools/validate_ai_run_app.py`.
- `run.bat`: bỏ hard-code số phiên bản — banner + log giờ ĐỌC TRỰC TIẾP từ file
  `VERSION` gốc repo (`set /p APP_VERSION`) nên luôn khớp, không phải sửa tay mỗi
  lần bump version.
- Tài liệu nêu rõ nguyên tắc kiểu Codex: "codebase" mà AI đọc VÀ ghi là **project
  mà người dùng tạo/mở** (`Documents\LuaS30 Projects\<name>`), KHÔNG bao giờ là thư
  mục cài đặt LuaS30-IDE (IDE chỉ là trình soạn thảo + biên dịch MRE + launcher
  VXPEmu). Ghi được cưỡng chế bởi `AIChangeService._safe_target` (chối đường dẫn
  tuyệt đối, ổ đĩa, `..`/symlink thoát khỏi gốc, tên được bảo vệ); tệp mới tạo dưới
  gốc project, tệp cũ backup ở `<project>/.luas30/ai-backups/`. Viết ở
  `doc/studio/STUDIO_GUIDE.md`.
- **Ép code fenced trong chat thành tệp dự án** (Codex-style): khi model bỏ qua
  protocol `luas30-edit` và chỉ dán nguồn trong khối Markdown thường, nếu info-string
  CỦA KHỐI khai báo tệp (` ```lua path=src/menu.lua ````, `file=`, hoặc bare
  ` ```src/conf.lua ``) thì `_recover_fenced_files` (`ai_agent_protocol.py`) biến nó
  thành `CodeEditAction` ghi CẢ TỆP MỚI vào project đang mở, và xoá khối code đó khỏi
  văn bản chat. Đây chỉ là fallback: khối `luas30-edit`/XML thắng, fence chỉ ghi ngôn
  ngữ không đường dẫn vẫn rơi về phục hồi theo tệp đang mở, snippet ngắn không đường
  dẫn KHÔNG tạo tệp (tránh nhận nhầm). `_extract_fenced_path` chặn trước tuyệt đối/ổ
  đĩa/`..`, `_safe_target` giam lại lần nữa khi ghi. Prompt bảo model đặt đường dẫn
  tương đối-project trong fence. Validator: `tools/validate_ai_fenced_files.py`.
- **Thẻ lỗi PROBLEM cập nhật realtime trong Chat AI** (thay snapshot tĩnh): trước đây
  mỗi lần áp code lại chèn MỘT thẻ "N lỗi cần sửa" đứng im, sửa xong trạng thái không
  đổi. Nay `AIChatView` giữ MỘT **thẻ sống** (`_live_problem_card`) và khớp lỗi theo
  **chữ ký** (`_problem_row_sig` = severity + đường dẫn tương đối + thông điệp, KHÔNG
  dùng số dòng vì nó nhảy khi sửa). Lỗi biến mất -> `✓ Đã sửa` (xanh, gạch ngang); lỗi
  mới -> thêm vào; header đếm lại `⚠ còn N lỗi · ✓ M đã sửa`; sạch hết -> `✓ Đã sửa hết`.
  `refresh_problem_card()` chạy cả khi áp code (`report_errors_after_change`) LẪN khi
  editor phát `diagnostics_changed`: `MainWindow._diagnostics_changed` mồi
  `_ai_problem_timer` (throttle 400ms) -> `_refresh_ai_problem_card`, nên thẻ bám theo
  cả lỗi người dùng tự sửa, không chỉ lỗi AI sửa. Tool `problems` cũng ghi vào thẻ sống.
  Phiên mới hoàn nguyên thẻ. Validator: `tools/validate_ai_problem_card_live.py`.
- **Bong bóng tin nhắn Chat AI theo kiểu Codex/DuckChat**: `_append_message` trước
  đây chỉ in nhãn trần `<b>You</b>` / `<b>AI` bám sát mép trái dock. Nay mỗi lượt
  là một **thẻ** đúng chất Codex: lời người dùng = bong bóng nền `BG_RAISED` viền
  mảnh **canh phải**, lời trợ lý = khối nội dung **canh trái** có viền trái accent
  mảnh, và phía trên là **header dòng nhỏ** — "BẠN" hoặc `◆ <tên model>` (màu
  accent) để biết model nào đang trả lời. Cột nội dung có khoảng thở
  (`document().setDocumentMargin(12)`) thay vì chữ kẹt mép. Thuần PySide6 (dựng
  HTML trong `QTextBrowser`), không đổi hành vi vòng lặp agent.
- **Sửa AI "không thấy sửa gì": nhận tool-call có THÂN LÀ JSON**: model kiểu
  Ling/Gemini hay bỏ qua fenced `luas30-edit` và phát thẻ
  `tool_call` tên dính thẳng sau tag, thân là JSON (không phải cặp
  `arg_key`), thường quên đóng thẻ — đúng như ảnh: tool-call tên
  `luas30-edit` mang mảng JSON `{path,find,replace}`. Ca `EDIT_RE` (cần fence)
  lẫn `XML_TOOL_RE` (cần `>` + `arg_key` + đóng thẻ) đều bỏ lọt, nên lỗi sửa
  của model không bao giờ được áp. Hàm mới `_recover_json_tool_calls` dùng
  `json.JSONDecoder().raw_decode` (chịu thân nhiều dòng + thẻ không đóng) dịch
  nó thành `CodeEditAction`/`ToolAction` và xoá khỏi văn bản chat. Chỉ nhận khi
  thân mở bằng `[` hoặc `{`; prose nhắc `tool_call` không payload vẫn bỏ qua.
  Chính sách plan/disabled vẫn do view `_edit_policy()` giữ (giống fenced block).
  Validator: `tools/validate_ai_json_toolcall.py`.
- **Khu vực AI Trợ lý khoác giao diện DuckChat (QSS thuần Python)**: thêm nhóm
  token `CHAT_*` vào `palette.py` — nền gần đen (`#0d0d0d`→`#242424`), accent cam
  `#ff6700`, viền `#262626` — rồi trỏ toàn bộ selector `AIChat*`/`AIWelcome*`/
  `AIQuick*`/`AIContext*`/`AIThinking*`/`AIActivity*`/`AIShell*`/`AIAccess*`/
  `AIChanges*`/`AIProvider*`/`AISessionsMenu` trong `theme.py` về `@CHAT_*`
  (bo góc vẫn chỉ 6/8/12, nút gửi pill, badge model font mono); `ai_chat_view.py`
  đổi HTML bong bóng/thẻ/card sang `palette.CHAT_*`, giữ màu trạng thái ngữ nghĩa
  (xanh/đỏ/hổ phách) cho diff·PROBLEM·shell. Chỉ đổi CHROME — cơ chế full access
  (`_edit_policy`/`_shell_policy`/`ACCESS_MODES`/vòng lặp agent) và palette VS
  Code toàn cục giữ nguyên. `studio_theme_check.py` PASS, 19 validator
  `validate_ai_*` PASS.
- **Nâng khu vực AI Trợ lý sát bản DuckChat thật (thẻ tin nhắn + khối code)**: mỗi
  lượt chuyện giờ là một **thẻ bo viền** có **avatar tròn** (người dùng nền
  `CHAT_RAISED` chữ "B" canh phải; trợ lý nền `CHAT_ACCENT_DEEP` dấu ◆ canh trái)
  kèm **tên** "Bạn"/"AI Trợ lý", thay cho khối bong bóng cũ chỉ in nhãn trần.
  `_render_markdown` tách văn bản thường khỏi **fenced code block**: khối code
  render dạng **bảng có cột số dòng** (số mờ canh phải, code thụt đầu dòng bằng
  `&nbsp;`), **tô màu cú pháp Lua** (comment/chuỗi/số/từ khoá qua `_LUA_TOKEN_RE`
  + palette `SYN_*`), và **nút "Sao chép"** neo `x-luas30://copy/<id>` — bấm là
  nội dung vào clipboard (`_copy_blocks` đăng ký khi render, `QApplication.clipboard`).
  Tab "Chat" đang chọn đổi sang **viền cam** (`#AIChatTab:checked` nền trong);
  composer chia **hai hàng**: hàng icon đính kèm/@/{ } + gợi ý "Shift + Enter để
  xuống dòng", hàng pill truy cập/model + **nút "Gửi"** thành pill chữ cam (giữ
  nguyên `objectName=AIChatSendIcon` và dòng `apply_icon(... "stop", 13)` mà
  validator `validate_ai_full_access_stop.py` ghim); **status bar đáy** mới
  "● Ready" trái + tagline "Hỗ trợ lập trình tốt hơn mỗi ngày ♥" phải. Thuần
  PySide6/HTML trong `QTextBrowser` (góc bo của thẻ là giới hạn của QTextBrowser,
  chấp nhận vuông); không đụng vòng lặp agent, `_edit_policy`/`_shell_policy` hay
  palette VS Code toàn cục. `studio_theme_check.py` PASS, 19 `validate_ai_*` PASS.
- **AI Trợ lý theo chuẩn "Modern Dark IDE / AI Coding Assistant"**: bảng `CHAT_*`
  được viết lại đúng spec prompt — nền `#0d1014`, panel `#11151a`, thẻ `#151a21`,
  ô nhập `#131820`, accent `#ff6a00/#ff7a1a/#e95f00`, cùng 20 token mới (trạng
  thái dừng `CHAT_STOP`, nút gửi bị tắt, timestamp, avatar người dùng, thanh cuộn,
  khối code `CHAT_CODE_*` và 6 màu cú pháp `CHAT_SYN_*`). `theme.py`: header
  50px, tab Chat hoạt động nền `#1c1815` viền cam, **thanh cuộn mảnh 6px**
  (thumb `#343c47`), composer bo 10px viền focus cam, pill Full Access **viền cam
  thay vì tô cam**, nút Gửi/Gửi-Dừng có `:pressed` + `:disabled`; `studio_theme_check.py`
  nới tập hợp bán kính cho phép thành 6/8/10/12. Logic tách vào module mới
  `ai_chat_render.py` (`TranscriptHtmlRenderer`: avatar, đầu thẻ kèm **timestamp
  góc phải**, markdown, tô sáng Lua cả lời gọi hàm, khối code có số dòng + "Sao
  chép"), `ai_chat_view.py` thêm **composer tự lớn 86→180px**, **cuộn thông minh**
  (không nhảy xuống nếu người dùng đang đọc lên — hiện nút "↓ Tin nhắn mới"),
  **Esc = dừng agent**, nút Gửi tự tắt khi trống, nhãn/model co giãn responsive
  360/420/480/600 (rút còn icon dưới 430px, tên model có ellipsis). Toàn bộ hợp
  đồng cũ giữ nguyên: `ACCESS_MODES`/chính sách sửa-vỏ, `worker.abort()`, neo
  `x-luas30://{copy,step,review,more,openfile}`, các dòng apply_icon bị validator
  ghim. `studio_theme_check.py` PASS, 19 `validate_ai_*` PASS, render offscreen
  360/420/480/600 không rò theme sáng.
- **Siết đúng thông số spec của prompt "Cursor agent"** (đợt 2, chỉ số đo — không
  đổi kiến trúc): tab Chat cao **42px** chữ 13px (spec 42–46); tiêu đề "AI Trợ lý"
  **18px** (spec typography 18–20); icon header **18px** (spec 18–20); pill model
  cao **42px** (spec 42–44); nút Gửi cao **44px** (spec 44–46); composer đệm trong
  **14px** (spec padding 14, đồng bộ hằng số tự lớn 86→180 sang `pad=32`); đầu
  khối code đệm 10px → cao ~35px (spec 34–38); font code đổi sang chuỗi
  **"JetBrains Mono" → "Cascadia Code" → Consolas** (thay vì Consolas trần) và
  transcript khai báo **"Inter" → "Segoe UI"** theo đúng thứ tự ưu tiên typography
  spec. Kiểm lại bằng `studio_theme_check.py` PASS + 19 `validate_ai_*` PASS +
  render offscreen 360/420/480/600: footer không tràn, send/model không overlap.
- **Tệp AI sửa/tạo tự mở thành tab editor kiểu VS Code**: `main_window.py` thêm
  `_open_ai_touched_tabs(change_set)` — sau `_apply_ai_changes` (cả luồng review
  bấm "Áp" lẫn auto-apply của Edit automatically/Full access qua
  `QTimer.singleShot(0, ...)`) và `_accept_ai_change_file` (accept từng file),
  mọi tệp trong change set được `tabs.open_file` mở tab (tệp đã mở thì nạp lại,
  không sinh tab trùng), nội dung đúng bản after, không dirty, tab cuối mở được
  chọn và focus. Tệp không tồn tại/bị loại bị bỏ qua êm. Smoke offscreen thật
  (dựng VxpMainWindow + dự án tạm + AIChangeService.apply): 7/7 PASS; 19
  `validate_ai_*` PASS.
- **Đồng bộ bảng màu AI Trợ lý theo UAGet Desktop**: toàn bộ token `CHAT_*`
  trong `palette.py` đổi sang đúng scheme indigo-navy + cam của
  `D:\UAGet\uaget\src\uaget\desktop\styles\dark.qss` — nền chat `#19192e`,
  header `#18182d`, card `#202039`, viền `#303049`/`#24243d`, accent
  `#ff8a00` (hover `#ff9a22`, nhấn `#e87a00`), tab đang chọn `#1c2a3b`, nút
  Dừng `#e85d75`, timestamp `#b99069`, send disabled `#4b566a`, code block
  `#10111a` + 6 màu cú pháp theo highlighter `chat_area.py` (`#ef8fcb`,
  `#6bdc91`, `#d7a6ff`, `#ffad4a`, `#777d86`, `#d3d7e3`). Chỉ đổi giá trị
  token — `theme.py`/view không sửa, chrome toàn cục và 3 lớp kích thước
  (42/18/44px) giữ nguyên. Verify: `studio_theme_check` FULL PASS (0 khối
  sáng), 19 `validate_ai_*` PASS, render offscreen 360/480px khớp ảnh tham
  chiếu.
- **Đồng bộ màu UAGet cho TOÀN BỘ IDE + đổi tên "AI Trợ lý" → "AI Agent"**:
  palette toàn cục trong `palette.py` chuyển từ VS Code Dark Modern sang đúng
  scheme UAGet (nền `#111122`/`#19192e`/`#1c1c33`, viền `#24243d`–`#303049`,
  accent cam `#ff8a00` với chữ tối `#1a1a2c`, selection `#1c2a3b`, status bar
  `#151527`); 41 màu chrome cấu trúc trong `app/vxpui/*.py` +
  `resources/dark_theme.qss` được map hàng loạt sang UAGet (giữ nguyên màu cú
  pháp Material Ocean của editor và swatch thẻ dự án `home_page.py`). Chuỗi
  hiển thị "AI Trợ lý"/"LuaS30 AI Assistant" đổi thành "AI Agent"
  (`ai_chat_view.py`, `ai_chat_render.py`, `STUDIO_GUIDE.md`). Verify:
  `studio_theme_check` FULL PASS (WCAG 14/14 với bảng màu mới, 0 khối sáng,
  ảnh render toàn IDE + Project Hub), **57/57 validators** PASS, quét CJK sạch.
- **Thanh cuộn thủ công hiện rõ trong AI Agent**: scrollbar của transcript
  (`QTextEdit#AIChatTranscript`) từ 6px track trong suốt → 10px có nền
  `@CHAT_PANEL` + viền `@CHAT_BORDER_WEAK` (cả trục đứng lẫn ngang), thumb
  `min-height/width` 36→48px dễ bấm-kéo; policy vẫn AsNeeded nên chỉ chiếm
  chỗ khi nội dung tràn. Render offscreen 14 tin dài: scrollbar hiện, kéo được
  (max=1805); pill "↓ Tin nhắn mới" + smart-scroll không đổi hành vi. 19
  `validate_ai_*` + theme check FULL PASS.
- **Bố cục chuyên nghiệp cho menu chọn chế độ truy cập (AI Agent)**:
  `AccessModeOption` nâng hàng 62→64px, icon đặt trong chip bo góc 30×30 căn
  giữa dọc (thay vì lề trên), tiêu đề 13px/600, mô tả 11px tự xuống dòng
  (hết chữ nhỏ mờ 10px), dấu ✓ căn giữa phải; thêm header in hoa "CHẾ ĐỘ
  TRUY CẬP" đầu popup, hàng đang chọn có nền + viền accent nhạt, pill chế độ
  cao 40→42px đồng bộ tab. Render offscreen đã soi ảnh; theme check + 19
  `validate_ai_*` PASS.
- Menu sidebar trang chủ (Trang chủ / Dự án / Tài liệu) căn TRÁI và có tính
  năng thật: QSS mới cho `#SidebarButton`/`#SidebarUtility`/`#SidebarSection`
  (nền trong, padding 10×12, hover đậm, hàng đang chọn nền `#1C2A3B` + vạch
  accent cam trái 3px). "Trang chủ" giờ hiển thị 4 dự án gần nhất với tiêu đề
  "Dự án gần đây" + nút "Xem tất cả →"; "Dự án" mở toàn bộ lưới "Tất cả dự
  án"; "Tài liệu" mở `doc/INDEX.md`. Verify: studio_theme check PASS,
  57/57 validators PASS, render offscreen 2 chế độ đã soi.


## 1.15.0 — AI Workbench v1

- Added AI access selector under the ChatAI prompt.
- Added Ask before changes, Edit automatically, Plan mode and Full access modes.
- Kept sensitive/dangerous shell commands confirmation-gated in Full access.
- Replaced inline provider drawer with a custom AI Provider Settings dialog.
- Added Test Connection, Apply and Save & Close provider actions.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_15_0.md) (+11 mục khác)

## 1.15.0 · Agent Editor Fix — AI Agent Editor Apply Fix

- AI providers that ignore the `luas30-edit` protocol and return a normal fenced source block can now be recovered into an edit proposal for the active project file.
- Generated source no longer has to remain only in the Chat transcript when the request clearly asks to create, fix, update, refactor, or otherwise modify code.
- `Ask before changes` keeps the recovered edit pending for review/apply.
- `Edit automatically` and `Full access` continue through the existing automatic apply pipeline, writing the project file and refreshing any open editor buffer.
- Explanation/review prompts are excluded from fallback recovery to avoid accidental file replacement.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_15_0_AGENT_EDITOR_FIX.md) (+3 mục khác)

## 1.14.0 — AI Agent Activity + Shell

- Added collapsible AI Activity / Reasoning Summary panel.
- Added explicit policy against raw/private chain-of-thought display.
- Added `luas30-summary` response protocol.
- Added `luas30-shell` JSON action protocol.
- Added Shell access modes: Disabled, Ask, Auto Safe.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_14_0.md) (+8 mục khác)

## 1.13.0 — MediaTek MRE Project Wizard

- Replaced the old one-line New Project name prompt with a custom MediaTek MRE SDK modal.
- Added APPNAME, APPVER and VENDOR fields.
- Added screen-resolution preset selection.
- Added MTK6260, MTK6261, MTK6250 and MTK6225 presets.
- Added Heap RAM presets with chipset-specific recommended defaults.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_13_0.md) (+7 mục khác)

## 1.12.0 — Series 30+ High Compatibility

- Added S30+ compatibility profiles: auto, standalone, s30plus-native, nokia225-rm1011.
- Added native MRE SDK layout detection.
- Added ARM GCC high-compatibility MRE compile defines.
- Added native linking against local MRE SDK per*.a libraries and SDK scat.ld.
- Added explicit `vm_main()` application entry.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_12_0.md) (+8 mục khác)

## 1.11.0 — AI Workbench

- Added tab right-click Close / Close Others / Close All Tabs.
- Close All Tabs reaches every editor group.
- Rebuilt workbench as Explorer | center editor | ChatAI.
- Compact Bottom Panel is now center-only.
- Added ChatAI secondary sidebar and Ctrl+Alt+I.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_11_0.md) (+5 mục khác)

## 1.10.3 — Colored Panel / HEX / Unique AppID

- Added semantic colors to Console and Build log output.
- Added colored direct-terminal prompt/output.
- Added HEX tab to Compact Bottom Panel.
- Added 64 KiB paged VXP hex viewer with offset/hex/ASCII columns.
- Run/Emulator automatically loads and selects the exact manifest VXP in HEX.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_3.md) (+5 mục khác)

## 1.10.2 — Direct Integrated Terminal

- Removed the separate terminal command QLineEdit.
- Added `TerminalSurface`, a direct-edit QPlainTextEdit.
- Commands are typed directly after the cwd prompt.
- Protected terminal history from normal edits.
- Added Up/Down command history in the terminal surface.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_2.md) (+6 mục khác)

## 1.10.1 — Compact Bottom Panel

- Bottom Console/Build/Problems/Terminal panel is hidden on every startup.
- Terminal toggle opens/focuses the panel and hides it when invoked again.
- Added top-right Close Panel button.
- Hiding Terminal does not kill its QProcess shell.
- Added compact 145 px default reveal height and 72 px minimum.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_1.md) (+4 mục khác)

## 1.10.0 — Multi-Toolchain MRE Profiles

- Added `tools/toolchain_profiles.py`.
- Added ARM GCC, RVDS/RVCT and ARM ADS1.2 compiler profiles.
- Added `--compiler-profile auto|gcc|rvds|ads12`.
- Added `--entry-symbol` override.
- Added nested toolchain detection for gcc/readelf, armcc/armlink/fromelf and tcc.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_10_0.md) (+9 mục khác)

## 1.9.8 — Startup Screen Setting

- Added Settings -> Startup screen.
- Added Welcome startup mode.
- Added Project Hub startup mode.
- Added Empty Editor startup mode.
- Empty Editor restores project/layout but restores no file, untitled or tool tabs.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_8.md) (+4 mục khác)

## 1.9.7 — MRE GCC Build Fix

- Fixed literal `\n` being written into generated GCC probe C source.
- Fixed the same probe-source bug in `toolchain_doctor.py`.
- Added shared MRE GCC compile/link flag definitions.
- Added `MRE`, `GCC` and `__MRE_COMPILER_GCC__` compile defines.
- Preflight now verifies GCC driver, cc1, assembler and the MRE-style linker path.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_7.md) (+3 mục khác)

## 1.9.6 — Clean Startup Tabs

- Startup/restart no longer reopens source file tabs.
- Startup/restart no longer recreates untitled editor tabs.
- Removed automatic `main.lua` fallback during workspace restore.
- Session save filters file/untitled tabs from startup state.
- Older session files containing document tabs are accepted, but those entries are skipped.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_6.md) (+2 mục khác)

## 1.9.5 — Explorer / Activity Bar Toggles

- Added Workbench Bar Explorer button.
- Added Workbench Bar Activity Bar button.
- `Ctrl+B` toggles Explorer / Primary Side Bar.
- `Ctrl+Alt+A` toggles Activity Bar.
- Both actions are in View and Command Palette.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_5.md) (+2 mục khác)

## 1.9.4 — Project Hub Clean Layout

- Welcome and Project Storage now use a clean full-width central layout.
- Activity Bar is hidden on Project Hub pages.
- Explorer/Search sidebar is hidden on Project Hub pages.
- Find/Replace bar is hidden on Project Hub pages.
- Console/Build/Problems/Terminal bottom panel is hidden on Project Hub pages.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_4.md) (+3 mục khác)

## 1.9.3 — Integrated Terminal / Console

- Added real integrated Terminal based on QProcess.
- Added Console and Terminal toggle actions in View.
- Added top-level Terminal menu with New/Kill/Clear actions.
- Added Ctrl+J panel toggle, Ctrl+Shift+Y Console toggle, Ctrl+` Terminal toggle and
- Bottom panel is hidden by default in a new workspace.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_3.md) (+3 mục khác)

## 1.9.2 — Welcome / Project Hub

- Added VS Code-like `Welcome` startup tab.
- Welcome opens at tab index 0 of editor group 0.
- Added New Project, Open Folder, Import into Storage and Manage Storage start actions.
- Added Recent project list backed by managed Project Storage.
- Added Project Storage count/size/build summary and current-workspace card.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_2.md) (+5 mục khác)

## 1.9.1 — Workspace Session Restore

- Added automatic VS Code-like workspace session persistence.
- Added real multi-group editor workspace with horizontal editor groups.
- Added View → Split Editor Right and Close Editor Group.
- Restores current project, open source/tool/untitled tabs, tab order, active tab and active group.
- Restores editor-group splitter sizes.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_1.md) (+5 mục khác)

## 1.9.0 — Tabbed Workspace + Project Storage

- Removed whole-workspace switching for Assets, Designer, Emulator and Settings.
- Source files and persistent tools now share one closable/movable editor tab strip.
- Added keyed tool tabs so opening a feature focuses the existing instance.
- Added Toolchain Doctor as a real tab backed by `toolchain_doctor.py`.
- Project Doctor and Runtime Compatibility Matrix now open result tabs.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_9_0.md) (+11 mục khác)

## 1.8.4 — Portable ARM GCC Compile Fix

- Fixed portable ARM GCC child backend/DLL lookup on Windows.
- Build process now prepends bundled `arm-gcc/bin` and `arm-none-eabi/bin` to its local PATH.
- Added automatic GCC driver/cc1/assembler compile preflight.
- Added `tools/toolchain_doctor.py`.
- Build failures now include compiler stderr in the raised error message.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_4.md) (+2 mục khác)

## 1.8.3 — Runtime Compatibility Matrix

- Added `compat/runtime_abi_contract.json`.
- Added per-firmware MRE symbol manifests under `compat/mre/`.
- Added host-side runtime compatibility evaluator.
- Matrix rows report native/effective capabilities, selected ABI aliases, activated
- Added JSON, CSV and text matrix reports.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_3.md) (+4 mục khác)

## 1.8.2 — Runtime Compatibility Layer

- Added `ls30_compat_report` and compatibility levels: full/degraded/incompatible.
- Added native-vs-effective capability detection.
- Added conservative same-signature ABI alias resolution and alias hit reporting.
- Added safe fallbacks for graphics helpers, text metrics, resource init, file commit,
- Added software line/fill fallbacks so firmware only needs one basic primitive.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_2.md) (+3 mục khác)

## 1.8.1 — Single VXP

- Removed normal per-device VXP build selection.
- Removed `build_matrix.py`.
- Removed `--profile`, `--imsi` and device-bound application artifact mode from the normal builder.
- Canonical final artifact is always `build/<ProjectName>.vxp`.
- Templates no longer contain `target_profile`.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_1.md) (+5 mục khác)

## 1.8.0 — Release Security

- Added explicit signing modes: dev, device-bound, cert100.
- Added profile-level direct-run signing policy.
- `--release` refuses signing modes that the selected profile does not declare trusted.
- Added VXP structure/trailer inspection and release manifests.
- Added multi-target `build_matrix.py` for separate device-specific artifacts.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_8_0.md) (+7 mục khác)

## 1.7.1 — AI Agent Project Protocol

- Added a mandatory two-file preflight: `doc/ai/SKILL.md`, then `doc/ai/PROMPT.md`.
- Added `doc/ai/README.md` as the AI-agent entry point.
- Agents must inspect the selected target profile and current project template before
- Agents must select `GENERIC_VXP`, `KNOWN_DEVICE_PROFILE` or `NEW_DEVICE_PORT`.
- Target application code is engine-only and should not add external runtime frameworks.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_7_1.md) (+5 mục khác)

## 1.7.0 — Compact Workbench

- Removed duplicate Dashboard, Projects, Build and standalone Console pages.
- Activity Bar now contains only Explorer, Search, Assets, UI Designer, Emulator and Settings.
- Top workbench bar now contains project context + Command Palette only.
- Reduced menu set to File / Edit / View / Run / Tools / About.
- Integrated Output / Build / Problems remains the only log/panel surface.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_7_0.md) (+7 mục khác)

## 1.6.3 — Documentation Layout

- Consolidated all Markdown documentation under `doc/`.
- Kept only root `README.md` outside the documentation tree.
- Replaced the former `docs/` directory with categorized `doc/` subfolders.
- Moved `SKILL.md` and `PROMPT.md` to `doc/ai/`.
- Moved third-party notices to `doc/legal/`.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6_3.md) (+4 mục khác)

## 1.6.2 — Font Icon UI

- Removed emoji/pictogram-style control text from the Studio.
- Added `studio/app/ui/icons.py`.
- Uses Windows system font icons: Segoe Fluent Icons / Segoe MDL2 Assets.
- No font files are bundled.
- Activity Bar, menus, top command bar, Explorer toolbar, Find/Replace and major

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6_2.md) (+3 mục khác)

## 1.6.1 — Documentation & Agent Guide

- Rewrote root README around the current v1.6 Native SDK architecture.
- Added `doc/INDEX.md`.
- Added Quick Start, Architecture, Build VXP, Studio Guide, Device Compatibility,
- Expanded Native SDK documentation.
- Updated Lua API reference with `capabilities()` and `device_info()`.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6_1.md) (+5 mục khác)

## 1.6

- Rebuilt the Explorer as a VS Code-style directory tree.
- Added quick New File/New Folder/Refresh/Collapse controls.
- Added relative path copy, reveal, generated-folder toggle, rename and delete.
- Added `sdk/luas30/` as a project-owned SDK.
- Replaced CoreMRE-facing runtime calls with stable `ls30_*` API calls.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_6.md) (+8 mục khác)

## 1.5 — VS Code-style workspace

- Replaced the wide dashboard/sidebar chrome with a compact VS Code-style workspace.
- Added a top application menu: File, Edit, Selection, View, Go, Run, Terminal, Help, About.
- Added a narrow activity bar for Explorer, Search, Projects, Build, Emulator, Assets, UI Designer, Console and Settings.
- Converted the editor project/search pane to an Explorer-style primary sidebar with hidden internal tabs.
- Reduced oversized headings, rounded dashboard cards and decorative chrome across Studio views.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_5.md) (+5 mục khác)

## 1.4.2

- Added requirement-aware dependency manager.
- `run.bat` no longer downloads/upgrades Python packages on every launch.
- Added automatic offline fallback and explicit `--offline` mode.
- Added `--online`, `--deps-only`, and `--force-deps` launcher modes.
- Added persistent dependency change log and JSON environment state.

→ [Chi tiết](doc/release/changelog/CHANGELOG_1_4_2.md) (+3 mục khác)

## Studio 1.3

- Added Lua 5.1 + LuaS30 `engine.*` autocomplete.
- Added current/project symbol completion.
- Added Find/Replace with match highlighting and wrap-around navigation.
- Added low-overhead source minimap.
- Added dependency-free inline Lua structural diagnostics.

→ [Chi tiết](doc/release/changelog/CHANGELOG_STUDIO_1_3.md) (+6 mục khác)
