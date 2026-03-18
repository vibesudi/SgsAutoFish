import os
import win32gui
import win32con
import pyautogui
import time
import cv2
import numpy as np
import yaml
import keyboard
from threading import Thread
from enum import Enum, auto
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from setting import Config
import logging
# ... existing code ...

class FishState(Enum):
    """钓鱼游戏的状态枚举"""
    START_FISHING = auto()  # 开始钓鱼 - 等待点击开始钓鱼按钮的初始状态
    CAST_ROD = auto()  # 抛竿 - 执行抛竿动作的状态
    NO_BAIT = auto()  # 鱼饵不足 - 需要补充鱼饵的状态
    CATCH_FISH = auto()  # 捕鱼 - 成功钓到鱼后的处理状态
    FISHING = auto()  # 钓鱼中 - 正在进行钓鱼玩法的核心状态
    INSTANT_KILL = auto()  # 秒杀 - 进入最后一击的特殊状态
    END_FISHING = auto()  # 结束钓鱼 - 钓鱼完成后的结算状态
    EXIT = auto()  # 退出 - 程序退出状态


@dataclass
class GameConfig:
    """游戏配置数据类 - 存储所有游戏相关的配置和检测到的位置信息"""
    window_title: str  # 模拟器窗口标题 - 用于定位游戏窗口
    window_size: Tuple[int, int, int, int]  # 模拟器窗口大小和位置 (x, y, width, height) - 截图区域
    start_fishing_pos: Optional[Tuple[int, int]] = None  # 开始钓鱼按钮的中心点坐标 - 用于点击开始钓鱼
    rod_position: Optional[Tuple[int, int]] = None  # 钓鱼界面拉杆位置中心点坐标 - 用于检测拉杆移动
    pressure_indicator_pos: Optional[Tuple[int, int]] = None  # 用来判断压力是否过高的点的位置 - 压力条检测点
    low_pressure_color: Optional[Tuple[int, int, int]] = None  # 用来判断压力是否过高的点的颜色 - 低压状态下的颜色基准
    original_rod_color: Optional[Tuple[int, int, int]] = None  # 钓鱼界面拉杆位置中心点颜色 - 拉杆未移动的顏色基准
    direction_icon_positions: Optional[Dict[str, Tuple[int, int]]] = None  # 方向图标位置字典 - 秒杀阶段的方向键位置
    retry_button_center: Optional[Tuple[int, int]] = None  # 再来一次按钮的中心点坐标 - 钓鱼结束后重新开始
    use_bait_button_pos: Optional[Tuple[int, int]] = None  # 使用鱼饵按钮的位置 - 鱼饵不足时点击


