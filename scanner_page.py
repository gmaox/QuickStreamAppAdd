import os
import threading
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from scanner_add_page import load_scanners, save_scanners, normalize_scanner
from scanner_manage_page import run_scanner, _load_ignored_targets
from main import find_main_window


def _cc(widget, card_type, title, message, on_result=None, yes_text=None, no_text=None, default_yes=False):
    """通过父级 MainWindow 的 confirm_card 统一显示卡片；找不到主窗口则回退 QMessageBox。"""
    mw = find_main_window(widget)
    if mw is not None:
        return mw.confirm_card(card_type, title, message, yes_text=yes_text, no_text=no_text,
                              default_yes=default_yes, on_result=on_result)
    from PyQt5.QtWidgets import QMessageBox
    if card_type == 'question':
        reply = QMessageBox.question(widget, title, message, QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.Yes if default_yes else QMessageBox.No)
        if on_result:
            on_result(reply == QMessageBox.Yes)
    else:
        fn = {'information': QMessageBox.information, 'warning': QMessageBox.warning,
              'critical': QMessageBox.critical}.get(card_type, QMessageBox.information)
        fn(widget, title, message)
        if on_result:
            on_result(True)
    return None


# 蓝色按钮统一样式（含焦点态，供手柄导航识别）
_BLUE_BTN = (
    "QPushButton {"
    "  background-color: #2E7D9B;"
    "  color: white;"
    "  border: 2px solid transparent;"
    "  border-radius: 5px;"
    "  padding: 6px 12px;"
    "}"
    "QPushButton:hover { background-color: #245A71; }"
    "QPushButton:pressed { background-color: #1C4455; }"
    "QPushButton:focus {"
    "  background-color: #66ccff;"
    "  color: #003344;"
    "  border: 2px solid #ffffff;"
    "}"
    "QPushButton:disabled { background-color: #888888; color: #cccccc; }"
)

_LIST_STYLE = (
    "QListWidget { border: 2px solid #2E7D9B; border-radius: 5px; padding: 5px; }"
    "QListWidget::item:selected { background-color: #2E7D9B; color: white; }"
    "QListWidget::item:focus { background-color: #66ccff; color: #003344; }"
    "QListWidget:focus { border: 2px solid #66ccff; }"
)


