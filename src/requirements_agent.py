import json
import os
from typing import Dict, List, Optional
from pydantic import BaseModel
from llmClient import LLMClient
from dotenv import load_dotenv


# 加载环境变量
load_dotenv()

class Requirement(BaseModel):
    """需求模型"""
    id: str
    type: str  # 功能需求/非功能需求
    category: str  # 具体类别
    description: str
    priority: str  # 高/中/低
    dependencies: List[str] = []
    acceptance_criteria: List[str] = []

class RequirementsAnalysis:
    """需求分析智能体"""
    def __init__(self):
        # 从环境变量获取配置
        api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL")
        model = os.getenv("DASHSCOPE_MODEL", "qwen-plus")
        
        if not all([api_key, base_url, model]):
            raise ValueError("缺少必要的环境变量配置：DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, DASHSCOPE_MODEL")
            
        self.llm_client = LLMClient(api_key, base_url, model)
        self.requirements: List[Requirement] = []
        
    def analyze_requirements(self, user_input: str) -> Dict:
        """分析用户输入的需求"""
        prompt = f"""
        请分析以下需求，提取关键信息：
        {user_input}
        
        请以JSON格式返回，包含以下字段：
        - 功能模块列表
        - 非功能需求列表
        - 业务规则和约束条件
        - 优先级建议
        """
        
        response = self.llm_client.chat(prompt)
        try:
            analysis = json.loads(response)
            return analysis
        except:
            return {"error": "需求解析失败，请重试"}
    
    def generate_use_case_diagram(self, requirements: List[Requirement]) -> str:
        """生成用例图的PlantUML代码"""
        prompt = f"""
        请根据以下需求生成用例图的PlantUML代码：
        {json.dumps([req.dict() for req in requirements], ensure_ascii=False, indent=2)}
        
        要求：
        1. 使用PlantUML语法
        2. 包含所有功能需求作为用例
        3. 添加适当的角色（Actor）
        4. 使用合适的布局和样式
        5. 只返回PlantUML代码，不要包含其他说明
        """
        
        response = self.llm_client.chat(prompt)
        return response.strip()
    
    def generate_requirement_doc(self, requirements: List[Requirement]) -> str:
        """生成需求文档"""
        # 生成用户故事
        user_stories = self._generate_user_stories(requirements)
        
        # 生成用例图
        use_case_diagram = self._generate_use_case_diagram(requirements)
        
        # 生成需求规格说明书
        srs = self._generate_srs(requirements)
        
        # 组合成完整文档
        doc = f"""# 需求规格说明书

## 1. 用户故事
{user_stories}

## 2. 用例图
```mermaid
{use_case_diagram}
```

## 3. 详细需求
{srs}
"""
        return doc
    
    def _generate_user_stories(self, requirements: List[Requirement]) -> str:
        """生成用户故事"""
        stories = []
        for req in requirements:
            if req.type == "功能需求":
                story = f"""### {req.category}
- 作为[角色]
- 我想要[功能]
- 以便于[价值]
"""
                stories.append(story)
        return "\n".join(stories)
    
    def _generate_use_case_diagram(self, requirements: List[Requirement]) -> str:
        """生成用例图"""
        diagram = """graph TD
"""
        for req in requirements:
            if req.type == "功能需求":
                diagram += f"    {req.id}[{req.category}]\n"
        return diagram
    
    def _generate_srs(self, requirements: List[Requirement]) -> str:
        """生成需求规格说明书"""
        srs = []
        for req in requirements:
            section = f"""### {req.category}
- 描述：{req.description}
- 优先级：{req.priority}
- 验收标准：
"""
            for criteria in req.acceptance_criteria:
                section += f"  - {criteria}\n"
            srs.append(section)
        return "\n".join(srs)

    def clarify_requirement(self, user_input: str, history: List[dict]) -> dict:
        prompt = f"""
        你是需求分析师。用户的需求描述如下：
        {user_input}
        已有澄清历史：{json.dumps(history, ensure_ascii=False)}
        请判断需求是否还需澄清，如果需要，给出一个具体追问；如果不需要，回复"需求已完善"。
        返回格式：{{"clarify": "你的追问或'需求已完善'"}}。
        """
        response = self.llm_client.chat(prompt)
        return json.loads(response)

    def generate_srs_with_template(self, user_input: str, clarify_history: list, template: str) -> str:
        """
        根据自定义SRS模板、用户原始需求和澄清对话历史，生成完整需求文档
        """
        prompt = f"""
你是专业的软件需求分析师，请根据以下SRS模板、用户需求描述和澄清对话，自动补全并生成一份完整的高质量软件需求规格说明书（SRS）。
【SRS模板】：
{template}

【用户需求描述】：
{user_input}

【澄清对话历史】：
{json.dumps(clarify_history, ensure_ascii=False, indent=2)}

请严格按照模板结构输出，内容尽量详细、专业，所有空白部分都要结合上下文自动补全。
"""
        response = self.llm_client.chat(prompt)
        return response.strip()