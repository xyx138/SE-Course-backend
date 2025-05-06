from llmClient import LLMClient
from mcpClient import MCPClient

from utils.load_json import load_mcp_config
from utils.logger import MyLogger, logging
from collections import defaultdict
from dotenv import load_dotenv
import os
import asyncio
import sys
from asyncio import CancelledError
import json
from retrieve import Retriever

load_dotenv()

PROJECT_PATH = os.getenv('PROJECT_PATH')

logger = MyLogger(log_file="logs/app.log", level=logging.INFO)


class Agent():
    '''agent = llm+tool'''
    
    def __init__(self, api_key:str , base_url:str , model: str = None, label: str = 'public') -> None:
        '''初始化 llm 客户端和 mcp 客户端'''

        logger.info("初始化LLM和MCP客户端")

        self.llmClient = LLMClient(api_key, base_url, model)
        
        mcp_servers = load_mcp_config(PROJECT_PATH + '/mcp.json')['mcpServers']
        self.mcp_clients = defaultdict(MCPClient)
        self.tools = []
        for server_name, config in mcp_servers.items():
            command, args = config['command'], config['args']
            self.mcp_clients[server_name] = MCPClient(command, args)

        self.retriever = Retriever(similarity_threshold=0.5)
        self.label = label

    async def update_label(self, label: str):
        '''
        更新索引标签

        args:
            label: 索引标签
        '''

        self.label = label
        print(f"成功挂载知识库：{self.label}")

    async def write_messages(self):
        '''
        把上下文写入到文件
        '''

        all_text = [f"{message['role']}: {message['content']}" for message in self.llmClient.messages]
        all_text = '\n'.join(all_text)
        with open(f"{PROJECT_PATH}/src/logs/messages.json", "w") as f:
            f.write(all_text)
            

    async def setup(self):
        # 启动所有服务，并记录所有工具

        logger.info("启动MCP服务器")

        try:
            for name in self.mcp_clients:
                mcp_client = self.mcp_clients[name]
                await mcp_client.connect_to_server()
            
            
            for name, client in self.mcp_clients.items():
                tools = client.getTool()
                # print(f"获取到的工具为：{tools}")
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
            print(f"获取到的工具为：{self.tools}")

        except Exception as e:
            # 异常处理代码
            print(f"发生错误: {e}")
            # 可能的恢复策略
    
    async def chat(self, query: str) -> str:
        try:
            logger.info(f"开始检索")
            print(f"检索的标签为：{self.label}")
            chunk_text = self.retriever.retrieve(query, self.label)
            print(f"检索结果为：{chunk_text}")

            prompt = f"根据以下检索结果，回答用户的问题：\n{chunk_text}\n用户的问题是：{query}"

            logger.info(f"调用LLM")
            res = await self.llmClient.chat(prompt, self.tools)
            
            tool_calls = res.choices[0].message.tool_calls

            while tool_calls:
                logger.info("调用工具")
                tool_names = [tool.function.name for tool in tool_calls]

                print(f"调用的工具包括：{tool_names}")
                # 确保工具调用在主线程中执行
                for tool_call in tool_calls:
                    func = tool_call.function
                    name, args = func.name, func.arguments
                    logger.info(f"调用工具:{name}")
                    
                    args = json.loads(args)
                    target_client = None
                    for mcp_name, mcp_client in self.mcp_clients.items():
                        if mcp_client.have_tool(name):
                            target_client = mcp_client
                            print(f"找到{name}对应的mcp_client:{target_client}")
                            break
                    
                    if target_client:
                        print(f"调用{name}，参数为{args}")
                        try:
                            # 添加超时处理
                            tool_res = await asyncio.wait_for(
                                target_client.call_tool(name, args),
                                timeout=30.0
                            )
                            print(f"调用{name}的执行结果为{tool_res}")
                            await self.llmClient.add_tool_call(
                                role="tool", 
                                content=tool_res.content, 
                                tool_call_id=tool_call.id
                            )
                        except asyncio.TimeoutError:
                            print(f"工具{name}调用超时")
                            await self.llmClient.add_tool_call(
                                role="tool", 
                                content=f"工具{name}调用超时", 
                                tool_call_id=tool_call.id
                            )
                        except Exception as e:
                            print(f"工具{name}调用出错: {e}")
                            await self.llmClient.add_tool_call(
                                role="tool", 
                                content=f"工具{name}调用出错: {str(e)}", 
                                tool_call_id=tool_call.id
                            )

                res = await self.llmClient.chat(message=None, tools=self.tools)
                tool_calls = res.choices[0].message.tool_calls if res.choices[0].message.tool_calls else None
            
            logger.info("回复结果")
            await self.write_messages() # 写入上下文信息
            return res.choices[0].message.content
        except Exception as e:
            logger.error(f"聊天过程中出错: {e}")
            return f"处理请求时出错: {str(e)}"


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




load_dotenv()
api_key = os.getenv("DASHSCOPE_API_KEY")
base_url = os.getenv("DASHSCOPE_BASE_URL")
model = 'qwen-plus'

async def main():


    agent = Agent(api_key, base_url, model)

    await agent.setup()
    # 这里可以添加更多使用 agent 的代码
    await agent.chat("你可以操作哪一个文件夹？")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序运行时出错: {e}")
