import logging
import os
import platform

# ANSI颜色代码
class Colors:
    RESET = '\033[0m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    # 背景色
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

# 检查是否为Windows系统
IS_WINDOWS = platform.system() == "Windows"

# 如果是Windows系统，需要启用ANSI颜色支持
if IS_WINDOWS:
    # 尝试启用Windows终端的颜色支持
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # 启用ANSI转义序列处理
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        # 如果失败，禁用颜色
        for attr in dir(Colors):
            if not attr.startswith('__'):
                setattr(Colors, attr, '')

class ColoredFormatter(logging.Formatter):
    """自定义彩色格式化器"""
    
    COLORS = {
        'DEBUG': Colors.BLUE,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.BOLD + Colors.RED,
    }
    
    def format(self, record):
        """添加颜色到日志级别"""
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Colors.RESET}"
            record.name = f"{Colors.CYAN}{record.name}{Colors.RESET}"
            # 可以添加更多彩色字段
        return super().format(record)

class MyLogger:
    def __init__(self, name: str = __name__, log_file: str = None, level: int = logging.INFO, colored: bool = True):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 禁止日志传播到父记录器
        self.logger.propagate = False
        
        # 防止重复添加处理器
        if not self.logger.handlers:
            # 控制台输出
            console_handler = logging.StreamHandler()
            
            if colored:
                # 彩色格式
                colored_formatter = ColoredFormatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s", 
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(colored_formatter)
            else:
                # 普通格式
                plain_formatter = logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s", 
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(plain_formatter)
                
            self.logger.addHandler(console_handler)

            # 可选：写入文件 (文件中不使用颜色)
            if log_file:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_formatter = logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s", 
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)

    def debug(self, msg): self.logger.debug(msg)
    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def critical(self, msg): self.logger.critical(msg)
    
    def color_text(self, text, color):
        """返回带颜色的文本"""
        color_code = getattr(Colors, color.upper(), Colors.RESET)
        return f"{color_code}{text}{Colors.RESET}"
    
    # 提供额外的彩色日志方法
    def success(self, msg): 
        self.logger.info(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
        
    def highlight(self, msg, color='YELLOW'):
        """使用指定颜色高亮显示消息"""
        color_code = getattr(Colors, color.upper(), Colors.YELLOW)
        self.logger.info(f"{color_code}{msg}{Colors.RESET}")
