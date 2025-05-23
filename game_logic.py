import random
import time
from flask_socketio import emit

WORDS = ["apple", "banana", "cat", "dog", "elephant", "flower", "guitar", "house", "icecream"]

def get_initial_game_state():
    return {
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

def start_game_round(game_state, nickname_to_sid, socketio):
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

    socketio.start_background_task(timer_countdown, game_state, drawer, socketio)

def timer_countdown(game_state, drawer, socketio):
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
        socketio.start_background_task(start_game_round, game_state, nickname_to_sid, socketio)