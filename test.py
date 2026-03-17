import logging
import time
from threading import Thread
from typing import Tuple, Optional, Dict, Any

import cv2
import keyboard
import numpy as np
import pyautogui
import win32con
import win32gui
import yaml

from main import WindowManager, GameConfig, FishState
from setting import Config


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
            threshold: 匹配阈值，默认 0.8

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
        time.sleep(0.5)  # 等待窗口稳定

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
        """检查秒杀界面 - 匹配"上"字图标"""
        up_button = cv2.imread(str(Config.UP_IMAGE))
        up = ImageProcessor.is_match_template(img, up_button)
        if up:
            logging.info(f"秒杀：{up}")
        return up

    def check_end_fishing_ui(self, img: np.ndarray) -> bool:
        """检查结束钓鱼界面 - 匹配"再来一次"按钮"""
        retry_button = cv2.imread(str(Config.RETRY_BUTTON))
        isretry = ImageProcessor.is_match_template(img, retry_button)
        if isretry:
            logging.info(f"再钓一次：{isretry}")
        return isretry

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

class FishingGame:
    def __init__(self):
        self.config = self._load_config()
        self.ui_recognizer = FishingUIRecognizer()

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
            time.sleep(1)
            current_img = ImageProcessor.get_screenshot(self.config.window_size)
            # s1 = self.ui_recognizer.check_start_fishing_ui(current_img);
            # logging.info(f"开始钓鱼：{str(s1)}")
            s2 = self.ui_recognizer.check_cast_rod_ui(current_img);
            logging.info(f"抛竿：{str(s2)}")
            s3 = self.ui_recognizer.check_no_bait_ui(current_img);
            logging.info(f"鱼饵不足：{str(s3)}")
            # s4 = self.ui_recognizer.check_catch_fish_ui(current_img);
            # logging.info(f"捕鱼：{str(s4)}")
            # s5 = self.ui_recognizer.check_fishing_ui(current_img);
            # logging.info(f"钓鱼中压力条：{str(s5)}")
            # s6 = self.ui_recognizer.check_instant_kill_ui(current_img);
            # logging.info(f"秒杀：{str(s6)}")
            # s7 = self.ui_recognizer.check_no_bait_ui(current_img);
            # logging.info(f"结束钓鱼再来一次：{str(s7)}")

            # 清理热键监听器
        keyboard.remove_hotkey('esc')
        self.state_manager.current_state = FishState.EXIT

    def run(self) -> None:
        """运行游戏主循环 - 启动状态检测线程和执行循环"""
        try:
            pyautogui.PAUSE = Config.FISHING_CLICK_INTERVAL / 2  # 设置鼠标操作延迟
            WindowManager.handle_window(self.config)  # 初始化窗口

            # 启动状态检测线程
            state_check_thread = Thread(target=self.check_current_UI)
            state_check_thread.start()

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