class WindowManager:
    """窗口管理类，处理窗口相关的操作 - 确保游戏窗口正确定位和激活"""

    @staticmethod
    def find_window(title: str) -> int:
        """查找指定标题的窗口句柄 - Windows API 调用"""
        return win32gui.FindWindow(None, title)

    @staticmethod
    def get_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
        """获取窗口位置和大小 - 返回左上角和右下角坐标"""
        return win32gui.GetWindowRect(hwnd)

    @staticmethod
    def bring_to_front(hwnd: int) -> None:
        """将窗口置于最前端并激活 - 确保窗口可操作"""
        win32gui.SetForegroundWindow(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    @staticmethod
    def handle_window(config: GameConfig) -> None:
        """处理窗口配置和位置 - 初始化时设置窗口"""
        hwnd = WindowManager.find_window(config.window_title)
        if not hwnd:
            raise ValueError(f"未找到标题为 {config.window_title} 的窗口")

        WindowManager.bring_to_front(hwnd)
        # 设置窗口位置和大小，确保截图区域准确
        win32gui.SetWindowPos(hwnd, None, *config.window_size, 0)
        # win32gui.SetWindowPos(hwnd, None, 0,0,0,0, win32con.SWP_NOSIZE)
        time.sleep(0.5)  # 等待窗口稳定
        # logging.info(str(WindowManager.get_window_rect(hwnd)))

# ... existing code ...

class ImageProcessor:
    """图像处理类，处理所有图像相关的操作 - 截图、模板匹配等核心功能"""

    @staticmethod
    def get_screenshot(size: Tuple[int, int, int, int],
                       is_save: bool = False,
                       save_path: Optional[str] = None) -> np.ndarray:
        """获取屏幕截图 - 使用 pyautogui 截取指定区域

        Args:
            size: 截图区域 (x, y, width, height)
            is_save: 是否保存截图
            save_path: 保存路径

        Returns:
            OpenCV 格式的图像数组 (BGR 格式)
        """
        img = pyautogui.screenshot(region=size)
        img_np = np.array(img)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)  # 转换为 OpenCV 的 BGR 格式
        if is_save and save_path:
            img.save(save_path)
        return img_np

    @staticmethod
    def is_match_template(img: np.ndarray,
                          template: np.ndarray,
                          threshold: float = 0.7) -> bool:
        """模板匹配判断 - 检查图像中是否存在指定的模板

        Args:
            img: 源图像
            template: 模板图像
            threshold: 匹配阈值，默认 0.8 , 0.8有时候匹配失败 -> 0.7

        Returns:
            是否匹配成功
        """
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        return len(loc[0]) > 0

    @staticmethod
    def match_template(img: np.ndarray,
                       template: np.ndarray,
                       threshold: float = 0.8,
                       position: Tuple[float, float] = (0.5, 0.5)) -> Tuple[int, int]:
        """模板匹配并返回指定位置 - 精确定位 UI 元素

        Args:
            img: 输入图像
            template: 模板图像
            threshold: 匹配阈值
            position: 归一化位置坐标，范围 [0,1]，(0,0) 表示左上角，(1,1) 表示右下角，默认为 (0.5,0.5) 即中心位置
                    如果值超出范围，将自动调整到最近的合法值

        Returns:
            返回指定位置的坐标 (x, y)
        """
        # 将 position 值限制在 [0,1] 范围内，防止计算错误
        clamped_x = max(0, min(1, position[0]))
        clamped_y = max(0, min(1, position[1]))

        # 如果值被调整，记录日志
        if clamped_x != position[0] or clamped_y != position[1]:
            logging.warning(f"position 参数值被调整：{position} -> ({clamped_x}, {clamped_y})")

        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)  # 获取最佳匹配位置

        # 获取模板的宽高
        template_width = template.shape[1]
        template_height = template.shape[0]

        # 根据归一化位置计算实际坐标 - 支持获取匹配框的任意相对位置
        x = int(max_loc[0] + template_width * clamped_x)
        y = int(max_loc[1] + template_height * clamped_y)

        return (x, y)


class ConfigManager:
    """配置管理类，处理配置文件的读写 - 持久化存储检测到的位置信息"""

    @staticmethod
    def write_yaml(data: Dict[str, Any]) -> None:
        """写入 YAML 配置文件 - 保存位置检测结果"""
        with open(str(Config.CONFIG_FILE), 'w', encoding='utf-8') as f:
            yaml.dump(data, f)

    @staticmethod
    def read_yaml() -> Dict[str, Any]:
        """读取 YAML 配置文件 - 加载已保存的位置信息"""
        with open(str(Config.CONFIG_FILE), 'r', encoding='utf-8') as f:
            return yaml.load(f, Loader=yaml.FullLoader)


class MouseController:
    """鼠标控制类，处理所有鼠标操作 - 模拟点击和拖拽"""

    @staticmethod
    def press_mouse_move(start_x: int, start_y: int,
                         x: int, y: int, button: str = 'left') -> None:
        """模拟鼠标拖拽操作 - 用于抛竿和拉杆动作

        Args:
            start_x, start_y: 起始位置
            x, y: 移动的距离（相对起始点）
            button: 鼠标按键，默认左键
        """
        pyautogui.mouseDown(start_x, start_y, button=button)
        pyautogui.moveTo(start_x + x, start_y + y, duration=0.03)  # 快速移动
        pyautogui.mouseUp(button=button)

    @staticmethod
    def click(position: Tuple[int, int]) -> None:
        """点击指定位置 - 用于按钮点击操作"""
        pyautogui.click(position)


