import logging
import os

class MyLogger:
    def __init__(self, name: str = __name__, log_file: str = None, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        formatter = logging.Formatter(f"{'=='*20} %(asctime)s - %(levelname)s - %(message)s {'==' * 20}", 
                                      datefmt='%Y-%m-%d %H:%M:%S')

        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 可选：写入文件
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, msg): self.logger.debug(msg)
    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def critical(self, msg): self.logger.critical(msg)
