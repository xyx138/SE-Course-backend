from flask import Flask, request, jsonify, render_template, redirect, url_for
from database import init_db, add_student, add_administrator, verify_student, verify_administrator
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于session加密

# 初始化数据库
init_db()

@app.route('/')
def index():
    return render_template('unified_auth.html')

# 学生登录
@app.route('/api/student/login', methods=['POST'])
def student_login():
    data = request.get_json()
    student_id = data.get('studentId')
    password = data.get('password')
    
    if not student_id or not password:
        return jsonify({'error': '请提供学号和密码'}), 400
    
    student = verify_student(student_id, password)
    if student:
        return jsonify({'message': '登录成功', 'user': student})
    return jsonify({'error': '学号或密码错误'}), 401

# 学生注册
@app.route('/api/student/register', methods=['POST'])
def student_register():
    data = request.get_json()
    student_id = data.get('studentId')
    password = data.get('password')
    name = data.get('name')
    
    if not all([student_id, password, name]):
        return jsonify({'error': '请提供所有必要信息'}), 400
    
    if add_student(student_id, password, name):
        return jsonify({'message': '注册成功'})
    return jsonify({'error': '该学号已被注册'}), 400

# 管理员登录
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    manager_id = data.get('managerId')
    password = data.get('password')
    
    if not manager_id or not password:
        return jsonify({'error': '请提供管理员ID和密码'}), 400
    
    admin = verify_administrator(manager_id, password)
    if admin:
        return jsonify({'message': '登录成功', 'user': admin})
    return jsonify({'error': '管理员ID或密码错误'}), 401

# 管理员注册
@app.route('/api/admin/register', methods=['POST'])
def admin_register():
    data = request.get_json()
    manager_id = data.get('managerId')
    password = data.get('password')
    name = data.get('name')
    
    if not all([manager_id, password, name]):
        return jsonify({'error': '请提供所有必要信息'}), 400
    
    if add_administrator(manager_id, password, name):
        return jsonify({'message': '注册成功'})
    return jsonify({'error': '该管理员ID已被注册'}), 400

# 学生仪表板
@app.route('/student/dashboard')
def student_dashboard():
    return render_template('student_dashboard.html')

# 管理员仪表板
@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

if __name__ == '__main__':
    app.run(debug=True) 