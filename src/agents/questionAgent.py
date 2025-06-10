from dotenv import load_dotenv
import os
import asyncio
# import aiomysql
from agents.agent import Agent
from enum import Enum
import json
from typing import Dict, List, Optional, Union

load_dotenv()

PROJECT_PATH = os.getenv('PROJECT_PATH')

class QuestionType(str, Enum):
    """题目类型枚举"""
    MULTIPLE_CHOICE = "选择题"
    FILL_IN_THE_BLANK = "填空题"
    TRUE_OR_FALSE = "判断题"
    SHORT_ANSWER = "简答题"


class QuestionDifficulty(str, Enum):
    """题目难度枚举"""
    EASY = "简单"
    MEDIUM = "中等"
    HARD = "困难"

class questionAgent(Agent):
    """软件工程习题解答助手"""
    
    def __init__(self, api_key: str, base_url: str, model: str = None, label: str = None) -> None:
        super().__init__(api_key, base_url, model, label, [
            # "memory"
        ])
        
    def get_system_prompt(self) -> str:
        return super().get_base_system_prompt() + """你是一个专业的软件工程教育专家，擅长出题和批改试题。
        你需要：
        1. 根据要求生成高质量的软件工程相关习题
        2. 对学生的答案进行专业的点评和解析
        3. 提供详细的参考答案和解题思路
        4. 指出答案中的优点和需要改进的地方

        在生成题目时：
        - 确保题目难度适中，符合学习阶段
        - 题目描述清晰，要求明确
        - 涵盖软件工程的重要概念和实践
        - 结合实际案例，培养实践能力

        在批改答案时：
        - 给出客观公正的评分
        - 详细说明得分点和失分点
        - 提供改进建议和学习方向
        - 鼓励学生思考和创新
        """



    async def generate_question(
        self,
        topic: str,
        question_type: QuestionType,
        difficulty: str
    ) -> Dict:
        """
        生成习题
        
        Args:
            topic: 题目主题/知识点
            question_type: 题目类型
            difficulty: 题目难度
            
        Returns:
            Dict: 包含题目信息的字典
        """
        prompt = f"""请生成一道软件工程相关的{difficulty}难度的{question_type.value}。
        要求：
        1. 主题/知识点：{topic}
        2. 题目描述要清晰准确
        3. 如果是选择题，需要提供4个选项
        4. 必须提供详细的参考答案和解题思路
        5. 说明考察的重点和难点

        输出格式：
        {{
            "question": "题目描述",
            "type": "题目类型",
            "difficulty": "难度",
            "options": ["A. 选项1", "B. 选项2", ...],  // 选择题必须提供
            "reference_answer": "参考答案",
            "analysis": "解题思路和重点分析",
            "key_points": ["考察重点1", "考察重点2", ...]
        }}

        请确保输出是有效的JSON格式。"""

        try:
            response = await self.chat(prompt)
            # 解析JSON响应
            question_data = json.loads(response)
            question_data["status"] = "success"
            return question_data
        except Exception as e:
            return {
                "status": "error",
                "message": f"生成题目时出错: {str(e)}"
            }

    # 解释用户输入的题目
    async def explain_question(
        self,
        question: str
    ) -> Dict:
        """
        解释用户输入的题目

        Args:
            question: 题目描述
            
        Returns:
            Dict: 包含解释结果的字典
        """
        prompt = f"""请对以下软件工程题目进行解释：
        题目：
        {question}

        要求：
        1. 给出详细的解释
        2. 说明题目考察的重点和难点
        3. 提供解题思路和参考答案

        输出格式：
        {{
            "explanation": "详细解释",
            "key_points": ["考察重点1", "考察重点2", ...],
            "reference_answer": "参考答案"
        }}

        请确保输出是有效的JSON格式。"""

        try:
            response = await self.chat(prompt)
            # 解析JSON响应
            explanation_result = response
            explanation_result["status"] = "success"
            return explanation_result
        except Exception as e:
            return {
                "status": "error",
                "message": f"解释题目时出错: {str(e)}"
            }

    async def grade_answer(
        self,
        question: str,
        student_answer: str,
        reference_answer: str,
        question_type: QuestionType,
        max_score: int = 100
    ) -> Dict:
        """
        批改答案
        
        Args:
            question: 题目描述
            student_answer: 学生答案
            reference_answer: 参考答案
            question_type: 题目类型
            max_score: 满分值
            
        Returns:
            Dict: 包含批改结果的字典
        """
        prompt = f"""请对以下软件工程{question_type.value}的答案进行批改和点评：

        题目：
        {question}

        学生答案：
        {student_answer}

        参考答案：
        {reference_answer}

        要求：
        1. 给出0-{max_score}分的评分
        2. 详细说明得分点和失分点
        3. 提供具体的改进建议
        4. 指出答案中的亮点和创新点（如果有）

        输出格式：
        {{
            "score": 分数,
            "scoring_points": [
                {{"point": "得分点1", "score": 得分}},
                {{"point": "失分点1", "deduction": 扣分}},
                ...
            ],
            "comments": "总体评价",
            "suggestions": ["改进建议1", "改进建议2", ...],
            "highlights": ["亮点1", "亮点2", ...]  // 如果没有可以为空列表
        }}

        请确保输出是有效的JSON格式。"""

        try:
            response = await self.chat(prompt)
            # 解析JSON响应
            grading_result = json.loads(response)
            grading_result["status"] = "success"
            return grading_result
        except Exception as e:
            return {
                "status": "error",
                "message": f"批改答案时出错: {str(e)}"
            }

    async def grade_practice_set(
        self,
        practice_set: List[Dict],
        student_answers: List[Dict],
        reference_answers: List[Dict]
    ) -> Dict:
        """
        批改练习题集
        
        Args:
            practice_set: 题目集
            student_answers: 学生答案集
            reference_answers: 参考答案集
            
        Returns:
            Dict: 包含批改结果的字典
        """
        prompt = f"""请对以下软件工程练习题集进行批改：

        题目集：
        {practice_set}

        学生答案集：
        {student_answers}

        参考答案集：
        {reference_answers}

        要求：
        1. 给出详细的批改结果
        2. 详细说明得分点和失分点
        3. 提供具体的改进建议
        4. 指出答案中的亮点和创新点（如果有）

        输出格式：
        {{
                "score": "总分", 
                "scoring_points": [ 
                    {{
                        "id": "题目id",
                        "point": "对应知识点", 
                        "score": "得分", 
                        "deduction": "扣分" 
                    }},
                    ...
                ],
                "comments": "总体评价",  
                "suggestions": ["改进建议1", "改进建议2", ...], 
                "highlights": ["亮点1", "亮点2", ...] 
        }}

        请确保输出是有效的JSON格式。"""

        try:
            response = await self.chat(prompt)
            # 解析JSON响应
            grading_result = response
            grading_result["status"] = "success"
            return grading_result
        except Exception as e:
            return {
                "status": "error",
                "message": f"批改练习题集时出错: {str(e)}"
            }   
        
    

    async def generate_practice_set(
        self,
        topics: List[str],
        num_questions: int = 5,
        difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM,
        question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    ) -> Dict:
        """
        生成练习题集
        
        Args:
            topics: 知识点列表
            num_questions: 题目数量
            difficulty: 题目难度
            question_type: 题目类型
        Returns:
            Dict: 包含题目集的字典
        """
        prompt = f"""请生成一套包含{num_questions}道软件工程练习题，难度为{difficulty.value}，题型为{question_type.value}。

        知识点范围：
        {', '.join(topics)}

        要求：
        1. 题型多样，包括选择题、填空题和简答题
        2. 每道题都要提供参考答案和解析
        3. 难度递进，由易到难
        4. 覆盖所有给定的知识点

        
        你只需要返回一个json字符串,包含以下内容，不要输出多余的前后缀：


        {{
            "questions": [
                {{
                    "id": 1,
                    "type": "题目类型",
                    "value": "分值"
                    "question": "题目描述",
                    "options": ["选项1", "选项2", ...],  // 选择题必须提供
                    "reference_answer": "参考答案",
                    "analysis": "解题思路",
                    "topics": ["涉及知识点1", "涉及知识点2", ...]
                }},
                ...
            ],
            "total_points": 总分,
            "estimated_time": "预计完成时间（分钟）",
            "difficulty_distribution": {{
                "easy": 简单题数量,
                "medium": 中等题数量,
                "hard": 困难题数量
            }}
        }}

        """

        try:
            response = await self.chat(prompt)
            return response
        except Exception as e:
            return {
                "status": "error",
                "message": f"生成练习题集时出错: {str(e)}"
            }

    async def quick_answer(
        self,
        question: str
    ) -> Dict:
        """
        快速回答软件工程相关问题
        
        Args:
            question: 用户提问的问题
            
        Returns:
            Dict: 包含回答的字典
        """
        prompt = f"""请针对以下软件工程相关问题提供简洁明了的回答：

        问题：
        {question}

        要求：
        1. 回答应该准确、专业，但简洁明了
        2. 如果涉及多种观点或方法，请简要列出
        3. 可以适当引用经典理论或最佳实践
        4. 如果问题不够明确，可以提供最可能的解释
        5. 回答中应包含关键概念的简短解释

        你只需要返回一个json字符串,包含以下内容，不要输出多余的前后缀：
        
        {{
            "answer": "详细回答",
            "key_concepts": ["关键概念1", "关键概念2", ...],
            "references": ["参考资料1", "参考资料2", ...] (可选)
        }}

       """

        try:
            response = await self.chat(prompt)
            # 解析JSON响应
            answer_data = json.loads(response)
            answer_data["status"] = "success"
            return answer_data
        except Exception as e:
            return {
                "status": "error",
                "message": f"回答问题时出错: {str(e)}"
            }



