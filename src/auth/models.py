from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import uuid

# 加载环境变量
load_dotenv()

# 获取项目路径
PROJECT_PATH = os.getenv("PROJECT_PATH", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 数据库路径
DB_PATH = os.path.join(PROJECT_PATH, "data", "users.db")

# 确保数据目录存在
os.makedirs(os.path.join(PROJECT_PATH, "data"), exist_ok=True)

# 数据库连接
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,         # 增加基本连接池大小
    max_overflow=30,      # 增加溢出连接数
    pool_timeout=60,      # 增加超时时间
    pool_pre_ping=True,   # 使用前检查连接是否有效
    pool_recycle=3600     # 每小时回收连接
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 密码处理
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 设置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", str(uuid.uuid4()))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天过期

class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @classmethod
    def get_by_username(cls, db, username):
        return db.query(cls).filter(cls.username == username).first()
    
    @classmethod
    def get_by_email(cls, db, email):
        return db.query(cls).filter(cls.email == email).first()
    
    @classmethod
    def create(cls, db, username, email, password):
        """创建新用户"""
        hashed_password = pwd_context.hash(password)
        user = cls(
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

def verify_password(plain_password, hashed_password):
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """哈希密码"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)

# 初始化数据库
init_db()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db  # 使用yield而不是return
    finally:
        db.close() 