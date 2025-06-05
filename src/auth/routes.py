from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from .models import User, get_db, create_access_token
from .auth import (
    UserCreate, 
    UserResponse, 
    Token, 
    authenticate_user, 
    get_current_active_user,
    get_admin_user
)

router = APIRouter(prefix="/auth", tags=["认证"])

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    db_user = User.get_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    # 检查邮箱是否已存在
    db_email = User.get_by_email(db, email=user.email)
    if db_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建新用户
    new_user = User.create(
        db=db,
        username=user.username,
        email=user.email,
        password=user.password
    )
    
    return new_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": user.username}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin
    }

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user

@router.get("/users", response_model=List[UserResponse])
async def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    """获取所有用户信息（仅管理员）"""
    users = db.query(User).all()
    return users

@router.post("/create-admin")
async def create_admin_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    admin_code: str = Form(...),
    db: Session = Depends(get_db)
):
    """创建管理员用户（需要管理员密码）"""
    # 验证管理员密码
    if admin_code != "admin123":  # 在实际应用中，应从环境变量或配置中获取
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员密码错误"
        )
    
    # 检查用户名是否已存在
    db_user = User.get_by_username(db, username=username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    # 检查邮箱是否已存在
    db_email = User.get_by_email(db, email=email)
    if db_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建管理员用户
    user = User.create(
        db=db,
        username=username,
        email=email,
        password=password
    )
    user.is_admin = True
    db.commit()
    db.refresh(user)
    
    return {"status": "success", "message": "管理员用户创建成功"} 