class ScannerPage(QtWidgets.QWidget):
    """扫描器统一管理页：左列表 + 右详情面板 + 顶部按钮。"""

    scan_log = QtCore.pyqtSignal(str)
    scan_finished = QtCore.pyqtSignal(object)
    scanners_changed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._current_id = None  # 当前编辑的扫描器 id；None 表示新建态
        self._last_auto_name = ""
        self._loading_form = False  # 防止加载表单时触发自动联动
        self._run_buttons = []
        self._setup_ui()
        self.scan_log.connect(self._append_log)
        self.scan_finished.connect(self._on_scan_finished)
        self.reload_scanners()

    # ------------------------------------------------------------------ UI
    def _setup_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # 顶部按钮栏
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)

        self.run_one_btn = QtWidgets.QPushButton(self.tr("测试此扫描器"))
        self.run_one_btn.setStyleSheet(_BLUE_BTN)
        self.run_one_btn.clicked.connect(self._on_run_one)
        top.addWidget(self.run_one_btn)

        self.run_all_btn = QtWidgets.QPushButton(self.tr("测试启用的扫描器"))
        self.run_all_btn.setStyleSheet(_BLUE_BTN)
        self.run_all_btn.clicked.connect(self._on_run_all)
        top.addWidget(self.run_all_btn)

        self.new_btn = QtWidgets.QPushButton(self.tr("新建扫描器"))
        self.new_btn.setStyleSheet(_BLUE_BTN)
        self.new_btn.clicked.connect(self._on_new)
        top.addWidget(self.new_btn)

        self._run_buttons = [self.run_one_btn, self.run_all_btn]

        top.addStretch()
        root.addLayout(top)

        # 主区域：左列表 + 右详情
        main = QtWidgets.QHBoxLayout()
        main.setSpacing(10)

        # 左列表
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setFixedWidth(220)
        self.list_widget.setStyleSheet(_LIST_STYLE)
        # 选中即加载到右详情；A 键（itemActivated）切换启用状态
        self.list_widget.itemSelectionChanged.connect(self._on_list_selection_changed)
        self.list_widget.itemActivated.connect(self._on_list_item_activated)
        main.addWidget(self.list_widget)

        # 右详情面板：用 QStackedWidget 在「编辑表单」与「模板选择」两页间切换
        self.right_stack = QtWidgets.QStackedWidget()
        main.addWidget(self.right_stack, 1)

        # ---------- 页 0：编辑表单 ----------
        edit_page = QtWidgets.QWidget()
        right_box = QtWidgets.QVBoxLayout(edit_page)
        right_box.setContentsMargins(8, 8, 8, 8)
        right_box.setSpacing(8)

        self.form = QtWidgets.QFormLayout()
        form = self.form
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText(self.tr("扫描器名称，例如 Steam 库"))
        form.addRow(self.tr("名称："), self.name_input)

        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItem(self.tr("Steam 库"), "steam")
        self.type_combo.addItem(self.tr("Epic 清单"), "epic")
        self.type_combo.addItem(self.tr("模拟器游戏文件"), "rom")
        self.type_combo.addItem(self.tr("文件夹exe扫描"), "custom")
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow(self.tr("类型："), self.type_combo)

        source_row = QtWidgets.QHBoxLayout()
        self.source_input = QtWidgets.QLineEdit()
        self.source_input.setPlaceholderText(self.tr("留空则自动检测"))
        self.source_input.textChanged.connect(self._on_source_changed)
        source_row.addWidget(self.source_input, 1)
        source_btn = QtWidgets.QPushButton(self.tr("浏览"))
        source_btn.clicked.connect(self._browse_source)
        source_row.addWidget(source_btn)
        form.addRow(self.tr("源路径："), source_row)

        self.enabled_chk = QtWidgets.QCheckBox(self.tr("启用"))
        self.enabled_chk.setChecked(True)
        form.addRow("", self.enabled_chk)

        self.recursive_chk = QtWidgets.QCheckBox(self.tr("递归扫描子文件夹"))
        self.recursive_chk.setChecked(True)
        form.addRow("", self.recursive_chk)

        self.hidden_chk = QtWidgets.QCheckBox(self.tr("包含隐藏文件"))
        self.hidden_chk.setChecked(False)
        form.addRow("", self.hidden_chk)

        emu_row_widget = QtWidgets.QWidget()
        emu_row = QtWidgets.QHBoxLayout(emu_row_widget)
        emu_row.setContentsMargins(0, 0, 0, 0)
        emu_row.setSpacing(6)
        self.emulator_input = QtWidgets.QLineEdit()
        self.emulator_input.setPlaceholderText(self.tr("仅限 ROM 类型：模拟器可执行文件路径"))
        emu_row.addWidget(self.emulator_input, 1)
        self._emu_browse_btn = QtWidgets.QPushButton(self.tr("浏览"))
        self._emu_browse_btn.clicked.connect(self._browse_emulator)
        emu_row.addWidget(self._emu_browse_btn)
        form.addRow(self.tr("模拟器："), emu_row_widget)
        self._emu_row_widget = emu_row_widget

        args_row_widget = QtWidgets.QWidget()
        args_row = QtWidgets.QHBoxLayout(args_row_widget)
        args_row.setContentsMargins(0, 0, 0, 0)
        args_row.setSpacing(6)
        self.args_input = QtWidgets.QLineEdit("{rom}")
        self.args_input.setPlaceholderText(self.tr("参数模板，使用 {rom} 占位符"))
        args_row.addWidget(self.args_input, 1)
        self._args_tpl_btn = QtWidgets.QPushButton(self.tr("模板"))
        self._args_tpl_btn.clicked.connect(self._show_args_template)
        args_row.addWidget(self._args_tpl_btn)
        form.addRow(self.tr("参数："), args_row_widget)
        self._args_row_widget = args_row_widget

        self.rom_ext_input = QtWidgets.QLineEdit(".zip,.7z,.iso,.cue,.chd")
        self.rom_ext_input.setPlaceholderText(self.tr("ROM 扩展名，逗号分隔"))
        form.addRow(self.tr("ROM 扩展名："), self.rom_ext_input)

        right_box.addLayout(form)

        # 保存 / 删除按钮
        btn_row = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton(self.tr("保存"))
        self.save_btn.setStyleSheet(_BLUE_BTN)
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        self.delete_btn = QtWidgets.QPushButton(self.tr("删除"))
        self.delete_btn.setStyleSheet(_BLUE_BTN)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        right_box.addLayout(btn_row)

        # 状态行 + 日志
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color:#2E7D9B;")
        self.status_label.setWordWrap(True)
        right_box.addWidget(self.status_label)

        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        right_box.addWidget(self.log_text)

        right_box.addStretch()
        self.right_stack.addWidget(edit_page)

        # ---------- 页 1：模板选择 ----------
        self._build_template_page()

        root.addLayout(main, 1)

        # 让所有可交互控件都接收焦点（手柄导航需要）
        for w in self.findChildren(QtWidgets.QWidget):
            if isinstance(w, (QtWidgets.QPushButton, QtWidgets.QLineEdit,
                              QtWidgets.QComboBox, QtWidgets.QCheckBox,
                              QtWidgets.QListWidget)):
                w.setFocusPolicy(Qt.StrongFocus)

    # -------------------------------------------------------------- 列表加载
    def reload_scanners(self, keep_selection_id=None):
        """刷新左列表。keep_selection_id 指定刷新后仍选中的扫描器 id。"""
        prev_id = keep_selection_id
        if prev_id is None and self.list_widget.currentItem() is not None:
            prev_id = self.list_widget.currentItem().data(Qt.UserRole)

        self.list_widget.clear()
        scanners = load_scanners()
        restore_row = 0
        for idx, s in enumerate(scanners):
            name = s.get("name", "") or self.tr("(未命名)")
            enabled = bool(s.get("enabled", True))
            # 用圆点指示启用状态
            label = ("● " if enabled else "○ ") + name
            item = QtWidgets.QListWidgetItem(label)
            item.setData(Qt.UserRole, s.get("id"))
            if not enabled:
                item.setForeground(Qt.gray)
            self.list_widget.addItem(item)
            if prev_id is not None and s.get("id") == prev_id:
                restore_row = idx

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(restore_row)
        else:
            # 无扫描器：进入新建态
            self._current_id = None
            self._clear_form()

    # ----------------------------------------------------------- 列表交互
    def _on_list_selection_changed(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        sid = item.data(Qt.UserRole)
        if sid is None:
            return
        # 找到对应扫描器并加载到表单
        for s in load_scanners():
            if s.get("id") == sid:
                self._load_scanner_to_form(s)
                return

    def _on_list_item_activated(self, item):
        """手柄 A 键 / 双击：切换启用状态（快捷操作）。"""
        sid = item.data(Qt.UserRole)
        if sid is None:
            return
        scanners = load_scanners()
        changed = False
        for s in scanners:
            if s.get("id") == sid:
                s["enabled"] = not bool(s.get("enabled", True))
                changed = True
                break
        if changed:
            save_scanners(scanners)
            self.scanners_changed.emit()
            self.reload_scanners(keep_selection_id=sid)
            self.status_label.setText(self.tr("已切换启用状态。"))

    # ----------------------------------------------------------- 表单加载
    def _load_scanner_to_form(self, scanner):
        self._loading_form = True
        try:
            self._current_id = scanner.get("id")
            self.name_input.setText(scanner.get("name", ""))
            idx = self.type_combo.findData(scanner.get("type", "custom"))
            self.type_combo.setCurrentIndex(idx if idx >= 0 else 3)
            self.source_input.setText(scanner.get("source", ""))
            self.enabled_chk.setChecked(bool(scanner.get("enabled", True)))
            self.recursive_chk.setChecked(bool(scanner.get("recursive", True)))
            self.hidden_chk.setChecked(bool(scanner.get("include_hidden", False)))
            self.emulator_input.setText(scanner.get("emulator_path", ""))
            self.args_input.setText(scanner.get("emulator_args", "{rom}") or "{rom}")
            self.rom_ext_input.setText(scanner.get("rom_extensions", ""))
            self._last_auto_name = ""
        finally:
            self._loading_form = False
        self._update_type_fields()

    def _clear_form(self):
        self._loading_form = True
        try:
            self.name_input.clear()
            self.type_combo.setCurrentIndex(0)
            self.source_input.clear()
            self.enabled_chk.setChecked(True)
            self.recursive_chk.setChecked(True)
            self.hidden_chk.setChecked(False)
            self.emulator_input.clear()
            self.args_input.setText("{rom}")
            self.rom_ext_input.setText(".zip,.7z,.iso,.cue,.chd")
            # 新建态默认填入 Steam 库作为名称，与默认类型保持一致
            default_name = self.tr("Steam 库")
            self.name_input.setText(default_name)
            self._last_auto_name = default_name
        finally:
            self._loading_form = False
        self._update_type_fields()

    # ----------------------------------------------------------- 表单交互
    def _on_type_changed(self):
        if not self._loading_form:
            self._update_type_fields()
            self._auto_fill_name()

    def _on_source_changed(self, _text):
        if self._loading_form:
            return
        current = self.name_input.text().strip()
        if not current or current == self._last_auto_name:
            self._auto_fill_name()

    def _auto_fill_name(self):
        scanner_type = self.type_combo.currentData()
        source = self.source_input.text().strip()
        name = ""
        if scanner_type == "steam":
            name = self.tr("Steam 库")
            if source:
                base = os.path.basename(source.rstrip("\\/"))
                if base:
                    name = self.tr("Steam 库 (%1)").replace('%1', base)
        elif scanner_type == "epic":
            name = self.tr("Epic 清单")
            if source:
                base = os.path.basename(source.rstrip("\\/"))
                if base:
                    name = self.tr("Epic 清单 (%1)").replace('%1', base)
        elif scanner_type == "rom":
            name = os.path.basename(source.rstrip("\\/")) if source else self.tr("xx模拟器配置")
        else:
            name = os.path.basename(source.rstrip("\\/")) if source else self.tr("自定义文件夹")

        current = self.name_input.text().strip()
        if name and (not current or current == self._last_auto_name):
            self.name_input.setText(name)
            self._last_auto_name = name

    def _update_type_fields(self):
        scanner_type = self.type_combo.currentData()
        rom_mode = scanner_type == "rom"
        custom_mode = scanner_type == "custom"

        # ROM/自定义：显示递归+隐藏选项；Steam/Epic：隐藏
        show_recursive = rom_mode or custom_mode
        self._set_form_row_visible(self.recursive_chk, show_recursive)
        self._set_form_row_visible(self.hidden_chk, show_recursive)

        # 仅 ROM：显示模拟器/参数/ROM 扩展名（整行容器同步显隐）
        self._set_form_row_visible(self._emu_row_widget, rom_mode)
        self._set_form_row_visible(self._args_row_widget, rom_mode)
        self._set_form_row_visible(self.rom_ext_input, rom_mode)

        self.emulator_input.setEnabled(rom_mode)
        self.args_input.setEnabled(rom_mode)
        self.rom_ext_input.setEnabled(rom_mode)
        self.recursive_chk.setEnabled(show_recursive)
        self.hidden_chk.setEnabled(show_recursive)

        if scanner_type == "steam":
            self.source_input.setPlaceholderText(self.tr("可选的 Steam 根路径（留空则自动检测）"))
        elif scanner_type == "epic":
            self.source_input.setPlaceholderText(self.tr("可选的 Epic 清单目录（留空则自动检测）"))
        elif scanner_type == "rom":
            self.source_input.setPlaceholderText(self.tr("ROM 目录"))
        else:
            self.source_input.setPlaceholderText(self.tr("要扫描的文件夹，查找 .exe/.lnk/.url"))

        if scanner_type in ("steam", "epic") and not self.source_input.text().strip():
            self.recursive_chk.setChecked(False)

    def _set_form_row_visible(self, field, visible):
        """隐藏/显示 QFormLayout 中某 field 及其关联 label。"""
        field.setVisible(visible)
        label = self.form.labelForField(field)
        if label is not None:
            label.setVisible(visible)

    def _browse_source(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr("选择扫描器源文件夹"))
        if directory:
            self.source_input.setText(os.path.normpath(directory))

    def _browse_emulator(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, self.tr("选择模拟器可执行文件"), "", self.tr("可执行文件 (*.exe);;所有文件 (*.*)")
        )
        if file_path:
            self.emulator_input.setText(os.path.normpath(file_path))

    # 常见模拟器参数模板：名称、参数模板、ROM 扩展名
    EMULATOR_TEMPLATES = [
        ("RetroArch",  '-L cores\\core.dll "{rom}"', ".zip,.7z,.iso,.cue,.chd"),
        ("PCSX2",      '"{rom}"',                     ".iso,.bin,.cue,.chd,.gz"),
        ("Dolphin",    '--exec "{rom}"',              ".iso,.wbfs,.gcm,.ciso,.elf,.dol"),
        ("RPCS3",      '"{rom}"',                     ".pkg,.iso"),
        ("PPSSPP",     '"{rom}"',                     ".iso,.cso,.pbp,.elf"),
        ("Citra",      '"{rom}"',                     ".3ds,.cia,.cci,.3dsx"),
        ("MAME",       '"{rom}"',                     ".zip,.7z"),
        ("mednafen",   '"{rom}"',                     ".cue,.iso,.chd,.pce,.ngc"),
        ("Yuzu",       '"{rom}"',                     ".nsp,.xci,.nsz"),
        ("Ryujinx",    '"{rom}"',                     ".nsp,.xci"),
    ]

    def _build_template_page(self):
        """构建模板选择页（right_stack 的第 1 页）。"""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QtWidgets.QLabel(self.tr("选择模拟器参数模板"))
        font = title.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        title.setFont(font)
        layout.addWidget(title)

        hint = QtWidgets.QLabel(self.tr("选择模拟器以套用对应参数模板和 ROM 扩展名："))
        hint.setStyleSheet("color:#666;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._tpl_table = QtWidgets.QTableWidget(len(self.EMULATOR_TEMPLATES), 3)
        self._tpl_table.setHorizontalHeaderLabels([self.tr("模拟器"), self.tr("参数"), self.tr("ROM 扩展名")])
        self._tpl_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self._tpl_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self._tpl_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self._tpl_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._tpl_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._tpl_table.doubleClicked.connect(self._apply_template)
        for row, (name, args, exts) in enumerate(self.EMULATOR_TEMPLATES):
            self._tpl_table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self._tpl_table.setItem(row, 1, QtWidgets.QTableWidgetItem(args))
            self._tpl_table.setItem(row, 2, QtWidgets.QTableWidgetItem(exts))
        layout.addWidget(self._tpl_table)

        btn_row = QtWidgets.QHBoxLayout()
        apply_btn = QtWidgets.QPushButton(self.tr("套用"))
        apply_btn.setStyleSheet(_BLUE_BTN)
        apply_btn.clicked.connect(self._apply_template)
        back_btn = QtWidgets.QPushButton(self.tr("返回"))
        back_btn.setStyleSheet(_BLUE_BTN)
        back_btn.clicked.connect(lambda: self.right_stack.setCurrentIndex(0))
        btn_row.addStretch()
        btn_row.addWidget(apply_btn)
        btn_row.addWidget(back_btn)
        layout.addLayout(btn_row)

        self.right_stack.addWidget(page)

    def _show_args_template(self):
        """切到模板选择页。"""
        self.right_stack.setCurrentIndex(1)
        self._tpl_table.setFocus()

    def _apply_template(self):
        """套用选中的模板，填入参数和 ROM 扩展名，返回编辑页。"""
        row = self._tpl_table.currentRow()
        if 0 <= row < len(self.EMULATOR_TEMPLATES):
            name, args, exts = self.EMULATOR_TEMPLATES[row]
            self.args_input.setText(args)
            self.rom_ext_input.setText(exts)
            self.status_label.setText(self.tr("已套用模板： %1").replace('%1', name))
        self.right_stack.setCurrentIndex(0)

    # ----------------------------------------------------------- 按钮动作
    def _on_new(self):
        # 先取消列表选中。clearSelection 会触发 itemSelectionChanged，
        # 此时 currentItem 可能仍指向旧项，导致旧数据被重新加载回表单。
        # 因此 clear_form 必须延迟到选中信号处理完毕后执行。
        self.list_widget.clearSelection()
        QtCore.QTimer.singleShot(0, self._do_new_form)

    def _do_new_form(self):
        """新建态：清空表单并填入默认值（与 _clear_form 的默认值一致）。"""
        self._current_id = None
        self._clear_form()
        self.status_label.setText(self.tr("请填写表单后点击保存。"))
        self.name_input.setFocus()

    def _build_scanner(self):
        scanner_type = self.type_combo.currentData()
        name = self.name_input.text().strip()
        source = self.source_input.text().strip()
        emulator_path = self.emulator_input.text().strip()

        if not name:
            raise ValueError(self.tr("扫描器名称是必需的。"))
        if scanner_type in ("rom", "custom") and not source:
            raise ValueError(self.tr("ROM/自定义扫描器需要源文件夹。"))
        if scanner_type == "rom" and not emulator_path:
            raise ValueError(self.tr("xx模拟器配置需要模拟器路径。"))

        data = {
            "name": name,
            "type": scanner_type,
            "source": source,
            "enabled": self.enabled_chk.isChecked(),
            "recursive": self.recursive_chk.isChecked(),
            "include_hidden": self.hidden_chk.isChecked(),
            "emulator_path": emulator_path,
            "emulator_args": self.args_input.text().strip() or "{rom}",
            "rom_extensions": self.rom_ext_input.text().strip(),
        }
        if self._current_id is not None:
            data["id"] = self._current_id
        return normalize_scanner(data)

    def _on_save(self):
        try:
            scanner = self._build_scanner()
        except ValueError as e:
            self.status_label.setText(str(e))
            return

        scanners = load_scanners()
        if self._current_id is None:
            # 新建：检查重复
            key = (scanner.get("type", ""), scanner.get("name", "").lower(),
                   scanner.get("source", "").lower())
            for s in scanners:
                ek = (str(s.get("type", "")), str(s.get("name", "")).strip().lower(),
                      str(s.get("source", "")).strip().lower())
                if ek == key:
                    self.status_label.setText(self.tr("已存在相同类型/名称/源的扫描器。"))
                    return
            scanners.append(scanner)
        else:
            # 更新
            updated = False
            for i, s in enumerate(scanners):
                if s.get("id") == self._current_id:
                    scanners[i] = scanner
                    updated = True
                    break
            if not updated:
                scanners.append(scanner)

        save_scanners(scanners)
        self.scanners_changed.emit()
        self._current_id = scanner.get("id")
        self.reload_scanners(keep_selection_id=self._current_id)
        self.status_label.setText(self.tr("已保存扫描器：%1").replace('%1', scanner.get("name", "")))

    def _on_delete(self):
        if self._current_id is None:
            self.status_label.setText(self.tr("请先在左侧选择要删除的扫描器。"))
            return

        def _do_delete(yes):
            if not yes:
                return
            scanners = load_scanners()
            keep = [s for s in scanners if s.get("id") != self._current_id]
            save_scanners(keep)
            self.scanners_changed.emit()
            self._current_id = None
            self._clear_form()
            self.reload_scanners()
            self.status_label.setText(self.tr("已删除扫描器。"))

        # 确认
        _cc(self, 'question', self.tr("删除扫描器"),
            self.tr("确认删除当前扫描器？"), default_yes=False, on_result=_do_delete)

    # ----------------------------------------------------------- 运行扫描
    def _on_run_one(self):
        if self._current_id is None:
            self.status_label.setText(self.tr("请先在左侧选择要运行的扫描器。"))
            return
        target = None
        for s in load_scanners():
            if s.get("id") == self._current_id:
                target = s
                break
        if target is None:
            return
        self._start_scan([target])

    def _on_run_all(self):
        scanners = [s for s in load_scanners() if s.get("enabled", True)]
        if not scanners:
            self.status_label.setText(self.tr("没有已启用的扫描器可运行。"))
            return
        self._start_scan(scanners)

    def _set_running(self, running):
        self._running = running
        for btn in self._run_buttons:
            btn.setEnabled(not running)

    def _start_scan(self, scanners):
        if self._running:
            self.status_label.setText(self.tr("扫描已在运行中。"))
            return

        self._set_running(True)
        self.scan_log.emit(self.tr("开始为 %1 个扫描器运行扫描...").replace('%1', str(len(scanners))))

        def worker():
            summary = {
                "scanner_count": len(scanners),
                "created": 0, "skipped": 0, "errors": 0,
            }
            all_scanners = load_scanners()
            scanner_map = {s.get("id"): s for s in all_scanners}
            try:
                ignored_targets = _load_ignored_targets()

                for scanner in scanners:
                    sid = scanner.get("id")
                    current = scanner_map.get(sid, scanner)
                    name = current.get("name", "Unnamed")
                    self.scan_log.emit(f"Running scanner: {name}")

                    # 配置页运行只统计数量，不写入工作文件夹（dry_run）
                    created, skipped, errors, note = run_scanner(
                        current, None, ignored_targets,
                        progress_cb=lambda msg: self.scan_log.emit(msg),
                        dry_run=True,
                    )
                    summary["created"] += int(created)
                    summary["skipped"] += int(skipped)
                    summary["errors"] += int(errors)

                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    current["last_run"] = now
                    current["last_result"] = f"Found {created}, Skipped {skipped}, Errors {errors} ({note})"
                    scanner_map[sid] = normalize_scanner(current)
                    self.scan_log.emit(
                        f"{name} finished: found={created}, skipped={skipped}, errors={errors}"
                    )
                save_scanners(list(scanner_map.values()))
            except Exception as e:
                summary["errors"] += 1
                self.scan_log.emit(f"Scan failed: {e}")

            self.scan_finished.emit(summary)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_scan_finished(self, summary):
        self._set_running(False)
        # 刷新列表但保留当前编辑项
        self.reload_scanners(keep_selection_id=self._current_id)

        created = summary.get("created", 0)
        skipped = summary.get("skipped", 0)
        errors = summary.get("errors", 0)
        count = summary.get("scanner_count", 0)
        text = self.tr("测试完成%1个扫描器，扫描到=%2，已跳过=%3，错误=%4")
        text = (text.replace('%1', str(count)).replace('%2', str(created))
                    .replace('%3', str(skipped)).replace('%4', str(errors)))
        self.status_label.setText(text)
        # 通知其他页面（如 add_games）扫描器数据有变动
        self.scanners_changed.emit()

    def _append_log(self, message):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.appendPlainText(f"[{stamp}] {message}")
