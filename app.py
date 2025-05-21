from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from flask_socketio import SocketIO, join_room, leave_room, emit
import bcrypt
import db_config
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app, manage_session=False)

WORDS = ["apple", "banana", "cat", "dog", "elephant", "flower", "guitar", "house", "icecream"]
online_users = set()
rooms = {}          # room_id: [nickname1, nickname2, ...]
game_rooms = {}     # room_id: {...遊戲狀態...}

# 紀錄 sid 與 nickname 對應，方便私訊
sid_to_nickname = {}
nickname_to_sid = {}

# ---------- 使用者功能 ----------

@app.route('/register', methods=['GET', 'POST'])
def register():
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

@app.route('/login', methods=['GET', 'POST'])
def login():
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/lobby')
def lobby():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('lobby.html', nickname=session['nickname'])

@app.route('/game/<room_id>')
def game_room(room_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if room_id not in rooms:
        return "房間不存在", 404
    return render_template('game.html', room_id=room_id, nickname=session['nickname'])


# ---------- SocketIO 事件 ----------

@socketio.on('connect')
def handle_connect():
    if 'user_id' not in session:
        return False
    nickname = session['nickname']
    online_users.add(nickname)
    sid_to_nickname[request.sid] = nickname
    nickname_to_sid[nickname] = request.sid
    emit('update_user_list', list(online_users), broadcast=True)
    emit('update_room_list', list(rooms.keys()), broadcast=True)

def emit_room_players(room_id):
    players = rooms.get(room_id, [])
    socketio.emit('update_room_players', {'room_id': room_id, 'players': players}, room=room_id)

@socketio.on('join_room')
def join_room_event(data):
    room_id = data['room_id']
    if room_id not in rooms:
        emit('error', {'msg': '房間不存在'})
        return
    nickname = session['nickname']
    if nickname not in rooms[room_id]:
        rooms[room_id].append(nickname)
        join_room(room_id)
    emit('update_room_list', list(rooms.keys()), broadcast=True)
    emit('joined_room', {'room_id': room_id}, room=request.sid)
    emit_room_players(room_id)  # 廣播房間內玩家名單

@socketio.on('create_room')
def create_room(data):
    room_id = data['room_id']
    if room_id in rooms:
        emit('error', {'msg': '房間已存在'})
    else:
        rooms[room_id] = [session['nickname']]
        join_room(room_id)
        emit('update_room_list', list(rooms.keys()), broadcast=True)
        emit('joined_room', {'room_id': room_id}, room=request.sid)
        emit_room_players(room_id)  # 廣播房間內玩家名單

@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = data.get('room_id')
    nickname = session.get('nickname')

    if room_id not in rooms or not nickname:
        emit('error', {'msg': '房間不存在或使用者未登入'})
        return

    if nickname in rooms[room_id]:
        rooms[room_id].remove(nickname)
        leave_room(room_id)
        emit_room_players(room_id)
        emit('left_room', {'room_id': room_id}, room=request.sid)

        # 如果房間沒人了就刪除房間和遊戲資料
        if len(rooms[room_id]) == 0:
            rooms.pop(room_id)
            game_rooms.pop(room_id, None)

        emit('update_room_list', list(rooms.keys()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    nickname = sid_to_nickname.get(sid)
    if nickname:
        online_users.discard(nickname)
        sid_to_nickname.pop(sid)
        nickname_to_sid.pop(nickname, None)
        for room_id, players in list(rooms.items()):
            if nickname in players:
                players.remove(nickname)
                leave_room(room_id)
                if len(players) == 0:
                    rooms.pop(room_id)
                    game_rooms.pop(room_id, None)
                else:
                    game = game_rooms.get(room_id)
                    if game and game['drawer'] == nickname:
                        socketio.emit('message', {'msg': '畫家離開，遊戲結束'}, room=room_id)
                        game_rooms.pop(room_id, None)
                    emit_room_players(room_id)
        emit('update_room_list', list(rooms.keys()), broadcast=True)
        emit('update_user_list', list(online_users), broadcast=True)

@socketio.on('start_game')
def handle_start_game(data):
    room_id = data['room_id']
    if room_id not in rooms:
        emit('error', {'msg': '房間不存在'})
        return
    if room_id in game_rooms:
        emit('error', {'msg': '遊戲已經開始'})
        return

    socketio.start_background_task(start_game_round, room_id)
    emit('game_starting', {'msg': '遊戲開始！'}, room=room_id)


def start_game_round(room_id):
    players = rooms[room_id]
    game = game_rooms.get(room_id, {
        'players': players,
        'current_turn': 0,
        'scores': {p: 0 for p in players},
        'rounds_played': set()
    })

    # 全部玩家都畫過一次了，遊戲結束
    if len(game['rounds_played']) == len(players):
        socketio.emit('game_over', {'scores': game['scores']}, room=room_id)
        game_rooms.pop(room_id, None)
        return

    # 找出還沒畫過的玩家當本回合畫家
    while game['players'][game['current_turn']] in game['rounds_played']:
        game['current_turn'] = (game['current_turn'] + 1) % len(players)

    drawer = game['players'][game['current_turn']]
    word = random.choice(WORDS)
    game.update({
        'word': word,
        'drawer': drawer,
        'guessed': False,
        'guessers': set(p for p in players if p != drawer)
    })
    game_rooms[room_id] = game

    for player in players:
        sid = nickname_to_sid.get(player)
        if not sid:
            continue
        if player == drawer:
            socketio.emit('your_turn_to_draw', {'word': word}, room=sid)
        else:
            socketio.emit('game_started', {'msg': f'{drawer} is drawing!'}, room=sid)

@socketio.on('drawing_data')
def handle_drawing(data):
    room_id = data['room_id']
    draw_data = data['draw_data']
    nickname = session['nickname']
    game = game_rooms.get(room_id)
    if game and nickname == game.get('drawer'):
        socketio.emit('update_drawing', {'draw_data': draw_data}, room=room_id, include_self=False)

@socketio.on('guess_word')
def handle_guess(data):
    room_id = data['room_id']
    guess = data['guess'].strip().lower()
    player = session['nickname']
    game = game_rooms.get(room_id)

    if not game or game['guessed']:
        return

    correct_word = game['word'].lower()
    if guess == correct_word:
        game['guessed'] = True
        game['rounds_played'].add(game['drawer'])
        game['scores'][player] += 1

        # 更新資料庫分數
        db = db_config.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT score FROM users WHERE nickname=%s", (player,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE users SET score=%s WHERE nickname=%s", (row['score'] + 1, player))
            db.commit()

        socketio.emit('correct_guess', {'player': player, 'word': correct_word}, room=room_id)

        # 換下一回合
        game['current_turn'] = (game['current_turn'] + 1) % len(game['players'])
        socketio.start_background_task(start_game_round, room_id)
    else:
        socketio.emit('guess_result', {'player': player, 'guess': guess}, room=room_id)


if __name__ == '__main__':
    socketio.run(app, debug=True)