class FishingStateManager:
    """负责状态管理和转换的类 - 识别当前游戏处于哪个阶段"""

    def __init__(self, current_img: np.ndarray):
        self.ui_recognizer = FishingUIRecognizer()
        self.current_state = self._determine_initial_state(current_img)
        self._setup_state_flags()

    def _setup_state_flags(self) -> None:
        """初始化状态标志 - 防止重复执行某些一次性操作"""
        self.first_start_fishing = True  # 首次开始钓鱼
        self.first_cast_rod = True  # 首次抛竿
        self.first_no_bait = True  # 首次鱼饵不足
        self.first_retry = True  # 首次重试
        self.first_instant_kill = True  # 首次进入秒杀
        self.rod_retrieve_time = 0  # 收杆时间记录

    def update_state(self, current_img: np.ndarray) -> None:
        """更新当前状态 - 根据识别到的 UI 元素进行状态转换

        状态转换逻辑:
        START_FISHING -> CAST_ROD: 检测到抛竿界面
        CAST_ROD -> NO_BAIT: 检测到鱼饵不足
        CAST_ROD -> CATCH_FISH: 检测到捕到鱼
        NO_BAIT -> CAST_ROD: 鱼饵补充完成
        CATCH_FISH -> FISHING: 进入钓鱼玩法
        FISHING -> END_FISHING: 钓鱼结束
        FISHING -> INSTANT_KILL: 进入秒杀
        INSTANT_KILL -> END_FISHING: 秒杀完成
        END_FISHING -> CAST_ROD: 重新开始
        """
        old_state = self.current_state

        match self.current_state:
            case FishState.START_FISHING:
                # 检测到抛竿界面的"饵"字图标，进入抛竿状态
                if self.ui_recognizer.check_cast_rod_ui(current_img):
                    self.current_state = FishState.CAST_ROD

            case FishState.CAST_ROD:
                # 检测到"使用"按钮，说明鱼饵不足
                if self.ui_recognizer.check_no_bait_ui(current_img):
                    self.current_state = FishState.NO_BAIT
                # 检测到倒计时图标，说明已经捕到鱼
                elif self.ui_recognizer.check_catch_fish_ui(current_img):
                    self.current_state = FishState.CATCH_FISH

            case FishState.NO_BAIT:
                # "使用"按钮消失，说明鱼饵已补充
                if not self.ui_recognizer.check_no_bait_ui(current_img):
                    self.current_state = FishState.CAST_ROD

            case FishState.CATCH_FISH:
                # 检测到压力条，进入正式钓鱼阶段
                if self.ui_recognizer.check_fishing_ui(current_img):
                    # FISHING 页面已就绪，但有些元素状态重置需要时间，比如挥杆 ？
                    # time.sleep(2) 2秒过长，改为0.2秒
                    time.sleep(0.2)
                    self.current_state = FishState.FISHING

            case FishState.FISHING:
                # 检测到"再来一次"按钮，钓鱼结束
                if self.ui_recognizer.check_end_fishing_ui(current_img):
                    self.current_state = FishState.END_FISHING
                # 检测到"上"字图标，进入秒杀阶段
                elif self.ui_recognizer.check_instant_kill_ui(current_img):
                    self.current_state = FishState.INSTANT_KILL

            case FishState.INSTANT_KILL:
                # 秒杀完成后进入结束状态
                if self.ui_recognizer.check_end_fishing_ui(current_img):
                    self.current_state = FishState.END_FISHING

            case FishState.END_FISHING:
                # 点击"再来一次"后，回到抛竿状态
                if self.ui_recognizer.check_cast_rod_ui(current_img):
                    self.current_state = FishState.CAST_ROD

        # 记录状态变化日志
        if old_state != self.current_state:
            logging.info(f"页面状态变化：{old_state} -> {self.current_state}")

    def reset_state_flags(self) -> None:
        """重置所有状态标志 - 一轮钓鱼完成后调用"""
        self._setup_state_flags()

    def _determine_initial_state(self, current_img: np.ndarray) -> FishState:
        """调整初始状态，兼容从任何页面启动程序

        Args:
            current_img: 当前屏幕截图

        Returns:
            初始状态
        """
        state = FishState.START_FISHING
        # 按照优先级检查各个 UI 界面，设置对应的状态
        if self.ui_recognizer.check_start_fishing_ui(current_img):
            state = FishState.START_FISHING
        elif self.ui_recognizer.check_cast_rod_ui(current_img):
            state = FishState.CAST_ROD
        elif self.ui_recognizer.check_no_bait_ui(current_img):
            state = FishState.NO_BAIT
        elif self.ui_recognizer.check_catch_fish_ui(current_img):
            state = FishState.CATCH_FISH
        elif self.ui_recognizer.check_fishing_ui(current_img):
            state = FishState.FISHING
        elif self.ui_recognizer.check_end_fishing_ui(current_img):
            state = FishState.END_FISHING
        elif self.ui_recognizer.check_instant_kill_ui(current_img):
            state = FishState.INSTANT_KILL
        else:
            # 如果都不匹配，默认设置为开始钓鱼状态
            state = FishState.START_FISHING

        logging.info(f"初始页面状态调整为：{state}")
        return state


