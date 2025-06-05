import sqlite3
import os
from werkzeug.security import generate_password_hash

def init_db():
    # 确保数据库目录存在
    db_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(db_dir, exist_ok=True)
    
    # 数据库文件路径
    db_path = os.path.join(db_dir, 'auth.db')
    
    # 连接到数据库（如果不存在则创建）
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建学生表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建管理员表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS administrators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manager_id TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 提交更改并关闭连接
    conn.commit()
    conn.close()

def get_db():
    """获取数据库连接"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'auth.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 这样可以通过列名访问结果
    return conn

def add_student(student_id, password, name):
    """添加新学生"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO students (student_id, password, name) VALUES (?, ?, ?)',
            (student_id, hashed_password, name)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def add_administrator(manager_id, password, name):
    """添加新管理员"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO administrators (manager_id, password, name) VALUES (?, ?, ?)',
            (manager_id, hashed_password, name)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_student(student_id, password):
    """验证学生登录"""
    from werkzeug.security import check_password_hash
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    
    if student and check_password_hash(student['password'], password):
        return {
            'id': student['id'],
            'student_id': student['student_id'],
            'name': student['name']
        }
    return None

def verify_administrator(manager_id, password):
    """验证管理员登录"""
    from werkzeug.security import check_password_hash
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM administrators WHERE manager_id = ?', (manager_id,))
    admin = cursor.fetchone()
    conn.close()
    
    if admin and check_password_hash(admin['password'], password):
        return {
            'id': admin['id'],
            'manager_id': admin['manager_id'],
            'name': admin['name']
        }
    return None

def get_student_by_id(student_id):
    """通过学号获取学生信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    return dict(student) if student else None

def get_administrator_by_id(manager_id):
    """通过管理员ID获取管理员信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM administrators WHERE manager_id = ?', (manager_id,))
    admin = cursor.fetchone()
    conn.close()
    return dict(admin) if admin else None

# 初始化数据库
if __name__ == '__main__':
    init_db() 