# -*- coding: utf-8 -*-
"""通过 ctypes 加载 SDL2.dll，为程序提供手柄（GameController）输入轮询支持。

设计说明：
- 仅在需要时加载 SDL2.dll，加载失败时退化为“不可用”状态，不影响主程序运行。
- 使用 SDL_GameController API（兼容 Xbox/PS 等标准手柄映射）。
- 采用轮询（poll）方式而非事件回调，便于和 Qt 的 QTimer 集成。
- 按钮（非方向类）使用“边沿触发”（按下/释放瞬间），避免长按重复触发。
- 方向输入（D-Pad + 左摇杆）使用 DAS/ARR 机制：
    * FIRST-<DIR>  ：按下瞬间触发一次
    * <DIR>        ：DAS 秒后每 ARR 秒重复触发一次（若 arr>0）
    * <DIR>_EDGE   ：若 arr==0，DAS 秒后只触发一次
"""
import ctypes
import os
import time

# SDL 初始化标志
SDL_INIT_JOYSTICK = 0x00000200
SDL_INIT_GAMECONTROLLER = 0x00000800

# SDL Game Controller 按钮常量（与 SDL_gamecontroller.h 一致）
SDL_CONTROLLER_BUTTON_INVALID = -1
SDL_CONTROLLER_BUTTON_A = 0
SDL_CONTROLLER_BUTTON_B = 1
SDL_CONTROLLER_BUTTON_X = 2
SDL_CONTROLLER_BUTTON_Y = 3
SDL_CONTROLLER_BUTTON_BACK = 4
SDL_CONTROLLER_BUTTON_GUIDE = 5
SDL_CONTROLLER_BUTTON_START = 6
SDL_CONTROLLER_BUTTON_LEFTSTICK = 7
SDL_CONTROLLER_BUTTON_RIGHTSTICK = 8
SDL_CONTROLLER_BUTTON_LEFTSHOULDER = 9
SDL_CONTROLLER_BUTTON_RIGHTSHOULDER = 10
SDL_CONTROLLER_BUTTON_DPAD_UP = 11
SDL_CONTROLLER_BUTTON_DPAD_DOWN = 12
SDL_CONTROLLER_BUTTON_DPAD_LEFT = 13
SDL_CONTROLLER_BUTTON_DPAD_RIGHT = 14
SDL_CONTROLLER_BUTTON_MAX = 15

# 方向键按钮集合（不由普通按钮边沿事件返回，改由 DAS/ARR 方向事件处理）
_DIRECTION_BUTTONS = frozenset((
    SDL_CONTROLLER_BUTTON_DPAD_UP,
    SDL_CONTROLLER_BUTTON_DPAD_DOWN,
    SDL_CONTROLLER_BUTTON_DPAD_LEFT,
    SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
))

# SDL Game Controller 轴常量
SDL_CONTROLLER_AXIS_INVALID = -1
SDL_CONTROLLER_AXIS_LEFTX = 0
SDL_CONTROLLER_AXIS_LEFTY = 1
SDL_CONTROLLER_AXIS_RIGHTX = 2
SDL_CONTROLLER_AXIS_RIGHTY = 3
SDL_CONTROLLER_AXIS_TRIGGERLEFT = 4
SDL_CONTROLLER_AXIS_TRIGGERRIGHT = 5
SDL_CONTROLLER_AXIS_MAX = 6

# 轴视为“按下”的阈值（用于把摇杆模拟为方向键）
AXIS_THRESHOLD = 16384

# DAS / ARR 默认值（秒）
DEFAULT_DAS = 0.3   # 延迟自动移动（Delayed Auto Shift）
DEFAULT_ARR = 0.07  # 自动重复率（Auto Repeat Rate）；设为 0 则仅触发一次 *_EDGE


