from openai import OpenAI
import json
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

'''大模型客户端'''
class LLMClient():
    
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        '''初始化大模型客户端'''
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.messages = [
            {
                "role": 'system',
                "content": f"你是一个有用的助手。必要的时候，你可以直接调用工具来实现用户的需求。如果你能够通过工具调用实现该功能，就不需要回复实现该功能的代码了。项目的根目录为{os.getenv('PROJECT_PATH')}, 所有的文件操作都基于这个根目录。所有的工具调用的参数要严格按照工具的定义来。操作文件的文件路径参数名是path而不是file_path。对于地点相关的问题，必要的时候你应该优先获取地点的经纬度，然后使用amap-maps工具来获取地点的详细信息。"
            }
        ]
        self.model = model

    '''结合tools调用一次LLM'''
    async def chat(self, message: str =None, tools: List[dict] = None):
        
        if message:
            self.messages.append(
                {
                    "role": "user",
                    "content": message
                }
            )

        try:
            response = self.client.chat.completions.create(
                messages=self.messages,
                model=self.model,
                tool_choice='auto',
                tools=tools,
                # parallel_tool_calls=True
            )
            print("LLM调用结果为：{}".format(response))
        except Exception as emg:
            print( f"调用LLM失败，错误信息为{emg}")

        role, content, tool_calls = response.choices[0].message.role, response.choices[0].message.content, response.choices[0].message.tool_calls

        self.messages.append(
            {
                "role": role,
                "content": content,
                "tool_calls": tool_calls
            }
        )
        
        return response
    
    '''增添messages'''
    async def add_content(self, role: str, content: str):
        self.messages.append(
            {
                "role": role,
                "content": content
            }
        )

        

    async def add_tool_call(self, role: str, content: str, tool_call_id: str):
        self.messages.append(
            {
                "role": role,
                "content": content,
                "tool_call_id" : tool_call_id
            }
        )
    

        
    
if __name__ == "__main__":
    load_dotenv()
    import asyncio

    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL")

    model = "qwen-plus"

    llmclient = LLMClient(api_key=api_key, base_url=base_url, model=model)
    res = asyncio.run(llmclient.chat('你好'))
    
    print(res)