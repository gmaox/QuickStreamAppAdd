import os
import threading

import psutil
import win32gui
import win32process
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QFrame, QMessageBox, QDialog, QFileDialog, QCheckBox,
    QSizePolicy
)
from PyQt5.QtGui import QFont, QIcon, QFontMetrics
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
import basic_def
from basic_def import runtomain, add_files_to_work_folder_as_shortcuts, notify_run_error, get_covers_dir
from scanner_add_page import load_scanners
from scanner_manage_page import run_scanner, _load_ignored_targets, _get_work_folder
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


class ElideLabel(QLabel):
    """根据自身宽度自动省略过长文本的 QLabel，避免撑宽列表触发横向滚动。"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text or ""
        self.setMinimumWidth(0)
        self.setTextInteractionFlags(Qt.NoTextInteraction)

    def setText(self, text):
        self._full_text = text or ""
        self._update_elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elide()

    def _update_elide(self):
        fm = self.fontMetrics()
        elided = fm.elidedText(self._full_text, Qt.ElideRight, max(self.width() - 4, 0))
        super().setText(elided)


class ResultList(QListWidget):
    """扫描结果列表：item 宽度始终跟随视口宽度，避免横向滚动。"""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vw = self.viewport().width()
        for i in range(self.count()):
            item = self.item(i)
            hint = item.sizeHint()
            if hint.width() != vw:
                hint.setWidth(vw)
                item.setSizeHint(hint)


class AddGameWindow(QWidget):
    # 子线程通过该信号把扫描结果回传到主线程
    scan_complete_signal = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        # “未扫描到新增应用”显示 5 秒后自动切回 scan 态的定时器
        self._empty_reset_timer = QTimer(self)
        self._empty_reset_timer.setSingleShot(True)
        self._empty_reset_timer.timeout.connect(self._reset_to_scan_state)
        # 连接扫描完成信号到主线程处理函数
        self.scan_complete_signal.connect(self._on_scan_complete)
        # 列表项激活防重入标志：避免鼠标双击时 itemClicked + itemActivated 重复触发
        self._scan_adding_in_progress = False
        self.init_ui()

    def _reset_to_scan_state(self):
        """定时器到期：把底部按钮切回 scan 态。"""
        self._set_scan_button_state("scan")

    def _safe_runtomain(self):
        try:
            runtomain()
        except PermissionError as e:
            notify_run_error(
                self.tr("无法访问 Sunshine 配置目录，可能需要管理员权限。\n\n"
                        "目标路径: %1\n\n"
                        "详情: %2").replace('%1', get_covers_dir()).replace('%2', str(e))
            )
        except OSError as e:
            notify_run_error(
                self.tr("访问 Sunshine 配置路径时出错。\n\n"
                        "目标路径: %1\n\n"
                        "详情: %2").replace('%1', get_covers_dir()).replace('%2', str(e))
            )
        except Exception as e:
            notify_run_error(self.tr("运行失败: %1").replace('%1', str(e)))
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        
        # ========== 左侧：开始添加 ==========
        left_widget = QFrame()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(12, 20, 12, 20)
        left_layout.setSpacing(15)
        
        # 标题
        left_title = QLabel(self.tr("开始添加"))
        left_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        left_layout.addWidget(left_title)

        # 说明文本 - 简介
        left_desc1 = QLabel(self.tr("将您的添加列表（工作文件夹）的游戏添加至Sunshine"))
        left_desc1.setFont(QFont("Segoe UI", 10))
        left_desc1.setWordWrap(True)
        left_layout.addWidget(left_desc1)

        # 说明文本 - 操作步骤
        left_desc2 = QLabel(
            self.tr("1. 点击 \"run\" 解析游戏\n"
                    "2. 等待封面下载完成\n"
                    "3. 点击保存，等待完成提示")
        )
        left_desc2.setFont(QFont("Segoe UI", 10))
        left_desc2.setWordWrap(True)
        left_layout.addWidget(left_desc2)

        # 说明文本 - 备注
        left_desc3 = QLabel(self.tr("封面有误可点击封面重新选择；\"忽略\"可隐藏不想添加的游戏。"))
        left_desc3.setFont(QFont("Segoe UI", 9))
        left_desc3.setWordWrap(True)
        left_layout.addWidget(left_desc3)

        import os

        drag_drop_text = self.tr("（也可拖入游戏启动文件添加，支持拖拽多个文件）")
        # 检查是否为管理员权限
        try:
            is_admin = (os.getuid() == 0)
        except AttributeError:
            # Windows 环境下判断管理员权限
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if is_admin:
            drag_drop_text += self.tr("\n（管理员权限下拖拽可能失效）")

        left_desc5 = QLabel(drag_drop_text)
        left_desc5.setFont(QFont("Segoe UI", 9))
        left_desc5.setWordWrap(True)
        left_layout.addWidget(left_desc5)
        
        # 添加弹性间隔
        left_layout.addStretch()
        
        # Run 按钮
        run_btn = QPushButton("run")
        run_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        run_btn.setFixedHeight(60)
        run_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #2E7D9B;"
            "  color: white;"
            "  border: 2px solid transparent;"
            "  border-radius: 5px;"
            "  padding: 8px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #245A71;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #1C4455;"
            "}"
            "QPushButton:focus {"
            "  background-color: #66ccff;"
            "  color: #003344;"
            "  border: 2px solid #ffffff;"
            "}"
        )
        left_layout.addWidget(run_btn)
        
        left_widget.setLayout(left_layout)
        # 仅保留分割线，不设背景以继承全局主题
        left_widget.setStyleSheet("QFrame { border-right: 1px solid #555555; }")
        # 连接按钮至方法
        run_btn.clicked.connect(self._safe_runtomain)
        
        # ========== 右侧：运作扫描器 ==========
        right_widget = QFrame()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(12, 20, 12, 20)
        right_layout.setSpacing(15)
        
        # 标题 + 右上角悬浮按钮
        right_title = QLabel(self.tr("运作扫描器"))
        right_title.setFont(QFont("Segoe UI", 16, QFont.Bold))

        add_running_btn = QPushButton(self.tr("添加运行中游戏"))
        add_running_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        add_running_btn.setFixedHeight(34)
        add_running_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #2E7D9B;"
            "  color: white;"
            "  border: 2px solid transparent;"
            "  border-radius: 5px;"
            "  padding: 4px 10px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #245A71;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #1C4455;"
            "}"
            "QPushButton:focus {"
            "  background-color: #66ccff;"
            "  color: #003344;"
            "  border: 2px solid #ffffff;"
            "}"
        )
        self.add_running_btn = add_running_btn
        add_running_btn.clicked.connect(self.quick_add_running_game)

        title_layout = QHBoxLayout()
        title_layout.addWidget(right_title)
        title_layout.addStretch()
        title_layout.addWidget(add_running_btn)
        right_layout.addLayout(title_layout)
        
        # 说明文本
        right_desc1 = QLabel(self.tr("扫描器能便捷的添加游戏至添加列表（工作文件夹）。请在「扫描器」页配置扫描器。"))
        right_desc1.setFont(QFont("Segoe UI", 10))
        right_desc1.setWordWrap(True)
        right_layout.addWidget(right_desc1)

        # 自动运行扫描器开关
        autorun_row = QHBoxLayout()
        self.autorun_chk = QCheckBox(self.tr("自动运行扫描器"))
        self.autorun_chk.setChecked(self._load_autorun_setting())
        self.autorun_chk.toggled.connect(self._on_autorun_toggled)
        autorun_row.addWidget(self.autorun_chk)
        autorun_row.addStretch()
        right_layout.addLayout(autorun_row)

        # 扫描结果列表
        self.result_label = QLabel(self.tr("扫描结果："))
        right_layout.addWidget(self.result_label)

        self.scan_result_list = ResultList()
        self.scan_result_list.setMinimumHeight(120)
        # 禁用横向滚动条，避免长名字撑宽列表
        self.scan_result_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scan_result_list.setHorizontalScrollMode(QListWidget.ScrollPerPixel)
        self.scan_result_list.setStyleSheet(
            "QListWidget { border: 2px solid #2E7D9B; border-radius: 5px; padding: 5px; }"
            "QListWidget::item:selected { background-color: #2E7D9B; color: white; }"
            "QListWidget::item:focus { background-color: #66ccff; color: #003344; }"
            "QListWidget:focus { border: 2px solid #66ccff; }"
        )
        right_layout.addWidget(self.scan_result_list)

        right_layout.addStretch()

        # 底部按钮（三态：scan 触发扫描 / 扫描中 禁用 / 全部加入 或 未扫描到新增应用）
        self.scan_btn = QPushButton(self.tr("scan"))
        self.scan_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.scan_btn.setFixedHeight(60)
        self.scan_btn.clicked.connect(self._on_scan_button_clicked)
        right_layout.addWidget(self.scan_btn)
        self._set_scan_button_state("scan")  # 初始为 scan 态

        right_widget.setLayout(right_layout)

        # 添加左右两部分到主布局
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 1)

        self.setLayout(main_layout)

        # 若启用自动运行，启动时自动触发扫描；否则按钮保持 scan 态等待用户点击
        if self.autorun_chk.isChecked():
            QTimer.singleShot(0, self._auto_run_scanners)

    def _load_autorun_setting(self):
        """从配置读取自动运行扫描器开关状态。"""
        try:
            basic_def.load_config()
            return bool(basic_def.autorun_scanner)
        except Exception:
            return False

    def _on_autorun_toggled(self, checked):
        """开关切换：持久化配置，启用时立即触发一次扫描。"""
        try:
            basic_def.autorun_scanner = bool(checked)
            basic_def.save_config()
        except Exception:
            pass
        if checked:
            self._auto_run_scanners()

    def _auto_run_scanners(self):
        """后台运行所有已启用的扫描器（dry-run），只发现不写入，结果填入列表。"""
        scanners = [s for s in load_scanners() if s.get("enabled", True)]
        if not scanners:
            self.scan_result_list.clear()
            self._set_scan_button_state("empty")
            return

        # 暂存待执行的扫描器，供「全部加入」时真正写入
        self._pending_scanners = scanners
        # 进入扫描中态（禁用按钮）
        self._set_scan_button_state("scanning")

        def worker():
            results = []  # [(name, target_path), ...]
            try:
                print(f"[Scanner] worker started, {len(scanners)} scanners", flush=True)
                ignored = _load_ignored_targets()
                print(f"[Scanner] ignored targets: {len(ignored)}", flush=True)
                found_messages = []
                # dry-run 时也传入实际 work_folder，让扫描器跳过已存在的文件
                work_folder = _get_work_folder()
                for s in scanners:
                    try:
                        # dry_run=True：只统计不写入，但会用 work_folder 检查已存在文件
                        run_scanner(
                            s, work_folder, ignored,
                            progress_cb=lambda msg: found_messages.append(msg),
                            dry_run=True,
                        )
                    except Exception as e:
                        print(f"[Scanner] scanner error: {e}", flush=True)
                print(f"[Scanner] found_messages: {len(found_messages)}", flush=True)
                # dry-run 消息格式："[ScannerName] found: AppName\tTargetPath"
                for msg in found_messages:
                    if "found: " in msg:
                        payload = msg.split("found: ", 1)[1]
                        if "\t" in payload:
                            name, path = payload.split("\t", 1)
                            results.append((name, path))
                        else:
                            results.append((payload, ""))
                print(f"[Scanner] extracted results: {len(results)}", flush=True)
            except Exception as e:
                print(f"[Scanner] scan worker error: {e}", flush=True)
            finally:
                # 通过信号回主线程（QTimer.singleShot 从子线程调用不可靠）
                self.scan_complete_signal.emit(results)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_scan_complete(self, results):
        """扫描完成：填充结果列表（每项含忽略按钮），更新底部按钮。"""
        # 特殊标记：来自「全部加入」流程，直接加入 Sunshine
        if results == ["__add_to_sunshine__"]:
            self._safe_runtomain()
            # 加入流程完成：清空结果列表，按钮切回 scan 态
            self.scan_result_list.clear()
            self._set_scan_button_state("scan")
            return

        print(f"[Scanner] _on_scan_complete called, results={len(results)}", flush=True)
        try:
            self.scan_result_list.clear()
            for name, path in results:
                # 用自定义 widget 显示「名字 + 忽略按钮」
                widget = QWidget()
                row_layout = QHBoxLayout(widget)
                row_layout.setContentsMargins(4, 2, 4, 2)
                row_layout.setSpacing(8)

                name_lbl = ElideLabel(name)
                name_lbl.setStyleSheet("background: transparent;")
                # 不设最大宽度，让 label 随视口宽度伸缩并自动省略文本
                name_lbl.setToolTip(name)
                row_layout.addWidget(name_lbl, 1)

                ignore_btn = QPushButton(self.tr("忽略"))
                ignore_btn.setFixedHeight(24)
                ignore_btn.setFixedWidth(60)
                ignore_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                # 允许手柄聚焦，方向键可在项内/项间导航
                ignore_btn.setFocusPolicy(Qt.StrongFocus)
                ignore_btn.setCursor(Qt.PointingHandCursor)
                ignore_btn.setStyleSheet(
                    "QPushButton { background-color: #888; color: white; "
                    "border: 2px solid transparent; border-radius: 3px; padding: 2px 8px; }"
                    "QPushButton:hover { background-color: #a55; }"
                    "QPushButton:focus { background-color: #66ccff; color: #003344; "
                    "border: 2px solid #ffffff; }"
                )
                row_layout.addWidget(ignore_btn)

                item = QListWidgetItem()
                # item 宽度跟随视口宽度，避免横向滚动；resize 时 ResultList 会同步更新
                vw = self.scan_result_list.viewport().width()
                hint = widget.sizeHint()
                hint.setWidth(vw if vw > 0 else hint.width())
                item.setSizeHint(hint)
                # 存 (name, path) 供点击加入使用
                item.setData(Qt.UserRole, (name, path))
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                self.scan_result_list.addItem(item)
                self.scan_result_list.setItemWidget(item, widget)

                # 忽略按钮：加入忽略列表并移除该项
                ignore_btn.clicked.connect(lambda _checked=False, it=item, n=name, p=path:
                                           self._ignore_scanned_item(it, n, p))

            # 列表项激活：鼠标单击（itemClicked）+ A 键/双击（itemActivated）
            # 两者都连到同一槽，用防重入标志避免双击时重复触发
            try:
                self.scan_result_list.itemClicked.disconnect()
            except Exception:
                pass
            try:
                self.scan_result_list.itemActivated.disconnect()
            except Exception:
                pass
            self.scan_result_list.itemClicked.connect(self._add_single_scanned)
            self.scan_result_list.itemActivated.connect(self._add_single_scanned)

            self._set_scan_button_state("add" if results else "empty")
            print(f"[Scanner] UI updated, button state: {self.scan_btn.text()}", flush=True)
            if results:
                msg = self.tr("扫描完成，扫描到 %1 个应用").replace('%1', str(len(results)))
                print(msg, flush=True)
                try:
                    from PyQt5.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        for w in app.topLevelWidgets():
                            if hasattr(w, 'log_tab'):
                                w.log_tab.show_success_notification(msg)
                                break
                except Exception as e:
                    print(f"[Scanner] notify error: {e}", flush=True)
        except Exception as e:
            print(f"[Scanner] _on_scan_complete error: {e}", flush=True)
            import traceback
            traceback.print_exc()

    def _add_single_scanned(self, item):
        """点击单个扫描结果：写入 work_folder 并加入 Sunshine。"""
        # 防重入：鼠标双击会先后触发 itemClicked 与 itemActivated，A 键只触发 itemActivated
        if self._scan_adding_in_progress:
            return
        data = item.data(Qt.UserRole)
        if not data:
            return
        self._scan_adding_in_progress = True
        # 短延时后解锁，避免连击；加入流程在子线程中执行不阻塞 UI
        QTimer.singleShot(400, lambda: setattr(self, '_scan_adding_in_progress', False))
        name, path = data
        # 找到对应的扫描器并只运行这一个（写入 work_folder）
        scanners = getattr(self, '_pending_scanners', None) or []
        # 简化：重新运行所有待处理扫描器写入 work_folder，然后加入 Sunshine
        # 实际上单项加入较复杂，这里直接调用全部加入流程
        self._add_all_scanned()

    def _ignore_scanned_item(self, item, name, path):
        """把扫描结果项加入忽略列表，并从列表移除。"""
        if not path:
            return
        try:
            import json
            basic_def.load_config()
            raw = basic_def.config.get('Settings', 'ignored_apps', fallback='[]')
            try:
                ignored = json.loads(raw)
            except Exception:
                ignored = []
            # 避免重复
            if not any(app.get('path') == path for app in ignored):
                ignored.append({'name': name, 'path': path})
                basic_def.config.set('Settings', 'ignored_apps', json.dumps(ignored, ensure_ascii=False))
                basic_def.save_config()
            # 从列表移除
            row = self.scan_result_list.row(item)
            self.scan_result_list.takeItem(row)
            # 焦点归位：移除项后按钮已被销毁，把焦点交回列表本身
            self.scan_result_list.setFocus()
            # 尝试选中相邻项，便于继续手柄操作
            if self.scan_result_list.count() > 0:
                target_row = min(row, self.scan_result_list.count() - 1)
                self.scan_result_list.setCurrentRow(target_row)
            # 若列表空了，切回 scan 态
            if self.scan_result_list.count() == 0:
                self._set_scan_button_state("empty")
        except Exception as e:
            print(f"[Scanner] ignore error: {e}", flush=True)

    # 蓝色按钮样式（scan / 全部加入 态共用）
    _BLUE_BTN_STYLE = (
        "QPushButton {"
        "  background-color: #2E7D9B;"
        "  color: white;"
        "  border: 2px solid transparent;"
        "  border-radius: 5px;"
        "  padding: 8px;"
        "}"
        "QPushButton:hover { background-color: #245A71; }"
        "QPushButton:pressed { background-color: #1C4455; }"
        "QPushButton:focus {"
        "  background-color: #66ccff;"
        "  color: #003344;"
        "  border: 2px solid #ffffff;"
        "}"
    )
    # 灰色禁用按钮样式（扫描中 / 未扫描到新增应用 态共用）
    _GREY_BTN_STYLE = (
        "QPushButton {"
        "  background-color: #888888;"
        "  color: #cccccc;"
        "  border: 2px solid transparent;"
        "  border-radius: 5px;"
        "  padding: 8px;"
        "}"
        "QPushButton:disabled {"
        "  background-color: #888888;"
        "  color: #cccccc;"
        "}"
    )

    def _set_scan_button_state(self, state):
        """统一设置底部按钮的状态、文字、样式与可用性。

        state 取值：
          "scan"     - 未扫描，可点击触发扫描
          "scanning" - 扫描进行中，禁用
          "add"      - 扫描完成且有新增，可点击加入 Sunshine
          "empty"    - 扫描完成但无新增，禁用，5 秒后自动切回 scan 态
        """
        if state == "scan":
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText(self.tr("scan"))
            self.scan_btn.setStyleSheet(self._BLUE_BTN_STYLE)
            self._empty_reset_timer.stop()
        elif state == "scanning":
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText(self.tr("扫描中..."))
            self.scan_btn.setStyleSheet(self._GREY_BTN_STYLE)
            self._empty_reset_timer.stop()
        elif state == "add":
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText(self.tr("全部加入"))
            self.scan_btn.setStyleSheet(self._BLUE_BTN_STYLE)
            self._empty_reset_timer.stop()
        elif state == "empty":
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText(self.tr("未扫描到新增应用"))
            self.scan_btn.setStyleSheet(self._GREY_BTN_STYLE)
            # 5 秒后自动切回 scan 态，方便用户重新触发扫描
            self._empty_reset_timer.start(5000)

    def _on_scan_button_clicked(self):
        """按钮点击分发：scan 态触发扫描，add 态写入并加入 Sunshine。"""
        text = self.scan_btn.text()
        if text == self.tr("scan"):
            self._auto_run_scanners()
        elif text == self.tr("全部加入"):
            self._add_all_scanned()

    def _add_all_scanned(self):
        """「全部加入」：真正运行扫描器写入 work_folder，然后加入 Sunshine。"""
        scanners = getattr(self, '_pending_scanners', None)
        if not scanners:
            return
        # 进入扫描中态
        self._set_scan_button_state("scanning")

        def worker():
            ignored = _load_ignored_targets()
            work_folder = _get_work_folder()
            for s in scanners:
                try:
                    run_scanner(s, work_folder, ignored, progress_cb=lambda m: None)
                except Exception:
                    pass
            # 通过信号回主线程加入 Sunshine
            self.scan_complete_signal.emit(["__add_to_sunshine__"])

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    def _extract_dropped_paths(self, event):
        paths = []
        mime = event.mimeData()

        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    if local_path:
                        paths.append(local_path)

        if not paths and mime.hasText():
            raw = mime.text().strip()
            if raw:
                # Fallback for drag sources that provide text payload.
                chunks = [x.strip().strip('{}') for x in raw.splitlines() if x.strip()]
                paths.extend(chunks)

        return paths

    def _has_supported_drop_file(self, event):
        for path in self._extract_dropped_paths(event):
            lowered = path.lower()
            if lowered.endswith('.exe') or lowered.endswith('.lnk'):
                return True
        return False

    def dragEnterEvent(self, event):
        if self._has_supported_drop_file(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._has_supported_drop_file(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [
            p for p in self._extract_dropped_paths(event)
            if p.lower().endswith('.exe') or p.lower().endswith('.lnk')
        ]

        if not paths:
            _cc(self, 'warning', self.tr('提示'), self.tr('仅支持拖入 .exe 或 .lnk 文件。'))
            event.ignore()
            return

        result = add_files_to_work_folder_as_shortcuts(paths)
        created_count = len(result.get('created', []))
        skipped_count = len(result.get('skipped', []))
        error_count = len(result.get('errors', []))

        lines = [self.tr("已在工作文件夹创建 %1 个快捷方式。").replace('%1', str(created_count))]
        if skipped_count:
            lines.append(self.tr("已跳过 %1 个不支持文件。").replace('%1', str(skipped_count)))
        if error_count:
            lines.append(self.tr("有 %1 个文件处理失败，请查看日志页。").replace('%1', str(error_count)))
        lines.append(self.tr("工作文件夹: %1").replace('%1', result.get('work_folder', '')))

        # 用成功通知代替阻塞对话框
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        msg = '\n'.join(lines)
        if app:
            for w in app.topLevelWidgets():
                if hasattr(w, 'log_tab'):
                    w.log_tab.show_success_notification(msg)
                    break

        event.acceptProposedAction()

    def quick_add_running_game(self):
        """快速添加运行中游戏"""
        scale = 1.0
        proc_dialog = QDialog(self)
        proc_dialog.setWindowTitle(self.tr("选择运行中游戏进程"))
        proc_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        proc_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(46, 46, 46, 0.98);
                border-radius: {int(10 * scale)}px;
                border: {int(2 * scale)}px solid #444444;
            }}
        """)

        vbox = QVBoxLayout(proc_dialog)
        vbox.setSpacing(int(10 * scale))
        vbox.setContentsMargins(
            int(20 * scale),
            int(20 * scale),
            int(20 * scale),
            int(20 * scale)
        )

        label = QLabel(
            self.tr("选择一个运行中游戏进程，加入到游戏列表。")
        )
        label.setStyleSheet("color: white; font-size: 16px;")
        label.setWordWrap(True)
        vbox.addWidget(label)

        # 枚举所有有前台窗口且不是隐藏的进程
        hwnd_pid_map = {}
        def enum_window_callback(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                hwnd_pid_map[pid] = hwnd
            return True
        win32gui.EnumWindows(enum_window_callback, None)

        proc_list = []
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                pid = proc.info.get('pid')
                name = proc.info.get('name', '')
                exe = proc.info.get('exe', '')
                if (
                    not pid
                    or pid not in hwnd_pid_map
                    or not exe
                    or name.lower() in ("explorer.exe", "desktopgame.exe", "textinputhost.exe")
                ):
                    continue
                proc_list.append(proc)
            except Exception:
                continue

        first_btn = None  # 记录第一个按钮，用于手柄焦点
        if not proc_list:
            label2 = QLabel(self.tr("没有检测到可用进程"))
            label2.setStyleSheet("color: white; font-size: 16px;")
            vbox.addWidget(label2)
        else:
            for proc in proc_list:
                proc_name = proc.info.get('name', self.tr('未知'))
                proc_exe = proc.info.get('exe', '')

                hbox = QHBoxLayout()
                hbox.setSpacing(8)

                btn = QPushButton(f"{proc_name} ({proc_exe})")
                btn.setFocusPolicy(Qt.StrongFocus)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #444444;
                        color: white;
                        border-radius: {int(8 * scale)}px;
                        font-size: {int(14 * scale)}px;
                        padding: {int(8 * scale)}px;
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        background-color: #555555;
                    }}
                    QPushButton:focus {{
                        background-color: #2E7D9B;
                        border: 2px solid #66ccff;
                    }}
                """)
                btn.clicked.connect(
                    lambda checked, exe=proc_exe: self._quick_add_and_notify(exe, proc_dialog)
                )
                hbox.addWidget(btn)
                if first_btn is None:
                    first_btn = btn

                folder_btn = QPushButton("📁")
                folder_btn.setFixedSize(32, 32)
                folder_btn.setFocusPolicy(Qt.StrongFocus)
                folder_btn.setStyleSheet(
                    "QPushButton {"
                    "  background-color: #666666;"
                    "  color: white;"
                    "  border-radius: 6px;"
                    "  font-size: 18px;"
                    "  padding: 0px;"
                    "}"
                    "QPushButton:hover {"
                    "  background-color: #888888;"
                    "}"
                    "QPushButton:focus {"
                    "  background-color: #2E7D9B;"
                    "  border: 2px solid #66ccff;"
                    "}"
                )

                def open_file_dialog(proc_exe=proc_exe):
                    start_dir = os.path.dirname(proc_exe) if proc_exe and os.path.exists(proc_exe) else ""
                    file_dialog = QFileDialog(proc_dialog)
                    file_dialog.setWindowTitle(self.tr("手动选择要添加的游戏文件"))
                    file_dialog.setNameFilter(self.tr("可执行文件 (*.exe *.lnk)"))
                    file_dialog.setFileMode(QFileDialog.ExistingFile)
                    if start_dir:
                        file_dialog.setDirectory(start_dir)
                    if file_dialog.exec_():
                        selected_file = file_dialog.selectedFiles()[0]
                        self._quick_add_and_notify(selected_file, proc_dialog)

                folder_btn.clicked.connect(
                    lambda checked, proc_exe=proc_exe: open_file_dialog(proc_exe)
                )
                hbox.addWidget(folder_btn)
                vbox.addLayout(hbox)

        proc_dialog.setLayout(vbox)
        proc_dialog.show()

        # 将对话框定位到"添加运行中游戏"按钮右上角对齐
        try:
            btn_pos = self.add_running_btn.mapToGlobal(self.add_running_btn.rect().topLeft())
            dlg_size = proc_dialog.sizeHint()
            x = btn_pos.x() + self.add_running_btn.width() - dlg_size.width()
            y = btn_pos.y() + self.add_running_btn.height() + 6
            proc_dialog.move(x, y)
        except Exception:
            pass

        # 手柄支持：将焦点设为第一个进程按钮，使方向键可在弹窗内导航
        if first_btn is not None:
            QTimer.singleShot(0, first_btn.setFocus)

    def _quick_add_and_notify(self, exe_path, dialog):
        """添加游戏并提示"""
        dialog.accept()
        result = add_files_to_work_folder_as_shortcuts([exe_path])
        created = len(result.get('created', []))
        skipped = len(result.get('skipped', []))
        errors = len(result.get('errors', []))

        lines = [self.tr("已在工作文件夹创建 %1 个快捷方式。").replace('%1', str(created))]
        if skipped:
            lines.append(self.tr("已跳过 %1 个不支持文件。").replace('%1', str(skipped)))
        if errors:
            lines.append(self.tr("有 %1 个文件处理失败，请查看日志页。").replace('%1', str(errors)))
        msg = "\n".join(lines)

        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            for w in app.topLevelWidgets():
                if hasattr(w, 'log_tab'):
                    w.log_tab.show_success_notification(msg)
                    break