# ... existing code ...

class FishingPositionDetector:
    """负责位置检测的类 - 自动定位游戏中的关键 UI 元素位置"""

    def __init__(self, config: GameConfig):
        self.config = config

    def detect_start_fishing_pos(self) -> None:
        """检测开始钓鱼按钮位置 - 首次运行时自动定位"""
        start_fishing_UI_img = ImageProcessor.get_screenshot(self.config.window_size)
        start_fishing_button_img = cv2.imread(str(Config.START_FISH_BUTTON))
        pos = ImageProcessor.match_template(start_fishing_UI_img, start_fishing_button_img)
        # 转换为全局坐标
        self.config.start_fishing_pos = (
            pos[0] + self.config.window_size[0],
            pos[1] + self.config.window_size[1]
        )
        ConfigManager.write_yaml(self.config.__dict__)

    def detect_fishing_positions(self) -> None:
        """检测钓鱼相关位置 - 拉杆位置和压力条检测点"""
        fishing_img = ImageProcessor.get_screenshot(self.config.window_size)
        push_rod_icon = cv2.imread(str(Config.PUSH_ROD_BUTTON))  # 拉杆图标模板
        pressure_img = cv2.imread(str(Config.PRESSURE_IMAGE))  # 压力条模板

        # 匹配拉杆位置（中心点）
        rod_pos = ImageProcessor.match_template(fishing_img, push_rod_icon)
        # 匹配压力条位置（左侧 30% 处，用于检测颜色变化, 25%会导致进化失败）
        pressure_pos = ImageProcessor.match_template(fishing_img, pressure_img, position=(0.3, 0.5))

        # 转换为全局坐标
        self.config.rod_position = (
            rod_pos[0] + self.config.window_size[0],
            rod_pos[1] + self.config.window_size[1]
        )
        self.config.pressure_indicator_pos = (
            pressure_pos[0] + self.config.window_size[0],
            pressure_pos[1] + self.config.window_size[1]
        )

        # 获取基准颜色 - 用于后续判断压力条是否变化
        self.config.low_pressure_color = pyautogui.pixel(*self.config.pressure_indicator_pos)
        self.config.original_rod_color = pyautogui.pixel(*self.config.rod_position)

        ConfigManager.write_yaml(self.config.__dict__)

    def detect_use_button_pos(self) -> None:
        """检测使用按钮位置 - 鱼饵不足时使用"""
        bait_ui_img = ImageProcessor.get_screenshot(self.config.window_size)
        use_button_img = cv2.imread(str(Config.USE_BUTTON))
        pos = ImageProcessor.match_template(bait_ui_img, use_button_img)
        self.config.use_bait_button_pos = (
            pos[0] + self.config.window_size[0],
            pos[1] + self.config.window_size[1]
        )
        ConfigManager.write_yaml(self.config.__dict__)

    def detect_retry_button_pos(self) -> None:
        """检测再次钓鱼按钮位置 - 钓鱼结束后点击"""
        game_over_img = ImageProcessor.get_screenshot(self.config.window_size)
        retry_icon = cv2.imread(str(Config.RETRY_BUTTON))
        pos = ImageProcessor.match_template(game_over_img, retry_icon)
        self.config.retry_button_center = (
            pos[0] + self.config.window_size[0],
            pos[1] + self.config.window_size[1]
        )
        ConfigManager.write_yaml(self.config.__dict__)

    def detect_direction_icons(self) -> None:
        """检测方向图标位置 - 秒杀阶段需要按顺序点击上下左右"""
        # 只截取下半部分屏幕进行搜索
        bottom_half_size = (
            self.config.window_size[0],
            (self.config.window_size[1] + self.config.window_size[3]) // 2,
            self.config.window_size[2],
            (self.config.window_size[1] + self.config.window_size[3]) // 2
        )
        bottom_half_img = ImageProcessor.get_screenshot(bottom_half_size)

        self.config.direction_icon_positions = {}
        for dir_icon_path in Config.DIRECTION_ICONS:
            dir_icon = cv2.imread(str(dir_icon_path))
            pos = ImageProcessor.match_template(bottom_half_img, dir_icon)
            name = dir_icon_path.stem  # 获取文件名作为方向名称
            self.config.direction_icon_positions[name] = (
                pos[0] + bottom_half_size[0],
                pos[1] + bottom_half_size[1]
            )
        #logging.info(f"方向图标位置：{self.config.direction_icon_positions}")
        ConfigManager.write_yaml(self.config.__dict__)


