import os
import sys
import logging
from enum import Enum
from pathlib import Path
from typing import Final

class Config:
    """配置类，管理所有配置项"""
    
    # 窗口配置
    WINDOW_SIZE: Final[tuple[int, int, int, int]] = (163, 33, 1602, 946) # **禁止修改，修改完可能图片检测不匹配
    WINDOW_TITLE: Final[str] = "ABC"  # 窗口标题
    
    # 游戏配置
    #ROD_RETRIEVE_INTERVAL: Final[int] = 14 # 钓鱼时收杆的间隔
    ROD_RETRIEVE_INTERVAL: Final[int] = 13  # 钓鱼时收杆(爆发)的间隔，高等级鱼竿可缩短此时间
    FISHING_CLICK_INTERVAL: Final[float] = 0.08 # 钓鱼时点击的间隔
    
    # 路径配置
    BASE_DIR: Final[Path] = Path(__file__).parent.absolute()
    GENERATE_DIR: Final[Path] = BASE_DIR / "generate"
    CONFIG_FILE: Final[Path] = GENERATE_DIR / "config.yaml"
    LOG_FILE: Final[Path] = GENERATE_DIR / "log.txt"
    
    # 根据是否打包成exe选择不同的资源路径
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        IMAGE_DIR: Final[Path] = Path(getattr(sys, '_MEIPASS', BASE_DIR)) / "images"
    else:
        IMAGE_DIR: Final[Path] = BASE_DIR / "images"
    
    # 图像资源路径
    START_FISH_BUTTON: Final[Path] = IMAGE_DIR / "start_fish.png"
    UP_IMAGE: Final[Path] = IMAGE_DIR / "01_up.png"
    LEFT_IMAGE: Final[Path] = IMAGE_DIR / "02_left.png"
    DOWN_IMAGE: Final[Path] = IMAGE_DIR / "03_un.png"
    RIGHT_IMAGE: Final[Path] = IMAGE_DIR / "04_right.png"
    WIND_IMAGE: Final[Path] = IMAGE_DIR / "05_wind.png"
    FIRE_IMAGE: Final[Path] = IMAGE_DIR / "06_fire.png"
    RAY_IMAGE: Final[Path] = IMAGE_DIR / "07_ray.png"
    ELECTRICITY_IMAGE: Final[Path] = IMAGE_DIR / "08_electricity.png"
    BAIT_IMAGE: Final[Path] = IMAGE_DIR / "huaner.png"
    USE_BUTTON: Final[Path] = IMAGE_DIR / "use_button.png"
    TIME_IMAGE: Final[Path] = IMAGE_DIR / "time.png"
    BUY_BUTTON: Final[Path] = IMAGE_DIR / "buy_button.png"
    PUSH_ROD_BUTTON: Final[Path] = IMAGE_DIR / "push_gan_button.png"
    PRESSURE_IMAGE: Final[Path] = IMAGE_DIR / "guogao.png"
    RETRY_BUTTON: Final[Path] = IMAGE_DIR / "again_button.png"
    CURRENT_UI: Final[Path] = IMAGE_DIR / "current_UI.png"
    
    # 方向图标列表
    DIRECTION_ICONS: Final[list[Path]] = [
        UP_IMAGE, DOWN_IMAGE, LEFT_IMAGE, RIGHT_IMAGE,
        WIND_IMAGE, FIRE_IMAGE, RAY_IMAGE, ELECTRICITY_IMAGE
    ]
    
    @classmethod
    def setup_logging(cls) -> None:
        """配置日志系统"""
        # 确保日志目录存在
        cls.GENERATE_DIR.mkdir(exist_ok=True)
        
        # 日志配置
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
            datefmt='%a, %d %b %Y %H:%M:%S',
            filename=str(cls.LOG_FILE),
            encoding='utf-8',
            filemode='a'
        )
        
        # 添加控制台输出
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        
        # 写入初始日志
        logging.info("开始记录日志")
    
    @classmethod
    def verify_resources(cls) -> None:
        """验证必要的资源文件是否存在"""
        required_files = [
            cls.START_FISH_BUTTON,
            cls.UP_IMAGE,
            cls.LEFT_IMAGE,
            cls.DOWN_IMAGE,
            cls.RIGHT_IMAGE,
            cls.WIND_IMAGE,
            cls.FIRE_IMAGE,
            cls.RAY_IMAGE,
            cls.ELECTRICITY_IMAGE,
            cls.BAIT_IMAGE,
            cls.USE_BUTTON,
            cls.TIME_IMAGE,
            cls.BUY_BUTTON,
            cls.PUSH_ROD_BUTTON,
            cls.PRESSURE_IMAGE,
            cls.RETRY_BUTTON
        ]
        
        missing_files = [str(f) for f in required_files if not f.exists()]
        if missing_files:
            raise FileNotFoundError(
                f"以下必要的资源文件缺失：\n{chr(10).join(missing_files)}"
            )


# 初始化配置
Config.setup_logging()
Config.verify_resources()
