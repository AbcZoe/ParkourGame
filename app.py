from flask import Flask, request, render_template, redirect, url_for, session
import dataset

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 改用 SQLite 資料庫連線
db = dataset.connect('sqlite:///game_users.db')
users_table = db['users']

# 建立資料表（SQLite 語法）
db.query('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        high_score REAL DEFAULT 0
    );
''')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = users_table.find_one(username=username)
        if user and user['password'] == password:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="帳號或密碼錯誤")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = users_table.find_one(username=username)
        if existing_user:
            return render_template('register.html', error="此帳號已存在")

        users_table.insert({'username': username, 'password': password, 'high_score': 0})
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/home')
def home():
    top_users = db.query('SELECT username, high_score FROM users ORDER BY high_score DESC LIMIT 10')
    return render_template('home.html', users=top_users)

@app.route('/game')
def game():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = users_table.find_one(username=session['username'])
    return render_template('game.html', username=user['username'], high_score=user['high_score'])

@app.route('/submit_score', methods=['POST'])
def submit_score():
    if 'username' not in session:
        return "請先登入", 403

    username = session['username']
    score = float(request.form['score'])

    user = users_table.find_one(username=username)
    if user:
        if score > user.get('high_score', 0):
            users_table.update({'id': user['id'], 'high_score': score}, ['id'])
            return '高分已更新'
        else:
            return '分數已接收'
    return '使用者不存在', 404

if __name__ == '__main__':
    app.run(debug=True)