def _default_dll_path():
    """返回默认的 SDL2.dll 路径（与本脚本同目录）。"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        script_dir = os.getcwd()
    return os.path.join(script_dir, "SDL2.dll")


class GamepadManager:
    """手柄管理器：使用 SDL2 进行手柄输入轮询。

    使用方式::

        gm = GamepadManager()
        if gm.available:
            btn_pressed, btn_released, dir_events = gm.poll()
            # btn_pressed / btn_released: list of (controller_index, button_int)
            # dir_events: list of (controller_index, event_str)
            #   event_str ∈ {'FIRST-UP','FIRST-DOWN','FIRST-LEFT','FIRST-RIGHT',
            #                 'UP','DOWN','LEFT','RIGHT',
            #                 'UP_EDGE','DOWN_EDGE','LEFT_EDGE','RIGHT_EDGE'}
    """

    def __init__(self, dll_path=None, das=DEFAULT_DAS, arr=DEFAULT_ARR):
        self._sdl = None
        self._controllers = []  # 已打开的控制器句柄列表（按索引）
        # 上一帧各按钮状态（用于边沿触发）：key=(controller_index, button) -> bool
        self._prev_btn_state = {}
        # 上次重新扫描控制器的时间戳（SDL_GetTicks 毫秒）
        self._last_rescan_ticks = 0
        # DAS / ARR 参数
        self.das = float(das)
        self.arr = float(arr)
        # 每个控制器的运行时状态（含 DAS/ARR repeat 子字典）
        # self.controllers[instance_id] = { 'repeat': { 'dirs': { 'UP': {...}, ... } } }
        self.controllers = {}
        self.available = False

        if dll_path is None:
            dll_path = _default_dll_path()

        # 加载 DLL：先尝试指定路径，再回退到系统搜索路径
        try:
            try:
                self._sdl = ctypes.CDLL(dll_path)
            except OSError:
                self._sdl = ctypes.CDLL("SDL2.dll")
        except OSError as e:
            print(f"[Gamepad] 加载 SDL2.dll 失败: {e}")
            return

        # 配置函数签名（避免 ctypes 默认类型不匹配）
        try:
            self._sdl.SDL_Init.argtypes = [ctypes.c_uint32]
            self._sdl.SDL_Init.restype = ctypes.c_int

            self._sdl.SDL_Quit.argtypes = []
            self._sdl.SDL_Quit.restype = None

            self._sdl.SDL_InitSubSystem.argtypes = [ctypes.c_uint32]
            self._sdl.SDL_InitSubSystem.restype = ctypes.c_int

            self._sdl.SDL_QuitSubSystem.argtypes = [ctypes.c_uint32]
            self._sdl.SDL_QuitSubSystem.restype = None

            self._sdl.SDL_WasInit.argtypes = [ctypes.c_uint32]
            self._sdl.SDL_WasInit.restype = ctypes.c_uint32

            self._sdl.SDL_NumJoysticks.argtypes = []
            self._sdl.SDL_NumJoysticks.restype = ctypes.c_int

            self._sdl.SDL_IsGameController.argtypes = [ctypes.c_int]
            self._sdl.SDL_IsGameController.restype = ctypes.c_int

            self._sdl.SDL_GameControllerOpen.argtypes = [ctypes.c_int]
            self._sdl.SDL_GameControllerOpen.restype = ctypes.c_void_p

            self._sdl.SDL_GameControllerClose.argtypes = [ctypes.c_void_p]
            self._sdl.SDL_GameControllerClose.restype = None

            self._sdl.SDL_GameControllerGetAttached.argtypes = [ctypes.c_void_p]
            self._sdl.SDL_GameControllerGetAttached.restype = ctypes.c_int

            self._sdl.SDL_GameControllerGetButton.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self._sdl.SDL_GameControllerGetButton.restype = ctypes.c_uint8

            self._sdl.SDL_GameControllerGetAxis.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self._sdl.SDL_GameControllerGetAxis.restype = ctypes.c_int16

            self._sdl.SDL_GameControllerUpdate.argtypes = []
            self._sdl.SDL_GameControllerUpdate.restype = None

            self._sdl.SDL_GetTicks.argtypes = []
            self._sdl.SDL_GetTicks.restype = ctypes.c_uint32
        except AttributeError as e:
            print(f"[Gamepad] SDL2 函数签名配置失败: {e}")
            self._sdl = None
            return

        # 初始化 gamecontroller 子系统（同时也会初始化 joystick）
        if self._sdl.SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER | SDL_INIT_JOYSTICK) != 0:
            print("[Gamepad] SDL_InitSubSystem 失败")
            self._sdl = None
            return

        self.available = True
        self._open_all_controllers()

    # ---- DAS / ARR repeat helpers ----

    def _init_repeat_state_for_controller(self, instance_id):
        """为指定 controller 初始化方向 DAS/ARR 状态。"""
        ctrl_state = self.controllers.setdefault(instance_id, {})
        ctrl_state.setdefault('repeat', {
            'dirs': {
                'UP':    {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
                'DOWN':  {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
                'LEFT':  {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
                'RIGHT': {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
            }
        })

    def _handle_direction_state(self, instance_id, up, down, left, right):
        """集中处理方向输入（D-Pad + 左摇杆的 OR 结果），应用 DAS/ARR。

        返回: list of (instance_id, event_str)
        """
        now = time.time()
        das = getattr(self, 'das', DEFAULT_DAS)
        arr = getattr(self, 'arr', DEFAULT_ARR)

        events = []
        repeat = self.controllers[instance_id].setdefault('repeat', {})
        dirs = repeat.setdefault('dirs', {})

        booleans = {'UP': up, 'DOWN': down, 'LEFT': left, 'RIGHT': right}

        for dname, is_pressed in booleans.items():
            state = dirs.setdefault(
                dname,
                {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
            )

            if is_pressed:
                if not state['pressed']:
                    # initial press
                    state['pressed'] = True
                    state['first_sent'] = True
                    state['edge_sent'] = False
                    state['next_time'] = now + das
                    events.append((instance_id, f'FIRST-{dname}'))
                else:
                    # already pressed, check for repeat
                    if now >= state['next_time']:
                        if arr == 0:
                            # edge behavior: emit once
                            if not state.get('edge_sent', False):
                                state['edge_sent'] = True
                                events.append((instance_id, f'{dname}_EDGE'))
                        else:
                            # emit normal repeat and schedule next
                            events.append((instance_id, dname))
                            state['next_time'] = now + arr
            else:
                # released
                if state['pressed']:
                    state['pressed'] = False
                    state['first_sent'] = False
                    state['edge_sent'] = False
                    state['next_time'] = 0

        return events

    # ---- Controller lifecycle ----

    def _open_all_controllers(self):
        """打开所有可用的 GameController 并初始化 DAS 状态。"""
        if not self.available:
            return
        # 关闭已存在的
        for c in self._controllers:
            try:
                self._sdl.SDL_GameControllerClose(c)
            except Exception:
                pass
        self._controllers = []
        self._prev_btn_state.clear()
        self.controllers.clear()

        try:
            n = self._sdl.SDL_NumJoysticks()
        except Exception:
            n = 0
        for i in range(n):
            try:
                if self._sdl.SDL_IsGameController(i):
                    ctl = self._sdl.SDL_GameControllerOpen(i)
                    if ctl:
                        self._controllers.append(ctl)
                        # 为每个控制器初始化 DAS/ARR 状态
                        self._init_repeat_state_for_controller(len(self._controllers) - 1)
            except Exception:
                continue
        if self._controllers:
            print(f"[Gamepad] 已连接 {len(self._controllers)} 个手柄")

    def refresh(self):
        """重新扫描并打开控制器（手柄热插拔后调用）。"""
        if self.available:
            self._open_all_controllers()

    def _maybe_rescan(self):
        """定时检测热插拔：每 2 秒尝试重新扫描一次。"""
        try:
            now = self._sdl.SDL_GetTicks()
        except Exception:
            return
        if now - self._last_rescan_ticks > 2000:
            self._last_rescan_ticks = now
            try:
                n = self._sdl.SDL_NumJoysticks()
            except Exception:
                n = 0
            gc_count = 0
            for i in range(n):
                try:
                    if self._sdl.SDL_IsGameController(i):
                        gc_count += 1
                except Exception:
                    continue
            if gc_count != len(self._controllers):
                self._open_all_controllers()

    # ---- Polling ----

    def poll(self):
        """轮询当前帧的按钮与方向事件。

        返回: (btn_pressed, btn_released, dir_events)
            btn_pressed / btn_released: list of (controller_index, button_int)
                方向按钮（DPAD_UP/DOWN/LEFT/RIGHT）不再在按钮事件中返回，
                改由 DAS/ARR 的 dir_events 输出。
            dir_events: list of (controller_index, event_str)
                event_str 形如 FIRST-UP、UP、UP_EDGE 等。
        """
        btn_pressed = []
        btn_released = []
        dir_events = []
        if not self.available or not self._controllers:
            return btn_pressed, btn_released, dir_events

        try:
            self._sdl.SDL_GameControllerUpdate()
        except Exception:
            return btn_pressed, btn_released, dir_events

        self._maybe_rescan()

        for idx, ctl in enumerate(self._controllers):
            try:
                if not self._sdl.SDL_GameControllerGetAttached(ctl):
                    continue
            except Exception:
                continue

            # ---- 读取方向状态（D-Pad + 左摇杆，取 OR） ----
            try:
                dpad_up = self._sdl.SDL_GameControllerGetButton(
                    ctl, SDL_CONTROLLER_BUTTON_DPAD_UP
                ) != 0
            except Exception:
                dpad_up = False
            try:
                dpad_down = self._sdl.SDL_GameControllerGetButton(
                    ctl, SDL_CONTROLLER_BUTTON_DPAD_DOWN
                ) != 0
            except Exception:
                dpad_down = False
            try:
                dpad_left = self._sdl.SDL_GameControllerGetButton(
                    ctl, SDL_CONTROLLER_BUTTON_DPAD_LEFT
                ) != 0
            except Exception:
                dpad_left = False
            try:
                dpad_right = self._sdl.SDL_GameControllerGetButton(
                    ctl, SDL_CONTROLLER_BUTTON_DPAD_RIGHT
                ) != 0
            except Exception:
                dpad_right = False

            try:
                left_x = self._sdl.SDL_GameControllerGetAxis(ctl, SDL_CONTROLLER_AXIS_LEFTX)
            except Exception:
                left_x = 0
            try:
                left_y = self._sdl.SDL_GameControllerGetAxis(ctl, SDL_CONTROLLER_AXIS_LEFTY)
            except Exception:
                left_y = 0

            axis_right = left_x > AXIS_THRESHOLD
            axis_left = left_x < -AXIS_THRESHOLD
            axis_down = left_y > AXIS_THRESHOLD
            axis_up = left_y < -AXIS_THRESHOLD

            combined_up = bool(dpad_up or axis_up)
            combined_down = bool(dpad_down or axis_down)
            combined_left = bool(dpad_left or axis_left)
            combined_right = bool(dpad_right or axis_right)

            # 确保该控制器的 repeat 结构存在（热插拔补建）
            if idx not in self.controllers:
                self._init_repeat_state_for_controller(idx)
            dir_events.extend(
                self._handle_direction_state(
                    idx, combined_up, combined_down, combined_left, combined_right
                )
            )

            # ---- 读取非方向按钮（边沿触发） ----
            for btn in range(SDL_CONTROLLER_BUTTON_MAX):
                if btn in _DIRECTION_BUTTONS:
                    # 方向按键由 DAS/ARR 统一处理，不再作为普通按钮事件返回
                    continue
                try:
                    state = self._sdl.SDL_GameControllerGetButton(ctl, btn) != 0
                except Exception:
                    continue
                key = (idx, btn)
                prev = self._prev_btn_state.get(key, False)
                if state and not prev:
                    btn_pressed.append((idx, btn))
                elif not state and prev:
                    btn_released.append((idx, btn))
                self._prev_btn_state[key] = state

        return btn_pressed, btn_released, dir_events

    # ---- 向后兼容的辅助方法（已弃用，保留避免外部代码报错） ----

    def poll_axis_as_dpad(self):
        """已弃用。方向输入现由 poll() 中的 DAS/ARR 统一处理。

        返回两个空列表，供旧代码解包。
        """
        return [], []

    def has_controllers(self):
        """是否至少连接了一个手柄。"""
        return bool(self._controllers)

    def cleanup(self):
        """释放所有控制器并关闭 SDL 子系统。"""
        for c in self._controllers:
            try:
                self._sdl.SDL_GameControllerClose(c)
            except Exception:
                pass
        self._controllers = []
        self.controllers.clear()
        self._prev_btn_state.clear()
        if self.available and self._sdl is not None:
            try:
                self._sdl.SDL_QuitSubSystem(SDL_INIT_GAMECONTROLLER | SDL_INIT_JOYSTICK)
            except Exception:
                pass
            try:
                self._sdl.SDL_Quit()
            except Exception:
                pass
        self.available = False
