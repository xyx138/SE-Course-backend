from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from .models import User, get_db, create_access_token, get_password_hash, verify_password
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

# 修改密码
@router.post("/change-password")
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    修改密码
    
    Args:
        current_password: 当前密码
        new_password: 新密码
        current_user: 当前登录用户（从依赖注入获取）
        db: 数据库会话
        
    Returns:
        dict: 修改结果
        {
            "status": "success"/"error",
            "message": str
        }
    """
    try:
        # 验证当前密码是否正确
        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码不正确"
            )
        
        # 验证新密码是否符合要求
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="新密码长度必须至少为6个字符"
            )
        
        # 如果新密码与当前密码相同，则不需要更改
        if current_password == new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="新密码不能与当前密码相同"
            )
        
        # 更新密码（先哈希处理）
        hashed_new_password = get_password_hash(new_password)
        
        # 获取数据库中的用户对象
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 更新密码
        user.hashed_password = hashed_new_password
        db.commit()
        
        return {
            "status": "success", 
            "message": "密码修改成功"
        }
        
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise e
    except Exception as e:
        # 记录错误
        print(f"修改密码时出错: {str(e)}")
        # 返回通用错误信息
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改密码时出错: {str(e)}"
        )

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