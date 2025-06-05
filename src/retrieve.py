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
from utils.logger import MyLogger, logging, Colors
import re
# from utils.splitter import split_questions
#

# 创建彩色日志记录器
logger = MyLogger(name="Retriever", level=logging.INFO, colored=True)

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
        if label is None:
            return ""

        index = self.vector_store.load_index(label)
        retriever = index.as_retriever(
            similarity_top_k=5,
        )
    
        retrieve_chunk = retriever.retrieve(query)
        try:
            results = self.dashscope_rerank.postprocess_nodes(retrieve_chunk, query_str=query)
            count = logger.color_text(str(len(results)), "YELLOW")
            logger.success(f"重排序成功，获取到{count}个结果")
        except Exception as e:
            error_msg = logger.color_text(str(e), "RED")
            logger.warning(f"重排序失败: {error_msg}，使用原始结果")
            results = retrieve_chunk[:self.chunk_cnt]
            
        chunk_text = ""
        valid_count = 0
        for i in range(len(results)):
            if results[i].score >= self.similarity_threshold:
                chunk_text = chunk_text + f"## {i+1}:\n {results[i].text}\n"
                valid_count += 1
        
        if valid_count > 0:
            threshold = logger.color_text(str(self.similarity_threshold), "CYAN")
            count = logger.color_text(str(valid_count), "YELLOW")
            logger.info(f"使用相似度阈值 {threshold}，获取了 {count} 个有效结果")
                
        return chunk_text

    def create_index(self, file_path: str, label: str):
        # 创建索引
        path = logger.color_text(file_path, "CYAN")
        label_str = logger.color_text(label, "YELLOW")
        logger.info(f"正在为 {path} 创建索引: {label_str}")
        
        index = self.vector_store.create_index(file_path, label)
        logger.success(f"索引 {label_str} 创建成功")
        return index

    def delete_index(self, label: str):
        try:
            label_str = logger.color_text(label, "YELLOW")
            logger.info(f"正在删除索引: {label_str}")
            
            res = self.vector_store.delete_index(label)
            logger.success(f"索引 {label_str} 删除成功")
            return res
        except Exception as e:
            error_msg = logger.color_text(str(e), "RED")
            logger.error(f"删除向量索引失败: {error_msg}")
            return f"删除向量索引失败: {e}"
    
    def retrieve_by_knowledge_point(self, knowledge_point: str, label: str = None):
        """检索包含指定知识点的所有题目"""
        if label is None:
            return {"error": "未选择知识库"}
        
        kp = logger.color_text(knowledge_point, "CYAN")
        label_str = logger.color_text(label, "YELLOW")
        logger.info(f"检索知识点: {kp}, 知识库: {label_str}")
        
        index = self.vector_store.load_index(label)
        retriever = index.as_retriever(
            similarity_top_k=50,  # 检索更多，防止漏掉
        )
        query = knowledge_point
        retrieve_chunk = retriever.retrieve(query)
        
        try:
            results = self.dashscope_rerank.postprocess_nodes(retrieve_chunk, query_str=query)
            count = logger.color_text(str(len(results)), "YELLOW")
            logger.info(f"重排序后结果数量: {count}")
        except Exception as e:
            error_msg = logger.color_text(str(e), "RED")
            logger.warning(f"重排序失败: {error_msg}，使用原始结果")
            results = retrieve_chunk

        if not results:
            logger.warning(f"未找到与 {kp} 相关的习题")
            return {"error": f"未找到与'{knowledge_point}'相关的习题"}

        matched_questions = []
        for i, result in enumerate(results):
            text = getattr(result.node, "text", None)
            if not text:
                continue
                
            kp_match = re.search(r"知识点:\s*(.*?)(?:\n|$)", text)
            if kp_match:
                kp_list = [k.strip() for k in kp_match.group(1).split(",") if k.strip()]
                
                if any(knowledge_point in k for k in kp_list):
                    matched_questions.append({
                        "question": text,
                        "knowledge_points": kp_list,
                        "score": round(result.score, 2)
                    })
            
        if not matched_questions:
            logger.warning(f"未找到与 {kp} 相关的习题")
            return {"error": f"未找到与'{knowledge_point}'相关的习题"}

        # 按相似度分数排序
        matched_questions.sort(key=lambda x: x["score"], reverse=True)
        
        count = logger.color_text(str(len(matched_questions)), "YELLOW")
        logger.success(f"匹配到 {count} 道题目")
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
    result = retriever.retrieve(query="什么是北京科技大学", label="public")
    if result:
        logger.success("检索成功")
        print(result)
    else:
        logger.warning("未找到相关内容")