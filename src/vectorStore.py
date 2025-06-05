from llama_index.core import VectorStoreIndex,Settings,SimpleDirectoryReader,load_index_from_storage
from llama_index.embeddings.dashscope import (
    DashScopeEmbedding,
    DashScopeTextEmbeddingModels,
    DashScopeTextEmbeddingType,
)
from llama_index.core.schema import TextNode
import os 
from dotenv import load_dotenv
from llama_index.core.storage import StorageContext
import shutil
# from utils.splitter import split_questions
from llama_index.core import Document

load_dotenv()

DB_PATH = os.getenv("PROJECT_PATH") + "/VectorStore"
KB_PATH = os.getenv("PROJECT_PATH") + "/knowledge_base"

class VectorStore:
    def __init__(self, index_path: str = DB_PATH, model_name: str = DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V2, type: str = DashScopeTextEmbeddingType.TEXT_TYPE_DOCUMENT):
        
            

        self.index_path = index_path
        os.makedirs(self.index_path, exist_ok=True)

        self.embedding_model = DashScopeEmbedding(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        model_name=model_name,
        text_type=type,
        )
        Settings.embed_model = self.embedding_model


    def load_index(self, label: str):

        db_path = os.path.join(self.index_path, label)
        if not os.path.exists(db_path):
            raise ValueError(f"向量数据库路径不存在: {db_path}")
        index = load_index_from_storage(
            storage_context=StorageContext.from_defaults(persist_dir=db_path),
        )
        return index
    

    def delete_index(self, label: str):
        kb_dir = os.path.join(KB_PATH, label)
        vs_dir = os.path.join(self.index_path, label)

        if os.path.exists(kb_dir):
            shutil.rmtree(kb_dir)
        
        else:
            raise ValueError(f"知识库不存在: {label}")

        if os.path.exists(vs_dir):
            shutil.rmtree(vs_dir)
        
        else:
            raise ValueError(f"向量数据库路径不存在: {vs_dir}") 
        
        return 1

    def list_label(self):
        return os.listdir(self.index_path)
    
    
    def create_index(self, file_path: str, label: str):


        # 确认路径存在
        if not os.path.exists(file_path):
            raise ValueError(f"文件路径不存在: {file_path}")

        reader = SimpleDirectoryReader(file_path)
        index = VectorStoreIndex.from_documents(
            documents=reader.load_data(),
            embedding=self.embedding_model,
        )
        db_path = os.path.join(self.index_path, label)
        index.storage_context.persist(db_path)
        print(f"向量数据库创建成功: {label}")

if __name__ == "__main__":
    vector_store = VectorStore()
    vector_store.create_index(file_path=f"{os.getcwd()}/src/knowledge_base", label="knowledge_base")