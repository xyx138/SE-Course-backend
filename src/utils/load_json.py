import json
import os
from dotenv import load_dotenv
import re

load_dotenv()

def load_mcp_config(config_path: str) -> dict[str, dict]:
    '''
    读取 mcp 配置文件

    Args:
        config_path: json文件所在路径

    Returns:
        配置文件的python字典表示

    '''

    try:
        with open(config_path, "r", encoding='utf-8') as f:
            config = json.load(f)

        def replace_env_vars(match):
            var_name = match.group(1)
            return os.getenv(var_name)
 
        config_str = re.sub(r'\$\{([^}]+)\}', replace_env_vars, json.dumps(config))

        # 解析替换后的JSON字符串
        config = json.loads(config_str)
        return config
    
    except FileNotFoundError:
        print(f"配置文件 '{config_path}' 不存在")
        return None
    except json.JSONDecodeError as e:
        print(f"配置文件不是有效的 JSON 格式: {e}")
        return None
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return None
    

if __name__ == "__main__":
    config = load_mcp_config('../mcp.json')
    print(config, type(config))