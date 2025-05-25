from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from flask_socketio import SocketIO
import db_config
from user_service import register_user, login_user
import chat_events

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app, manage_session=False)

# 遊戲狀態與連線管理
online_users = set()
sid_to_nickname = {}
nickname_to_sid = {}

# 路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    return register_user(request, db_config, session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    return login_user(request, db_config, session)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/lobby')
def lobby():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # 查詢排行榜
    db = db_config.get_db()
    cursor = db.cursor()
    cursor.execute("SELECT nickname, score FROM users ORDER BY score DESC, nickname ASC LIMIT 10")
    leaderboard = cursor.fetchall()
    return render_template('lobby.html', nickname=session['nickname'], leaderboard=leaderboard)

@app.route('/game')
def game():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('game.html', nickname=session['nickname'])

@socketio.on('connect')
def handle_connect(auth):
    nickname = session.get('nickname')
    sid = request.sid
    print(f"[CONNECT] SID={sid}, Nickname from session: {nickname}")
    if not nickname:
        return
    online_users.add(nickname)
    sid_to_nickname[sid] = nickname
    nickname_to_sid[nickname] = sid

    # 更新大廳線上名單
    socketio.emit('update_user_list', list(online_users))

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    nickname = sid_to_nickname.get(sid)
    if nickname:
        online_users.discard(nickname)
        sid_to_nickname.pop(sid, None)
        nickname_to_sid.pop(nickname, None)
        # 更新大廳線上名單
        socketio.emit('update_user_list', list(online_users))

# SocketIO事件註冊
chat_events.register(socketio, online_users, sid_to_nickname)

if __name__ == '__main__':
    socketio.run(app, debug=True)

