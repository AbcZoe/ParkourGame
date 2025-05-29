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
def handle_disconnect(auth):
    global Asker
    sid = request.sid
    nickname = sid_to_nickname.get(sid)
    if nickname:
        online_users.discard(nickname)
        sid_to_nickname.pop(sid, None)
        nickname_to_sid.pop(nickname, None)
        players.pop(sid, None)
        if sid in player_list:
            player_list.remove(sid)

        socketio.emit('update_user_list', list(online_users))

    if sid == Asker:
        emit('message', f"⚠️ 出題者 {nickname} 離開，重新開始遊戲", broadcast=True)
        reset_game()


# SocketIO事件註冊
chat_events.register(socketio, online_users, sid_to_nickname)

Asker=''
Answer=''
game_started = False
players = {}
player_list = []
hints = []

@socketio.on('join')
def on_join(data):
    global game_started, Asker
    sid = request.sid
    name = data['name']
    players[sid] = name
    if sid not in player_list:
        player_list.append(sid)

    emit('message', f"{name} 加入遊戲", broadcast=True)

    if not game_started and len(player_list) >= 2:
        Asker = random.choice(player_list)
        game_started = True
        socketio.emit('message', "🎮 遊戲開始！請根據特徵猜出物品。")
        socketio.emit('set_asker', {'asker_sid': Asker})
    elif game_started:
        # 遊戲正在進行中，新加入者要進入猜題狀態
        emit('set_asker', {'asker_sid': Asker}, to=sid)

        # 若已出題也可選擇補送提示（選做）
        if Answer:
            emit('message', f"🆕 歡迎{name}加入遊戲，請開始猜題！", to=sid)
            for hint in hints:
                emit('extraHint', f"💡 提示：{hint}", to=sid)

    # 確保遊戲能恢復
    if not game_started and len(player_list) >= 2:
        reset_game()


@socketio.on('question')
def Ask_question(data):
    global Answer
    Answer = data['answer']  # 謎底
    emit('message', f"出題者:{players.get(Asker)}")

@socketio.on('hint')
def Ask_hint(data):
    global hints
    hint = data['hint']
    hints.append(hint)
    emit('extraHint', f"💡 提示：{hint}")
    
    
@socketio.on('guess')
def on_guess(data):
    global game_started,Answer,Asker
    sid = request.sid
    guess = data['guess']
    name = players.get(sid, '匿名')

    if not game_started:
        emit('message', "⏳ 等待兩人以上加入...", to=sid)
        return

    if guess == Answer:
        emit('message', f"🎉{name} 猜 {guess} ，猜中了 ！")
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
    elif guess != Answer:
        emit('message', f"{name} 猜 {guess} ，猜錯了。")

def reset_game():
    global Asker, Answer, game_started,hints

    # 清掉不存在的 sid
    valid_sids = set(sid_to_nickname.keys())
    for sid in player_list[:]:
        if sid not in valid_sids:
            player_list.remove(sid)

    Asker = ''
    Answer = ''
    game_started = False
    hints = []

    if len(player_list) >= 2:
        Asker = random.choice(player_list)
        game_started = True
        socketio.emit('message', "🆕 新回合開始！")
        socketio.emit('set_asker', {'asker_sid': Asker})
    else:
        socketio.emit('message', "⚠️ 人數不足，請等待更多玩家加入")




if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

