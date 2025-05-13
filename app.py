from flask import Flask, request, render_template, redirect, url_for, session, flash
import pymysql
import dataset
import bcrypt
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key'  # session 加密用

# 資料庫連線設定
connection = pymysql.connect(
    host='localhost',
    user='root',
    password='123456',
    database='game_db'
)
try:
    with connection.cursor() as cursor:
        # 建立資料表 SQL 語句
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS ParkourGame_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(20) UNIQUE,
            password VARCHAR(100),
            high_score FLOAT DEFAULT 0
        );
        '''
        cursor.execute(create_table_sql)
        connection.commit()
        print("資料表 'ParkourGame_users' 建立成功")
finally:
    connection.close()

# 使用 dataset 連接到資料庫
db = dataset.connect('mysql+pymysql://root:123456@localhost/game_db')
users_table = db['ParkourGame_users']

# 顯示錯誤訊息
def show_error(message):
    return render_template('error.html', message=message)

# 密碼加密
def hash_password(password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8')  # 儲存為字串

# 密碼驗證
def check_password(stored_hash, password):
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash)  # 只對 password 進行編碼，stored_hash 已經是 bytes 類型

# 登入
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_table.find_one(username=username)
        if user:
            if check_password(user['password'].encode('utf-8'), password):
                session['username'] = username
                return redirect(url_for('game'))
            else:
                return show_error('密碼錯誤，請重新輸入')
        else:
            return show_error('用戶名不存在，請註冊')

    return render_template('login.html')

# 註冊
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 檢查使用者名稱是否已經存在
        user = users_table.find_one(username=username)  # 使用 users_table 來查詢
        if user:
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))

        hashed_password = hash_password(password)
        # 在 dataset 中插入新使用者
        users_table.insert({'username': username, 'password': hashed_password})
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# 遊戲主頁
@app.route('/game')
def game():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = users_table.find_one(username=session['username'])
    return render_template('game.html', username=user['username'], high_score=user['high_score'])

# 登出
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 排行榜
@app.route('/leaderboard')
def leaderboard():
    # 改用 SQL 排序
    top_users = db.query('SELECT username, high_score FROM ParkourGame_users ORDER BY high_score DESC LIMIT 10')
    return render_template('leaderboard.html', users=top_users)

# 成績上傳
@app.route('/submit_score', methods=['GET', 'POST'])
def submit_score():
    
    if 'username' not in session:
        return "請先登入", 403  # 如果未登入，則回應 403

    username = session['username']
    score = float(request.form['score'])  # 從 Unity 傳來的分數
    
    user = users_table.find_one(username=username)
    if user:
        if score > user['high_score']:
            users_table.update({'id': user['id'], 'high_score': score}, ['id'])
            return '高分已更新'
        else:
            return '分數已接收'
    return '使用者不存在', 404

if __name__ == '__main__':
    app.run(debug=True)
