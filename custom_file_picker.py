# -*- coding: utf-8 -*-
"""自制文件选择器：内嵌于主窗口 stacked，支持手柄导航（方向键 + A 确认 + B 返回）。

参照原 Simplenite.py 的 CustomFilePickerDialog 迁移而来，适配当前程序：
- 作为 QWidget 内嵌于主窗口 stacked（参照 SGDB 封面选择器模式）
- 手柄路由由主窗口统一处理：方向键空间导航，A 键发 Return 激活列表项，B 键关闭
- 主题色与全局深色主题一致（#2E7D9B / #66ccff / #2b2b2b）
- 支持 file（选择文件）与 directory（选择目录）两种模式
"""

import os

from PyQt5.QtCore import Qt, pyqtSignal, QFileInfo, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QSizePolicy, QFileIconProvider,
)


class CustomFilePickerDialog(QWidget):
    """自制文件选择器（内嵌模式）。"""

    file_selected = pyqtSignal(str)
    picker_cancelled = pyqtSignal()

    def __init__(self, mode='file', file_types=None, initial_path=None,
                 title=None, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomFilePickerDialog")
        self._mode = 'directory' if mode == 'directory' else 'file'
        # file 模式下的扩展名白名单（小写、带点）；directory 模式忽略
        self._file_types = [e.lower() for e in (file_types or [])]
        if self._mode == 'file' and not self._file_types:
            self._file_types = ['.exe', '.lnk']

        self.current_path = ""
        self.selected_file = None
        self.file_list = []  # [(display_name, full_path, is_dir), ...]
        self.sidebar_items = []  # [(name, path), ...]

        # 系统图标提取：缓存避免重复提取
        self._icon_provider = QFileIconProvider()
        self._icon_cache = {}  # path(lower) -> QIcon

        self.setWindowTitle(title or (self.tr("选择目录") if self._mode == 'directory'
                                       else self.tr("选择文件")))
        self._setup_ui()
        self._build_sidebar()

        start = initial_path
        if not start or not os.path.isdir(start):
            start = self._get_initial_path()
        self._navigate_to(start)

    # ------------------------------------------------------------------ UI
    def _setup_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(10)

        # ---- 左侧边栏 ----
        sidebar = QVBoxLayout()
        sidebar.setSpacing(5)
        sidebar_label = QLabel(self.tr("快速访问"))
        sidebar_label.setStyleSheet("color: #93ffff; font-size: 14px; font-weight: bold;")
        sidebar.addWidget(sidebar_label)

        self.sidebar_list = QListWidget()
        self.sidebar_list.setFocusPolicy(Qt.StrongFocus)
        self.sidebar_list.itemActivated.connect(self._on_sidebar_activated)
        self.sidebar_list.setStyleSheet(self._list_qss())
        sidebar.addWidget(self.sidebar_list)

        # ---- 右侧主区域 ----
        right = QVBoxLayout()
        right.setSpacing(5)

        # 路径栏
        path_row = QHBoxLayout()
        path_lbl = QLabel(self.tr("位置:"))
        path_lbl.setStyleSheet("color: white; font-size: 12px;")
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        path_row.addWidget(path_lbl)
        path_row.addWidget(self.path_display)
        right.addLayout(path_row)

        # 文件列表
        self.file_list_widget = QListWidget()
        self.file_list_widget.setFocusPolicy(Qt.StrongFocus)
        self.file_list_widget.itemActivated.connect(self._on_file_activated)
        self.file_list_widget.setStyleSheet(self._list_qss())
        self.file_list_widget.setIconSize(QSize(20, 20))
        right.addWidget(self.file_list_widget)

        # 选择栏
        sel_row = QHBoxLayout()
        sel_lbl = QLabel(self.tr("选择:"))
        sel_lbl.setStyleSheet("color: white; font-size: 12px;")
        self.selection_display = QLineEdit()
        self.selection_display.setReadOnly(True)
        sel_row.addWidget(sel_lbl)
        sel_row.addWidget(self.selection_display)
        right.addLayout(sel_row)

        # 按钮行
        btns = QHBoxLayout()
        self.up_button = QPushButton(self.tr("⬆ 返回上级"))
        self.up_button.clicked.connect(self._navigate_up)
        btns.addWidget(self.up_button)
        btns.addStretch()

        self.cancel_button = QPushButton(self.tr("取消"))
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        btns.addWidget(self.cancel_button)

        self.confirm_button = QPushButton(self.tr("选择"))
        self.confirm_button.clicked.connect(self._on_select_clicked)
        btns.addWidget(self.confirm_button)
        right.addLayout(btns)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setFixedWidth(200)
        main.addWidget(sidebar_widget)
        main.addLayout(right)

    @staticmethod
    def _list_qss():
        """文件/侧边栏列表样式：选中项蓝底，焦点项叠加青色边框（高可见）。"""
        return (
            "QListWidget { background-color: #404040; color: #ffffff; "
            "border: 1px solid #555555; border-radius: 5px; outline: none; }"
            "QListWidget::item { padding: 6px; border-radius: 3px; margin: 1px; }"
            "QListWidget::item:selected { background-color: #2E7D9B; color: #ffffff; }"
            "QListWidget::item:selected:focus { background-color: #2E7D9B; color: #ffffff; "
            "border: 2px solid #66ccff; }"
            "QListWidget::item:hover { background-color: #444444; }"
        )

    def _get_icon_for_path(self, path, is_dir=False):
        """提取系统关联图标（缓存）：目录用文件夹图标，文件用 .exe 内嵌/快捷方式图标。"""
        if is_dir:
            if 'folder' not in self._icon_cache:
                self._icon_cache['folder'] = self._icon_provider.icon(QFileIconProvider.Folder)
            return self._icon_cache['folder']
        if not path:
            return None
        key = path.lower()
        if key in self._icon_cache:
            return self._icon_cache[key]
        icon = None
        try:
            icon = self._icon_provider.icon(QFileInfo(path))
            if icon is not None:
                pix = icon.pixmap(32, 32)
                if pix.isNull():
                    icon = None
        except Exception:
            icon = None
        if icon is None:
            try:
                alt = QIcon(path)
                if not alt.isNull():
                    icon = alt
            except Exception:
                icon = None
        self._icon_cache[key] = icon
        return icon

    # -------------------------------------------------------------- 侧边栏
    def _build_sidebar(self):
        self.sidebar_items = []
        quick = [
            (self.tr("桌面"), os.path.expanduser("~/Desktop")),
            (self.tr("下载"), os.path.expanduser("~/Downloads")),
            (self.tr("文档"), os.path.expanduser("~/Documents")),
            (self.tr("图片"), os.path.expanduser("~/Pictures")),
        ]
        for name, path in quick:
            if os.path.exists(path):
                self.sidebar_items.append((name, path))
        for drive in self._get_available_drives():
            self.sidebar_items.append((drive, drive + "\\"))
        self._refresh_sidebar()

    @staticmethod
    def _get_available_drives():
        return [f'{l}:' for l in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f'{l}:')]

    def _refresh_sidebar(self):
        self.sidebar_list.clear()
        for name, path in self.sidebar_items:
            it = QListWidgetItem(name)
            it.setData(Qt.UserRole, path)
            self.sidebar_list.addItem(it)

    def _get_initial_path(self):
        for p in (os.path.expanduser("~/Desktop"),
                  os.path.expanduser("~/Documents"),
                  "C:\\Program Files", "C:\\"):
            if os.path.exists(p):
                return p
        return "C:\\"

    # -------------------------------------------------------------- 导航
    def _navigate_to(self, path):
        try:
            if not os.path.exists(path) or not os.path.isdir(path):
                path = self._get_initial_path()
            self.current_path = path
            self.path_display.setText(path)
            # directory 模式默认选中当前目录
            if self._mode == 'directory':
                self.selected_file = path
                self.selection_display.setText(os.path.basename(path.rstrip('\\')) or path)
            else:
                self.selected_file = None
                self.selection_display.setText("")

            self.file_list = []
            try:
                items = os.listdir(path)
            except PermissionError:
                self.file_list_widget.clear()
                it = QListWidgetItem(self.tr("⚠ 无权限访问此目录"))
                self.file_list_widget.addItem(it)
                self.up_button.setEnabled(True)
                return

            # 非根目录：第一项为“返回上级”，激活即跳到父目录
            parent = os.path.dirname(path.rstrip('\\'))
            if parent and parent != path:
                self.file_list.append((self.tr("返回上级"), parent, True))

            dirs, files = [], []
            for name in items:
                full = os.path.join(path, name)
                try:
                    if os.path.isdir(full):
                        dirs.append((name, full, True))
                    else:
                        _, ext = os.path.splitext(name)
                        if self._mode == 'directory':
                            # 目录模式：文件灰显，仅作参考，不可选
                            files.append((name, full, False, False))
                        elif ext.lower() in self._file_types:
                            files.append((name, full, False, True))
                except OSError:
                    pass
            self.file_list.extend(dirs + files)
            self._refresh_file_list()

            self.up_button.setEnabled(bool(parent) and parent != path)
        except Exception as e:
            print(f"文件选择器导航错误: {e}")

    def _refresh_file_list(self):
        self.file_list_widget.clear()
        for entry in self.file_list:
            # entry 可能 3 元素（可选中）或 4 元素（带 selectable 标志）
            if len(entry) == 4:
                display, full, is_dir, selectable = entry
            else:
                display, full, is_dir = entry
                selectable = True
            it = QListWidgetItem(display)
            it.setData(Qt.UserRole, full)
            it.setData(Qt.UserRole + 1, is_dir)
            it.setData(Qt.UserRole + 2, selectable)
            # 系统图标：目录用文件夹图标，文件用关联图标
            icon = self._get_icon_for_path(full, is_dir=is_dir)
            if icon is not None and not icon.isNull():
                it.setIcon(icon)
            if not selectable:
                # 灰显不可选项
                it.setForeground(Qt.gray)
            self.file_list_widget.addItem(it)
        if self.file_list_widget.count() > 0:
            self.file_list_widget.setCurrentRow(0)

    def _navigate_up(self):
        parent = os.path.dirname(self.current_path.rstrip('\\'))
        if parent and parent != self.current_path:
            self._navigate_to(parent)

    # -------------------------------------------------------------- 事件
    def _on_sidebar_activated(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self._navigate_to(path)
            # 从侧边栏跳转后，焦点回到文件列表便于继续浏览
            self._focus_file_list()

    def _on_file_activated(self, item):
        full = item.data(Qt.UserRole)
        is_dir = item.data(Qt.UserRole + 1)
        selectable = item.data(Qt.UserRole + 2)
        if is_dir:
            self._navigate_to(full)
        elif selectable and self._mode == 'file':
            self.selected_file = full
            self.selection_display.setText(os.path.basename(full))
            self._accept()

    def _on_select_clicked(self):
        # directory 模式：确认当前目录
        if self._mode == 'directory':
            self.selected_file = self.current_path
            self._accept()
            return
        # file 模式：若已有选中文件则确认，否则尝试当前列表项
        if self.selected_file:
            self._accept()
            return
        item = self.file_list_widget.currentItem()
        if item is not None:
            is_dir = item.data(Qt.UserRole + 1)
            selectable = item.data(Qt.UserRole + 2)
            if not is_dir and selectable:
                self.selected_file = item.data(Qt.UserRole)
                self._accept()

    def _on_cancel_clicked(self):
        self._reject()

    # -------------------------------------------------------------- 结束
    def _accept(self):
        if self.selected_file:
            self.file_selected.emit(self.selected_file)

    def _reject(self):
        self.picker_cancelled.emit()

    def showEvent(self, event):
        super().showEvent(event)
        # 打开时焦点置于文件/文件夹区域的当前选中项，便于手柄方向键直接操作
        self._focus_file_list()

    def _focus_file_list(self):
        """将焦点设到文件列表并确保有当前项高亮。"""
        if self.file_list_widget.count() > 0 and self.file_list_widget.currentRow() < 0:
            self.file_list_widget.setCurrentRow(0)
        self.file_list_widget.setFocus()
