from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from flask_socketio import SocketIO, emit
import db_config
from user_service import register_user, login_user
import chat_events
import random

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

Asker=''
Answer=''
game_started = False
players = {}
player_list = []

@socketio.on('join')
def on_join(data):
    global game_started, number_to_guess
    sid = request.sid
    name = data['name']
    players[sid] = name
    if sid not in player_list:
        player_list.append(sid)
    emit('message', f"{name} 加入遊戲 ({len(players)}/2)", broadcast=True)

    if len(player_list) == 2 and not game_started:
        Asker=player_list[random.randint(0,len(player_list))]
        game_started = True
        emit('message', "🎮 遊戲開始！請根據特徵猜出物品。", broadcast=True)


@socketio.on('question')
def Ask_question(data):
    global game_started
    sid = request.sid
    if not game_started:
        emit('message', "⏳ 等待兩人以上加入...", to=sid)
        return
    Answer=data
    name=Asker
    emit('message', f"出題者:{name}", broadcast=True)

@socketio.on('hint')
def Ask_hint(data):
    global game_started
    sid = request.sid
    if not game_started:
        emit('message', "⏳ 等待兩人以上加入...", to=sid)
        return
    Answer=data
    name=Asker
    emit('message', f"出題者:{name}", broadcast=True)

@socketio.on('guess')
def on_guess(data):
    global game_started
    sid = request.sid
    guess = data['guess']
    name = players.get(sid, '匿名')

    if not game_started:
        emit('message', "⏳ 等待兩人以上加入...", to=sid)
        return

    if guess == Answer:
        emit('message', f"🎉{name} 猜 {guess} ，猜中了 ！", broadcast=True)
         # 更新資料庫中的分數
        try:
            db = db_config.get_db()
            cursor = db.cursor()
            cursor.execute("UPDATE users SET score = score + 1 WHERE nickname = %s", (name,))
            db.commit()
            cursor.close()
        except Exception as e:
            print(f"資料庫更新錯誤: {e}")

        reset_game()
    elif guess != number_to_guess:
        emit('message', f"{name} 猜 {guess} ，猜錯了。", broadcast=True)

def reset_game():
    global Asker,Answer,players, player_list, game_started
    Asker=''
    Answer=''
    players = {}
    player_list = []
    game_started = False


if __name__ == '__main__':
    socketio.run(app, debug=True)