class FishingActionExecutor:
    """负责执行具体的钓鱼动作的类 - 实现各种钓鱼操作"""

    def __init__(self, config: GameConfig):
        self.config = config
        self.fishing_click_time = 0  # 记录上次点击时间
        self.rod_retrieve_time = 0  # 记录上次收杆时间

    def resset_time(self):
        self.fishing_click_time = 0
        self.rod_retrieve_time = 0

    def handle_default_state(self) -> None:
        """处理默认状态 - 点击开始钓鱼按钮"""
        MouseController.click(self.config.start_fishing_pos)

    def handle_cast_rod_state(self) -> None:
        """处理抛竿状态 - 向上拖动鼠标模拟抛竿动作"""
        MouseController.press_mouse_move(
            self.config.start_fishing_pos[0],
            self.config.start_fishing_pos[1],
            0, -100  # 向上移动 100 像素
        )

    def handle_no_bait_state(self) -> None:
        """处理鱼饵不足状态 - 点击使用鱼饵按钮"""
        MouseController.click(self.config.use_bait_button_pos)

    def handle_catch_fish_state(self) -> Optional[FishState]:
        """处理捕鱼状态 - 定时点击防止鱼跑掉"""
        click_interval = 0.485
        current_time = time.time()
        if not self.fishing_click_time > 0:
            self.fishing_click_time = current_time

        if current_time - self.fishing_click_time > click_interval:
            MouseController.click(self.config.start_fishing_pos)
            self.fishing_click_time = current_time
            return FishState.CAST_ROD
        return None

    def handle_ongoing_fishing(self) -> None:
        """处理持续钓鱼状态 - 核心玩法：收线、拉杆、压力控制"""
        current_time = time.time()
        click_interval = Config.FISHING_CLICK_INTERVAL
        pressure_check_interval = click_interval * 3

        # 检查收杆 - 定期收杆防止断线
        if current_time - self.rod_retrieve_time > Config.ROD_RETRIEVE_INTERVAL:
            self.handle_rod_retrieve()

        # 检查点击操作 - 通过压力条颜色判断是否需要收线
        if current_time - self.fishing_click_time >= click_interval:
            current_pressure_color = pyautogui.pixel(*self.config.pressure_indicator_pos)
            # 压力条颜色改变，说明压力增加，需要延迟点击
            if current_pressure_color != self.config.low_pressure_color:
                self.fishing_click_time = current_time + pressure_check_interval
            # 压力条颜色未改变，点击收线
            else:
                MouseController.click(self.config.start_fishing_pos)
                self.fishing_click_time = current_time

        # 拉竿检查 - 检测拉杆是否移动，如果移动则反向拉动
        current_rod_color = pyautogui.pixel(*self.config.rod_position)
        if current_rod_color != self.config.original_rod_color:
            self.handle_rod_movement()

    def handle_rod_movement(self) -> None:
        """处理拉杆移动 - 左右晃动鼠标抵消鱼的拉力"""
        # 向右拉动
        MouseController.press_mouse_move(
            self.config.rod_position[0],
            self.config.rod_position[1],
            100, 0
        )
        # 向左拉动复位
        MouseController.press_mouse_move(
            self.config.rod_position[0],
            self.config.rod_position[1],
            -100, 0
        )

    def handle_rod_retrieve(self) -> None:
        """处理收杆 - 向上滑动鼠标"""
        MouseController.press_mouse_move(
            self.config.start_fishing_pos[0],
            self.config.start_fishing_pos[1],
            0, -75  # 向上移动 75 像素
        )
        self.rod_retrieve_time = time.time()

    def handle_end_fishing_state(self) -> None:
        """处理结束钓鱼状态 - 点击"再来一次"按钮"""
        MouseController.click(self.config.retry_button_center)
        self.resset_time()

    def handle_direction_sequence(self) -> None:
        """处理方向序列 - 秒杀阶段按从左到右的顺序点击方向图标"""
        # 截取上半部分屏幕用于识别方向图标
        top_half_size = (
            self.config.window_size[0],
            self.config.window_size[1],
            self.config.window_size[2],
            (self.config.window_size[3] + self.config.window_size[1]) // 2
        )
        top_half_img = ImageProcessor.get_screenshot(top_half_size)

        # 识别所有出现的方向图标及其位置
        all_icons_dict = {}
        for dir_icon_path in Config.DIRECTION_ICONS:
            dir_icon = cv2.imread(str(dir_icon_path))
            res = cv2.matchTemplate(top_half_img, dir_icon, cv2.TM_CCOEFF_NORMED)
            res_loc = np.where(res >= 0.8)
            if len(res_loc[0]) > 0:
                points = list(zip(*res_loc[::-1]))  # 转换坐标格式
                classified_points = self._classify_positions(points)  # 去重
                for point in classified_points:
                    all_icons_dict[point] = dir_icon_path.stem

        # 按 x 坐标排序，从左到右依次点击
        all_icons_list = sorted(all_icons_dict.items(), key=lambda x: x[0][0])
        for pos, name in all_icons_list:
            logging.info(f"{name}, 位置：{pos}")
            click_pos = self.config.direction_icon_positions[name]
            MouseController.click(click_pos)

    @staticmethod
    def _classify_positions(point_list: list) -> list:
        """对识别出来的所有位置进行分类 - 去除重复的匹配点

        Args:
            point_list: 匹配到的位置列表

        Returns:
            去重后的位置列表
        """
        result_points = []
        for i in range(len(point_list)):
            point_set = set()
            if point_list[i] is None:
                continue
            point_set.add(point_list[i])
            for j in range(i + 1, len(point_list)):
                if point_list[j] is None:
                    continue
                # 距离小于 10 像素的点视为同一位置
                if (abs(point_list[i][0] - point_list[j][0]) < 10 and
                        abs(point_list[i][1] - point_list[j][1]) < 10):
                    point_set.add(point_list[j])
                    point_list[j] = None  # 标记为已处理
            if len(point_set) > 1:
                # 计算平均位置
                average_x = int(sum([x[0] for x in point_set]) / len(point_set))
                average_y = int(sum([x[1] for x in point_set]) / len(point_set))
                result_points.append((average_x, average_y))
        return result_points


