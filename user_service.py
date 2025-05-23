import bcrypt
from flask import render_template, redirect, url_for

def register_user(request, db_config, session):
    if request.method == 'POST':
        username = request.form['username']
        nickname = request.form['nickname']
        password = request.form['password'].encode('utf-8')
        db = db_config.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            return "帳號已存在", 400
        hashed = bcrypt.hashpw(password, bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password, nickname, score) VALUES (%s,%s,%s,%s)",
                       (username, hashed, nickname, 0))
        db.commit()
        return redirect(url_for('login'))
    return render_template('index.html')

def login_user(request, db_config, session):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        db = db_config.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if user and bcrypt.checkpw(password, user['password'].encode('utf-8')):
            session['user_id'] = user['id']
            session['nickname'] = user['nickname']
            return redirect(url_for('lobby'))
        else:
            return "帳號或密碼錯誤", 400
    return render_template('index.html')