import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from llmClient import LLMClient
from mcpClient import MCPClient
from utils.load_json import load_mcp_config
from utils.logger import MyLogger, logging, Colors
from collections import defaultdict
from dotenv import load_dotenv
import asyncio
from asyncio import CancelledError
import json
from retrieve import Retriever
from typing import List
load_dotenv()

PROJECT_PATH = os.getenv('PROJECT_PATH')

# 创建彩色日志记录器
logger = MyLogger(name="Agent", level=logging.INFO, colored=True)

all_servers = [
    "filesystem",
    "UML-MCP-Server",
    "bingcn",
    "fetch",
    # "memory",
    "time"
]

class Agent():
    '''agent = llm+tool'''
    
    @staticmethod
    def get_base_system_prompt() -> str:
        """获取基础系统提示词"""
        return f'''
        注意：
        1. 项目的根目录为{os.getenv('PROJECT_PATH')}, 所有的文件操作都基于这个根目录。
        2. 操作文件的文件路径参数名是path而不是file_path。move_file的参数分别为source和destination，不要增加path后缀。
        3. 输出文件默认保存到{os.getenv('PROJECT_PATH')}/static
        4. fetch_webpage的参数为result_id而不是id
        '''

    def __init__(self, api_key:str = os.getenv("DASHSCOPE_API_KEY"), base_url:str = os.getenv("DASHSCOPE_BASE_URL"), model: str = "qwen-plus", label: str = None, mcp_servers: List[str] = all_servers) -> None:
        '''初始化 llm 客户端和 mcp 客户端'''
        self.mcp_servers = mcp_servers
        self.system_prompt = self.get_system_prompt()
        self.llmClient = LLMClient(api_key, base_url, model, system_prompt=self.system_prompt)
        
        mcp_servers = load_mcp_config(PROJECT_PATH + '/mcp.json')['mcpServers']
        self.mcp_clients = defaultdict(MCPClient)
        
        self.tools = []
        for server_name, config in mcp_servers.items():
            if server_name in self.mcp_servers:
                command, args = config['command'], config['args']
                self.mcp_clients[server_name] = MCPClient(command, args)

        self.retriever = Retriever(similarity_threshold=0.5)
        self.label = None

    def get_system_prompt(self) -> str:
        return self.get_base_system_prompt()

    async def getMessages(self):
        return await self.llmClient.getMessages()

    async def update_label(self, label: str):
        '''
        更新索引标签

        args:
            label: 索引标签
        '''
        self.label = label
        logger.success(f"成功挂载知识库：{self.label}")

    async def write_messages(self):
        '''
        把上下文写入到文件
        '''
        all_text = [f"{message['role']}: {message['content']}" for message in self.llmClient.messages]
        all_text = '\n'.join(all_text)

        log_messages_dir = f"{PROJECT_PATH}/logs"
        os.makedirs(log_messages_dir, exist_ok=True)
        log_messages_file = f"{log_messages_dir}/messages.json"
        with open(log_messages_file, "w") as f:
            f.write(all_text)
        
        logger.info(f"上下文已保存到: {logger.color_text(log_messages_file, 'CYAN')}")
            
    async def setup(self):
        # 启动所有服务，并记录所有工具
        try:
            for name in self.mcp_clients:
                mcp_client = self.mcp_clients[name]
                await mcp_client.connect_to_server()
            
            for name, client in self.mcp_clients.items():
                tools = client.getTool()
                self.tools.extend([
                    {
                        "type": "function",
                        "function":{
                        "name" : tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                        } 
                    }
                
                for tool in tools])
            
            # 添加初始化完成的日志，显示 Agent 类型
            agent_type = self.__class__.__name__
            tool_count = logger.color_text(str(len(self.tools)), "YELLOW")
            logger.success(f"{agent_type} 初始化完成，可用工具数量: {tool_count}")

        except Exception as e:
            # 异常处理代码
            agent_type = self.__class__.__name__
            error_msg = logger.color_text(str(e), "RED")
            logger.error(f"{agent_type} 初始化失败: {error_msg}")
    
    async def chat(self, query: str) -> str:
        try:
            logger.info(f"检索标签: {logger.color_text(self.label or '无', 'CYAN')}")
            chunk_text = self.retriever.retrieve(query, self.label)
            
            if chunk_text:
                logger.info(f"获取到检索结果 ({logger.color_text(str(len(chunk_text)), 'YELLOW')} 字符)")
            else:
                logger.warning("未获取到检索结果")

            prompt = f"根据以下检索结果，回答用户的问题：\n{chunk_text}\n用户的问题是：{query}"
            if len(self.tools) > 0:
                res = await self.llmClient.chat(message=prompt, tools=self.tools)
            else:
                res = await self.llmClient.chat(message=prompt)
            
            tool_calls = res.choices[0].message.tool_calls

            # 多次调用工具
            while tool_calls:
                tool_names = [tool.function.name for tool in tool_calls]
                tool_names_str = ", ".join([logger.color_text(name, "CYAN") for name in tool_names])
                logger.info(f"正在调用工具: {tool_names_str}")
                
                # 确保工具调用在主线程中执行
                for tool_call in tool_calls:
                    func = tool_call.function
                    name, args = func.name, func.arguments
                    
                    args = json.loads(args)
                    target_client = None
                    for mcp_name, mcp_client in self.mcp_clients.items():
                        if mcp_client.have_tool(name):
                            target_client = mcp_client
                            break
                    
                    if target_client:
                        try:
                            # 检查客户端连接状态，如果需要则重新连接
                            if not target_client._connected or target_client.session is None:
                                logger.info(f"重新连接客户端: {logger.color_text(name, 'CYAN')}")
                                await target_client.connect_to_server()
                                
                            # 调用工具
                            tool_res = await target_client.call_tool(name, args)  
                            logger.success(f"工具 {logger.color_text(name, 'CYAN')} 调用成功")

                            await self.llmClient.add_tool_call(
                                role="tool", 
                                content=tool_res.content, 
                                tool_call_id=tool_call.id
                            )
                        except Exception as e:
                            error_msg = logger.color_text(str(e), "RED")
                            logger.error(f"工具 {logger.color_text(name, 'CYAN')} 调用出错: {error_msg}")
                            
                            # 如果是事件循环关闭错误，尝试重新连接所有客户端
                            if "Event loop is closed" in str(e):
                                logger.warning("检测到事件循环关闭错误，尝试重新连接所有客户端")
                                try:
                                    await self.reconnect_all_clients()
                                    # 重试工具调用
                                    try:
                                        tool_res = await target_client.call_tool(name, args)
                                        logger.success(f"重新连接后工具 {logger.color_text(name, 'CYAN')} 调用成功")

                                        await self.llmClient.add_tool_call(
                                            role="tool", 
                                            content=tool_res.content, 
                                            tool_call_id=tool_call.id
                                        )
                                    except Exception as retry_e:
                                        retry_error = logger.color_text(str(retry_e), "RED")
                                        logger.error(f"重试调用工具 {logger.color_text(name, 'CYAN')} 失败: {retry_error}")
                                        await self.llmClient.add_tool_call(
                                            role="tool", 
                                            content=f"工具{name}调用出错: {str(retry_e)}", 
                                            tool_call_id=tool_call.id
                                        )
                                except Exception as reconnect_e:
                                    reconnect_error = logger.color_text(str(reconnect_e), "RED")
                                    logger.error(f"重新连接客户端失败: {reconnect_error}")
                                    await self.llmClient.add_tool_call(
                                        role="tool", 
                                        content=f"工具{name}调用出错: 事件循环已关闭且无法重新连接 - {str(e)}", 
                                        tool_call_id=tool_call.id
                                    )

                if len(self.tools) > 0:
                    res = await self.llmClient.chat(message=None, tools=self.tools)
                else:
                    res = await self.llmClient.chat(message=None)
                tool_calls = res.choices[0].message.tool_calls if res.choices[0].message.tool_calls else None
            
            logger.info("回复结果")
            # await self.write_messages() # 写入上下文信息
            return {
                "status": "success",
                "message": res.choices[0].message.content
            }
        
        except Exception as e:
            logger.error(f"聊天过程中出错: {e}")
            return {
                "status": "error",
                "message": {e}
            }

    async def delete_index(self, label: str):
        res = self.retriever.delete_index(label)
        if res == 1:
            logger.info(f"删除向量索引成功，索引标签为{label}")
        else:
            logger.error(f"删除向量索引失败: {res}")


    async def create_index(self, files_dir: str, label: str):
        '''
        创建向量索引

        args:
            file_path: 文件路径
            label: 索引标签
        '''
        index = self.retriever.create_index(files_dir, label)
        logger.info(f"创建向量索引成功，索引标签为{label}")
        return index



    async def cleanup(self):
        """清理所有客户端资源，必须和 connect_to_server 在同一任务中执行"""
        for name, client in self.mcp_clients.items():
            try:
                # 直接 await，不要 shield，也不要并行 gather
                await client.cleanup()
                logger.info(f"客户端 {name} 清理完成")
            except Exception as e:
                logger.error(f"清理客户端 {name} 时出错: {e}")

    async def reconnect_all_clients(self):
        """尝试重新连接所有MCP客户端"""
        for name, client in self.mcp_clients.items():
            try:
                await client.connect_to_server()
                logger.info(f"重新连接客户端 {name} 成功")
            except Exception as e:
                logger.error(f"重新连接客户端 {name} 失败: {e}")




api_key = os.getenv("DASHSCOPE_API_KEY")
base_url = os.getenv("DASHSCOPE_BASE_URL")
model = 'qwen-plus'

prompt = f'''
我想要设计一个电商订单管理系统。画出该系统的类图。
'''

async def main():
    agent = Agent(api_key, base_url, model)
    await agent.setup()
    # 这里可以添加更多使用 agent 的代码
    # res = await agent.chat(prompt)
    # print(f"回复结果为：{res}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序运行时出错: {e}")