class FishingUIRecognizer:
    """负责 UI 识别的类 - 通过模板匹配识别游戏界面"""

    def check_start_fishing_ui(self, img: np.ndarray) -> bool:
        """检查开始钓鱼界面 - 匹配开始钓鱼按钮"""
        start_button = cv2.imread(str(Config.START_FISH_BUTTON))
        return ImageProcessor.is_match_template(img, start_button)

    def check_cast_rod_ui(self, img: np.ndarray) -> bool:
        """检查抛竿界面 - 匹配"饵"字图标"""
        huaner = cv2.imread(str(Config.BAIT_IMAGE))
        return ImageProcessor.is_match_template(img, huaner)

    def check_no_bait_ui(self, img: np.ndarray) -> bool:
        """检查鱼饵不足界面 - 匹配"使用"按钮"""
        use_button = cv2.imread(str(Config.USE_BUTTON))
        return ImageProcessor.is_match_template(img, use_button)

    def check_catch_fish_ui(self, img: np.ndarray) -> bool:
        """检查捕鱼界面 - 匹配倒计时图标"""
        time_icon = cv2.imread(str(Config.TIME_IMAGE))
        return ImageProcessor.is_match_template(img, time_icon)

    def check_fishing_ui(self, img: np.ndarray) -> bool:
        """检查钓鱼界面 - 匹配压力条"""
        pressure_img = cv2.imread(str(Config.PRESSURE_IMAGE))
        return ImageProcessor.is_match_template(img, pressure_img)

    def check_instant_kill_ui(self, img: np.ndarray) -> bool:
        """检查秒杀界面 - 匹配"风"字图标"""
        wind_image = cv2.imread(str(Config.WIND_IMAGE))
        return ImageProcessor.is_match_template(img, wind_image)

    def check_end_fishing_ui(self, img: np.ndarray) -> bool:
        """检查结束钓鱼界面 - 匹配"再来一次"按钮"""
        retry_button = cv2.imread(str(Config.RETRY_BUTTON))
        return ImageProcessor.is_match_template(img, retry_button)


