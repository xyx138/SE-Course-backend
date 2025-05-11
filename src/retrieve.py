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
 
logger = MyLogger("retriever")

DB_PATH = os.getenv("PROJECT_PATH") + "/VectorStore"

class Retriever:
    def __init__(self, index_path: str = DB_PATH, model_name: str = DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V2, type: str = DashScopeTextEmbeddingType.TEXT_TYPE_DOCUMENT, chunk_cnt: int = 5, similarity_threshold: float = 0.3):
        self.index_path = index_path
        self.vector_store = VectorStore(index_path=DB_PATH, model_name=model_name, type=type)
        self.dashscope_rerank = DashScopeRerank(top_n=chunk_cnt, return_documents=True)
        self.chunk_cnt = chunk_cnt
        self.similarity_threshold = similarity_threshold

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
    

if __name__ == "__main__":
    retriever = Retriever()
    logger.info(retriever.retrieve(query="什么是北京科技大学", label="public"))