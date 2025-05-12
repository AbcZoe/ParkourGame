from flask import Flask, request, render_template, redirect, url_for, session, flash
import pymysql
import dataset
import bcrypt

app = Flask(__name__)
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

# 使用 dataset 連接到資料庫（用於簡單的資料操作）
db = dataset.connect('mysql+pymysql://root:123456@localhost/game_db')
users_table = db['ParkourGame_users']  # 對應到你前面建立的資料表

# 顯示錯誤訊息的通用函式
def show_error(message):
    return render_template('error.html', message=message)

# 註冊時加密密碼
def hash_password(password):
    # 使用 bcrypt 進行加密，並生成鹽（salt）
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password

# 登入時檢查密碼
def check_password(stored_hash, password):
    # 檢查用戶輸入的密碼是否與存儲的密碼雜湊值相符
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash)

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        existing_user = users_table.find_one(username=username)

        if existing_user:
            return show_error('用戶名已存在，請選擇其他名稱')
        else:
            hashed_password = hash_password(password)
            users_table.insert(dict(username=username, password=hashed_password, high_score=0))
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/game')
def game():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = users_table.find_one(username=session['username'])
    return render_template('game.html', username=user['username'], high_score=user['high_score'])

@app.route('/leaderboard')
def leaderboard():
    # 根據 high_score 排序（由高至低）
    top_users = users_table.all(order_by='-high_score')
    return render_template('leaderboard.html', users=top_users)

@app.route('/submit_score', methods=['POST'])
def submit_score():
    if 'username' not in session:
        return "請先登入", 403

    username = session['username']
    score = float(request.form['score'])

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
