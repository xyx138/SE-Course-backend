from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.storage import StorageContext
from vectorStore import VectorStore
from llama_index.embeddings.dashscope import (
    DashScopeEmbedding,
    DashScopeTextEmbeddingModels,
    DashScopeTextEmbeddingType,
)
from llama_index.postprocessor.dashscope_rerank import DashScopeRerank
from dotenv import load_dotenv  
import os
load_dotenv()
from utils.logger import MyLogger
import re
# from utils.splitter import split_questions
#
logger = MyLogger("retriever")

DB_PATH = os.getenv("PROJECT_PATH") + "/VectorStore"

class Retriever:
    def __init__(self, index_path: str = DB_PATH, model_name: str = DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V2, type: str = DashScopeTextEmbeddingType.TEXT_TYPE_DOCUMENT, chunk_cnt: int = 5, similarity_threshold: float = 0.1):
        self.index_path = index_path
        self.vector_store = VectorStore(index_path=DB_PATH, model_name=model_name, type=type)
        self.dashscope_rerank = DashScopeRerank(top_n=chunk_cnt, return_documents=True)
        self.chunk_cnt = chunk_cnt
        self.similarity_threshold = similarity_threshold
        self.error_patterns = {}  # 存储错误模式
        self.knowledge_points = {}  # 存储知识点

    def retrieve(self, query: str, label: str = None):

        print(f"检索的标签为：{label}")
        if label is None:
            return ""

        index = self.vector_store.load_index(label)
        retriever = index.as_retriever(
            similarity_top_k=5,
        )

        print(f"index为：{index}")    
    
        retrieve_chunk = retriever.retrieve(query)
        print(f"原始chunk为：{retrieve_chunk}")
        try:
            results = self.dashscope_rerank.postprocess_nodes(retrieve_chunk, query_str=query)
            print(f"rerank成功，重排后的chunk为：{results}")
        except:
            results = retrieve_chunk[:self.chunk_cnt]
            print(f"rerank失败，chunk为：{results}")
        chunk_text = ""
        chunk_show = ""
        for i in range(len(results)):
            if results[i].score >= self.similarity_threshold:
                chunk_text = chunk_text + f"## {i+1}:\n {results[i].text}\n"
                chunk_show = chunk_show + f"## {i+1}:\n {results[i].text}\nscore: {round(results[i].score,2)}\n"

        print(f"重排后的chunk为：{chunk_show}")
        # 返回文本
        return chunk_text

    def create_index(self, file_path: str, label: str):
        # 创建索引
        index = self.vector_store.create_index(file_path, label)
        return index

    def delete_index(self, label: str):
        try:
            res = self.vector_store.delete_index(label)
            return res
        except Exception as e:
            return f"删除向量索引失败: {e}"
    
    def retrieve_by_knowledge_point(self, knowledge_point: str, label: str = None):
        """检索包含指定知识点的所有题目"""
        if label is None:
            return {"error": "未选择知识库"}
        
        print(f"开始检索知识点: {knowledge_point}")
        print(f"使用知识库: {label}")
        
        index = self.vector_store.load_index(label)
        retriever = index.as_retriever(
            similarity_top_k=50,  # 检索更多，防止漏掉
        )
        query = knowledge_point
        retrieve_chunk = retriever.retrieve(query)
        print(f"向量检索返回结果数量: {len(retrieve_chunk)}")
        
        try:
            results = self.dashscope_rerank.postprocess_nodes(retrieve_chunk, query_str=query)
            print(f"重排序后结果数量: {len(results)}")
        except Exception as e:
            print(f"重排序失败: {str(e)}")
            results = retrieve_chunk

        if not results:
            return {"error": f"未找到与'{knowledge_point}'相关的习题"}

        matched_questions = []
        for i, result in enumerate(results):
            text = getattr(result.node, "text", None)
            if not text:
                print(f"结果 {i} 没有text字段")
                continue
                
            print(f"\n检查结果 {i}:")
            print(f"文本内容: {text[:200]}...")  # 只打印前200个字符
            
            kp_match = re.search(r"知识点:\s*(.*?)(?:\n|$)", text)
            if kp_match:
                kp_list = [k.strip() for k in kp_match.group(1).split(",") if k.strip()]
                print(f"提取的知识点列表: {kp_list}")
                
                if any(knowledge_point in k for k in kp_list):
                    print(f"找到匹配的知识点!")
                    matched_questions.append({
                        "question": text,
                        "knowledge_points": kp_list,
                        "score": round(result.score, 2)
                    })
                else:
                    print(f"知识点不匹配")
            else:
                print("未找到知识点字段")

        if not matched_questions:
            return {"error": f"未找到与'{knowledge_point}'相关的习题"}

        # 按相似度分数排序
        matched_questions.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"\n最终匹配到 {len(matched_questions)} 道题目")
        return {
            "questions": matched_questions,
            "total": len(matched_questions)
        }

    def analyze_error_patterns(self, history_messages: list):
        """分析历史对话中的错误模式"""
        error_patterns = {}
        
        for message in history_messages:
            if message["role"] == "user":
                # 分析用户回答中的错误
                content = message["content"]
                if "错误" in content or "不正确" in content:
                    # 提取错误相关的知识点
                    # 这里需要根据实际对话格式进行调整
                    pass
                    
        return error_patterns

    def track_knowledge_points(self, question: str, correct: bool):
        """跟踪知识点掌握情况"""
        # 从问题中提取知识点
        # 更新知识点掌握情况
        pass

    def get_knowledge_gaps(self):
        """获取知识盲点"""
        # 基于错误模式和知识点掌握情况分析知识盲点
        return {
            "weak_points": [],  # 薄弱知识点
            "error_patterns": self.error_patterns,
            "suggested_review": []  # 建议复习的内容
        }

if __name__ == "__main__":
    retriever = Retriever()
    logger.info(retriever.retrieve(query="什么是北京科技大学", label="public"))