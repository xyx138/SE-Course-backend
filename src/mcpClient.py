import asyncio
import os
import platform
from contextlib import AsyncExitStack

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

from utils.logger import MyLogger, logging

logger = MyLogger(level=logging.INFO)

# 检测是否为Windows环境
IS_WINDOWS = platform.system() == "Windows"

class MCPClient:
    def __init__(self, command: str, args: list[str]):
        self.command = command
        self.args = args
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        self._lock = asyncio.Lock()
        self._connected = False
        self.tools: list = []
        self.tool_names: list[str] = []

    async def connect_to_server(self):
        """连接到 MCP 服务器，使用官方 stdio_client"""
        async with self._lock:
            if self._connected:
                logger.info("已经连接到服务器，跳过重复连接")
                return

            logger.info(f"开始连接服务器: {self.command} {' '.join(self.args)}")
            
            # 设置环境变量
            env = os.environ.copy()
            if IS_WINDOWS:
                # Windows环境下可能需要额外设置
                env["PYTHONIOENCODING"] = "utf-8"
                
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=env,
                shell=IS_WINDOWS  # Windows下使用shell=True可能更可靠
            )
            
            try:
                # 1. 使用 stdio_client 获取 stdio, write
                stdio, write = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                logger.info("stdio_client 已连接子进程")

                # 2. 创建 MCP 会话
                self.session = await self.exit_stack.enter_async_context(
                    ClientSession(stdio, write)
                )
                await self.session.initialize()
                logger.info("会话初始化成功")

                # 获取可用工具
                response = await self.session.list_tools()
                self.tools = response.tools
                self.tool_names = [tool.name for tool in self.tools]
                logger.info(f"连接成功，可用工具: {self.tool_names}")

                self._connected = True
            except Exception as e:
                logger.error(f"连接服务器失败: {e}")
                if IS_WINDOWS and isinstance(e, FileNotFoundError) and self.command in ["npx", "npx.cmd"]:
                    logger.error("Windows环境下可能需要全局安装相关NPM包，请尝试运行: npm install -g @modelcontextprotocol/server-filesystem")
                raise

    async def call_tool(self, tool_name: str, args: dict):
        if not self.session or not self._connected:
            raise RuntimeError("未连接到服务器")
        if tool_name not in self.tool_names:
            available = ", ".join(self.tool_names)
            raise ValueError(f"工具 '{tool_name}' 不可用。可用工具: {available}")
        
        # logger.info(f"调用工具 {tool_name}，参数: {args}")
        
        try:
            return await self.session.call_tool(tool_name, args)
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {e}")
            # Windows环境下可能需要特殊处理路径参数
            if IS_WINDOWS and "path" in args:
                # 尝试修复路径格式
                if isinstance(args["path"], str):
                    args["path"] = args["path"].replace('/', '\\')
                    logger.info(f"尝试使用Windows路径格式重新调用: {args['path']}")
                    return await self.session.call_tool(tool_name, args)
            raise

    def have_tool(self, tool_name: str) -> bool:
        return tool_name in self.tool_names

    def getTool(self) -> list:
        return self.tools

    async def cleanup(self):
        """清理所有资源"""
        await self.exit_stack.aclose()
        logger.info("资源清理完成")

async def main():
    # 测试 MCPClient
    command = 'npx.cmd' if IS_WINDOWS else 'npx'
    args = ['-y', '@modelcontextprotocol/server-filesystem', os.getcwd()]
    client = MCPClient(command, args)
    try:
        await client.connect_to_server()
        # 列出工具
        for tool in client.getTool():
            print(f"工具: {tool.name} - {tool.description}")
        # 调用 read_file
        test_file = os.path.join(os.getcwd(), 'README.md')
        if client.have_tool('read_file'):
            res = await client.call_tool('read_file', {'path': test_file})
            print(res.content)
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
