from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from flask_socketio import SocketIO, emit, join_room, leave_room
import bcrypt
import db_config
import random
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app, manage_session=False)

WORDS = ["apple", "banana", "cat", "dog", "elephant", "flower", "guitar", "house", "icecream"]
online_users = set()
sid_to_nickname = {}
nickname_to_sid = {}

game_state = {
    'players': [],
    'current_turn': 0,
    'scores': {},
    'rounds_played': set(),
    'drawer': None,
    'word': None,
    'guessed': False,
    'guessers': set(),
    'waiting_continue': set(),
    'continue_votes': {},
    'started': False
}

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

@app.route('/game')
def game():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('game.html', nickname=session['nickname'])

@socketio.on('connect')
def handle_connect():
    nickname = session.get('nickname')
    if not nickname:
        handle_disconnect()
        return
    online_users.add(nickname)
    sid_to_nickname[request.sid] = nickname
    nickname_to_sid[nickname] = request.sid

    socketio.emit('update_user_list', list(online_users), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    nickname = sid_to_nickname.get(sid)
    if nickname:
        online_users.discard(nickname)
        sid_to_nickname.pop(sid, None)
        nickname_to_sid.pop(nickname, None)

        socketio.emit('update_user_list', list(online_users), broadcast=True)

@socketio.on('start_game')
def handle_start_game():
    nickname = session['nickname']
    if nickname not in game_state['players']:
        game_state['players'].append(nickname)
        game_state['scores'][nickname] = 0

    if game_state['started']:
        return

    game_state['started'] = True
    socketio.emit('game_starting', {'msg': '遊戲開始！'}, broadcast=True)
    socketio.start_background_task(start_game_round)

def start_game_round():
    if len(game_state['rounds_played']) == len(game_state['players']):
        socketio.emit('ask_continue', {'scores': game_state['scores']}, broadcast=True)
        game_state['waiting_continue'] = set(game_state['players'])
        game_state['continue_votes'] = {}
        return

    while game_state['players'][game_state['current_turn']] in game_state['rounds_played']:
        game_state['current_turn'] = (game_state['current_turn'] + 1) % len(game_state['players'])

    drawer = game_state['players'][game_state['current_turn']]
    word = random.choice(WORDS)
    game_state.update({
        'word': word,
        'drawer': drawer,
        'guessed': False,
        'guessers': set(p for p in game_state['players'] if p != drawer)
    })

    for player in game_state['players']:
        sid = nickname_to_sid.get(player)
        if not sid:
            continue
        if player == drawer:
            socketio.emit('your_turn_to_draw', {'word': word}, room=sid)
        else:
            socketio.emit('game_started', {'msg': f'{drawer} is drawing!'}, room=sid)

    socketio.start_background_task(timer_countdown, drawer)

def timer_countdown(drawer):
    for remaining in range(180, 0, -1):
        socketio.emit('timer_update', {'time': remaining}, broadcast=True)
        time.sleep(1)
        if game_state.get('guessed'):
            return

    if not game_state.get('guessed'):
        game_state['rounds_played'].add(drawer)
        socketio.emit('round_timeout', {
            'drawer': drawer,
            'word': game_state['word']
        }, broadcast=True)
        game_state['current_turn'] = (game_state['current_turn'] + 1) % len(game_state['players'])
        socketio.start_background_task(start_game_round)

@socketio.on('guess_word')
def handle_guess_word(data):
    nickname = session.get('nickname')
    guess = data.get('guess', '').strip().lower()

    if not nickname or not guess or not game_state.get('word'):
        return

    if nickname not in game_state['guessers'] or game_state['guessed']:
        return

    if guess == game_state['word'].lower():
        game_state['guessed'] = True
        game_state['rounds_played'].add(game_state['drawer'])

        game_state['scores'][nickname] += 10
        game_state['scores'][game_state['drawer']] += 5

        socketio.emit('correct_guess', {
            'guesser': nickname,
            'drawer': game_state['drawer'],
            'word': game_state['word']
        }, broadcast=True)

        game_state['current_turn'] = (game_state['current_turn'] + 1) % len(game_state['players'])
        socketio.start_background_task(start_game_round)

@socketio.on('vote_continue')
def handle_vote_continue(data):
    vote = data['continue']
    nickname = session['nickname']
    game_state['continue_votes'][nickname] = vote

    if len(game_state['continue_votes']) == len(game_state['waiting_continue']):
        if all(v is True for v in game_state['continue_votes'].values()):
            game_state['rounds_played'] = set()
            game_state['current_turn'] = 0
            socketio.emit('continue_game', {}, broadcast=True)
            socketio.start_background_task(start_game_round)
        else:
            socketio.emit('game_over', {'scores': game_state['scores']}, broadcast=True)
            reset_game()

def reset_game():
    global game_state
    game_state = {
        'players': [],
        'current_turn': 0,
        'scores': {},
        'rounds_played': set(),
        'drawer': None,
        'word': None,
        'guessed': False,
        'guessers': set(),
        'waiting_continue': set(),
        'continue_votes': {},
        'started': False
    }

# 畫布繪圖事件: 畫家傳送畫筆座標、顏色等，廣播給其他玩家
@socketio.on('drawing')
def handle_drawing(data):
    # 只廣播給非畫家，讓他們看到畫的線條
    nickname = session.get('nickname')
    if nickname != game_state['drawer']:
        return
    # 廣播給所有除了畫家本人的連線
    for player in game_state['players']:
        if player != nickname:
            sid = nickname_to_sid.get(player)
            if sid:
                socketio.emit('drawing', data, room=sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)