class FishingGame:
    """钓鱼游戏主类 - 整合所有模块，运行自动钓鱼流程"""

    def __init__(self):
        self.config = self._load_config()
        self.position_detector = FishingPositionDetector(self.config)
        self.action_executor = FishingActionExecutor(self.config)

        # 获取当前截图用于初始化状态管理器
        current_img = ImageProcessor.get_screenshot(self.config.window_size)
        self.state_manager = FishingStateManager(current_img)

    def _load_config(self) -> GameConfig:
        """加载游戏配置 - 从 YAML 文件读取或创建默认配置"""
        if not Config.CONFIG_FILE.exists():
            config_dict = {}
        else:
            config_dict = ConfigManager.read_yaml()

        # 设置默认窗口标题
        if 'window_title' not in config_dict:
            config_dict['window_title'] = Config.WINDOW_TITLE
            ConfigManager.write_yaml(config_dict)

        # 设置窗口大小
        config_dict['window_size'] = Config.WINDOW_SIZE

        return GameConfig(**config_dict)

    def check_current_UI(self) -> None:
        """检查当前游戏界面状态 - 在独立线程中持续运行"""
        # 设置全局退出标志
        self.should_exit = False

        # 添加热键监听器 - ESC 键退出
        keyboard.add_hotkey('esc', lambda: setattr(self, 'should_exit', True))

        while not self.should_exit:
            current_img = ImageProcessor.get_screenshot(self.config.window_size)
            self.state_manager.update_state(current_img)
            # time.sleep(0.2)  # 添加 200ms 延时，降低 CPU 占用 不能加，影响收线

        # 清理热键监听器
        keyboard.remove_hotkey('esc')
        self.state_manager.current_state = FishState.EXIT

    def _handle_state(self) -> None:
        """处理当前状态 - 根据状态机执行对应的动作"""
        match self.state_manager.current_state:
            # 开始钓鱼状态 - 首次执行时检测按钮位置
            case FishState.START_FISHING if self.state_manager.first_start_fishing:
                if not self.config.start_fishing_pos:
                    self.position_detector.detect_start_fishing_pos()
                self.action_executor.handle_default_state()
                self.state_manager.first_start_fishing = False
                # hand add 手动设置 抛竿状态，这里没调好
                self.state_manager.current_state = FishState.CAST_ROD

            # 抛竿状态 - 执行抛竿动作
            case FishState.CAST_ROD if self.state_manager.first_cast_rod:
                self.action_executor.handle_cast_rod_state()
                self.state_manager.first_cast_rod = False
                self.state_manager.first_retry = True

            # 鱼饵不足状态 - 补充鱼饵
            case FishState.NO_BAIT if self.state_manager.first_no_bait:
                if not self.config.use_bait_button_pos:
                    self.position_detector.detect_use_button_pos()
                self.action_executor.handle_no_bait_state()
                self.state_manager.first_no_bait = False
                self.state_manager.first_cast_rod = True

            # 捕鱼状态 - 持续点击防止鱼跑掉
            case FishState.CATCH_FISH:
                next_state = self.action_executor.handle_catch_fish_state()
                if next_state:
                    self.state_manager.current_state = next_state

            # 钓鱼中状态 - 执行核心钓鱼玩法
            case FishState.FISHING:
                if not self.config.rod_position or not self.config.pressure_indicator_pos:
                    self.position_detector.detect_fishing_positions()
                self.action_executor.handle_ongoing_fishing()

            # 结束钓鱼状态 - 点击再来一次
            case FishState.END_FISHING if self.state_manager.first_retry:
                if not self.config.retry_button_center:
                    self.position_detector.detect_retry_button_pos()
                self.action_executor.handle_end_fishing_state()
                self.state_manager.reset_state_flags()
                self.state_manager.first_retry = False

            # 秒杀状态 - 按顺序点击方向图标
            case FishState.INSTANT_KILL if self.state_manager.first_instant_kill:
                if not self.config.direction_icon_positions:
                    self.position_detector.detect_direction_icons()
                self.action_executor.handle_direction_sequence()
                self.state_manager.first_instant_kill = False

    def run(self) -> None:
        """运行游戏主循环 - 启动状态检测线程和执行循环"""
        try:
            pyautogui.PAUSE = Config.FISHING_CLICK_INTERVAL / 2  # 设置鼠标操作延迟
            WindowManager.handle_window(self.config)  # 初始化窗口

            # 启动状态检测线程
            state_check_thread = Thread(target=self.check_current_UI)
            state_check_thread.start()

            # 主循环 - 根据状态执行动作
            while self.state_manager.current_state != FishState.EXIT:
                self._handle_state()

            # 保存最终配置
            ConfigManager.write_yaml(self.config.__dict__)
            logging.info("游戏结束")

        except Exception as e:
            logging.error(f"游戏运行出错：{str(e)}")
            raise


def main():
    """主函数 - 程序入口"""
    try:
        game = FishingGame()
        game.run()
    except Exception as e:
        logging.error(f"程序运行出错：{str(e)}")
        raise


if __name__ == '__main__':
    main()
