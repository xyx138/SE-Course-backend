import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agent import Agent
from utils.logger import MyLogger, logging
import json
from typing import Dict, List, Optional, Any, Union
from enum import Enum

logger = MyLogger(level=logging.INFO)
from dotenv import load_dotenv

load_dotenv()

PROJECT_PATH = os.getenv("PROJECT_PATH")

class TestType(str, Enum):
    """测试类型枚举"""
    UNIT_TEST = "unit_test"          # 单元测试
    INTEGRATION_TEST = "integration_test"  # 集成测试
    API_TEST = "api_test"            # API测试
    PERFORMANCE_TEST = "performance_test"  # 性能测试
    SECURITY_TEST = "security_test"   # 安全测试

class Language(str, Enum):
    """编程语言枚举"""
    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    CSHARP = "csharp"
    CPP = "cpp"

class TestAgent(Agent):
    """软件测试Agent，提供代码测试相关功能"""
    
    def __init__(self, api_key: str, base_url: str, model: str, label: str = None):
        super().__init__(api_key, base_url, model, label, [
            "bingcn",
            "time",
            "memory"
        ])
        
    def get_system_prompt(self) -> str:
        system_prompt = f'''
        你是一个软件测试专家，专注于帮助软件工程课程的大学生理解和实践软件测试。
        你需要帮助学生：
        1. 设计和生成各种类型的测试用例
        2. 分析代码并识别潜在的测试点
        3. 提供符合测试标准的最佳实践建议
        4. 解释测试概念和方法
        5. 评估测试覆盖率和质量
        
        请确保你的回答既专业又易于理解，适合软件工程课程的大学生学习使用。
        你提供的代码和解释应当具有教育意义，能帮助学生理解测试原理。
        '''
        
        return super().get_base_system_prompt() + '\n' + system_prompt
    
    async def generate_test_cases(self, code: str, language: Language, test_type: TestType, description: str = "") -> Dict:
        """
        为给定代码生成测试用例
        
        Args:
            code: 要测试的源代码
            language: 编程语言
            test_type: 测试类型
            description: 代码功能描述(可选)
            
        Returns:
            包含测试用例代码和解释的字典
        """
        try:
            prompt = f"""
            请为以下{language.value}代码生成{test_type.value}测试用例:
            
            ```{language.value}
            {code}
            ```
            
            代码功能描述：{description if description else "请分析代码功能"}
            
            生成的测试用例应该：
            1. 使用适合{language.value}语言的测试框架
            2. 涵盖主要功能路径和边缘情况
            3. 遵循测试最佳实践
            4. 包含测试用例的解释
            """
            
            response = await self.chat(prompt)
            return response
        
        except Exception as e:
            logger.error(f"生成测试用例时出错: {e}")
            return {
                "status": "error",
                "message": f"生成测试用例时出错: {str(e)}"
            }
    
    async def analyze_code_for_testability(self, code: str, language: Language) -> Dict:
        """
        分析代码的可测试性并提供改进建议
        
        Args:
            code: 要分析的代码
            language: 编程语言
            
        Returns:
            包含可测试性分析结果的字典
        """
        try:
            prompt = f"""
            请分析以下{language.value}代码的可测试性:
            
            ```{language.value}
            {code}
            ```
            
            分析应包括：
            1. 代码可测试性评分(1-10)
            2. 当前代码中影响测试的问题
            3. 具体改进建议，使代码更易于测试
            4. 应重点测试的部分
            5. 示例说明如何修改代码提高可测试性
            """
            
            response = await self.chat(prompt)
            return response
        
        except Exception as e:
            logger.error(f"分析代码可测试性时出错: {e}")
            return {
                "status": "error",
                "message": f"分析代码可测试性时出错: {str(e)}"
            }
    
    async def explain_testing_concept(self, concept: str) -> Dict:
        """
        解释软件测试相关概念
        
        Args:
            concept: 要解释的测试概念
            
        Returns:
            包含概念解释的字典
        """
        try:
            prompt = f"""
            请详细解释软件测试中的"{concept}"概念：
            
            解释应包括：
            1. 概念定义和基本原理
            2. 在软件测试中的应用场景
            3. 实现该测试类型的常用工具和框架
            4. 简单的代码示例说明如何应用
            5. 与其他测试概念的关系
            6. 在软件工程课程学习中的重要性
            """
            
            response = await self.chat(prompt)
            return response
        
        except Exception as e:
            logger.error(f"解释测试概念时出错: {e}")
            return {
                "status": "error",
                "message": f"解释测试概念时出错: {str(e)}"
            }
    
    async def generate_test_plan(self, project_description: str) -> Dict:
        """
        根据项目描述生成测试计划
        
        Args:
            project_description: 项目描述
            
        Returns:
            包含测试计划的字典
        """
        try:
            prompt = f"""
            根据以下项目描述，请生成一份完整的软件测试计划：
            
            项目描述：
            {project_description}
            
            测试计划应包括：
            1. 测试目标和范围
            2. 测试策略（测试级别、测试类型）
            3. 测试环境要求
            4. 测试用例设计方法
            5. 测试进度安排
            6. 风险评估和缓解措施
            7. 测试交付物
            8. 测试完成标准
            
            请确保测试计划适合软件工程课程项目的规模和特点。
            """
            
            response = await self.chat(prompt)
            return response
        
        except Exception as e:
            logger.error(f"生成测试计划时出错: {e}")
            return {
                "status": "error",
                "message": f"生成测试计划时出错: {str(e)}"
            }
    
    async def evaluate_test_coverage(self, code: str, tests: str, language: Language) -> Dict:
        """
        评估测试用例对代码的覆盖程度
        
        Args:
            code: 源代码
            tests: 测试代码
            language: 编程语言
            
        Returns:
            包含测试覆盖率评估的字典
        """
        try:
            prompt = f"""
            请评估以下测试代码对源代码的覆盖程度:
            
            源代码({language.value}):
            ```{language.value}
            {code}
            ```
            
            测试代码:
            ```{language.value}
            {tests}
            ```
            
            评估应包括：
            1. 功能覆盖率评估
            2. 分支/条件覆盖率评估
            3. 未覆盖的代码部分和边缘情况
            4. 改进测试覆盖率的建议
            5. 针对未覆盖部分的补充测试用例示例
            """
            
            response = await self.chat(prompt)
            return response
        
        except Exception as e:
            logger.error(f"评估测试覆盖率时出错: {e}")
            return {
                "status": "error",
                "message": f"评估测试覆盖率时出错: {str(e)}"
            }

async def main():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL")
    model = 'qwen-plus'
    test_agent = TestAgent(api_key=api_key, base_url=base_url, model=model)
    await test_agent.setup()
    
    # 测试代码分析功能
    code = """
def calculate_discount(price, discount_percent):
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("折扣百分比必须在0到100之间")
    discount = price * (discount_percent / 100)
    return price - discount
    """
    
    res = await test_agent.generate_test_cases(
        code=code, 
        language=Language.PYTHON, 
        test_type=TestType.UNIT_TEST, 
        description="计算商品折扣后的价格"
    )
    print(res)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 
    