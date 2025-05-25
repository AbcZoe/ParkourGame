from flask import request, session
from game_logic import start_game_round

def register(socketio, session_obj, online_users, sid_to_nickname, nickname_to_sid, game_state):
    @socketio.on('start_game')
    def handle_start_game():
        # 檢查是否有足夠玩家且遊戲尚未開始
        if len(online_users) >= 2 and not game_state['started']:
            for p in online_users:
                if p not in game_state['players']:
                    game_state['players'].append(p)
                    game_state['scores'][p] = 0
            game_state['started'] = True
            socketio.emit('game_starting', {'msg': '遊戲開始！'})
            socketio.start_background_task(start_game_round, game_state, nickname_to_sid, socketio)
        else:
            socketio.emit('game_waiting', {'msg': '等待更多玩家加入...'})

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

    @socketio.on('drawing')
    def handle_drawing(data):
        # 廣播畫圖資料給所有人
        socketio.emit('drawing', data, include_self=False)

    @socketio.on('clear_canvas')
    def handle_clear_canvas():
        socketio.emit('clear_canvas')

    @socketio.on('guess_word')
    def handle_guess_word(data):
        guess = data.get('guess', '').strip().lower()
        sid = request.sid
        nickname = sid_to_nickname.get(sid)
        if not nickname or not guess:
            return
    
        # 如果遊戲已結束或不是猜者，忽略
        if game_state.get('guessed') or nickname == game_state.get('drawer'):
            return
    
        correct_word = game_state.get('word', '').lower()
        if guess == correct_word:
            game_state['guessed'] = True
            # 猜對玩家加分
            game_state['scores'][nickname] = game_state['scores'].get(nickname, 0) + 1
            game_state['rounds_played'].add(game_state['drawer'])
        
         # 通知所有人猜對了
            socketio.emit('correct_guess', {
                'guesser': nickname,
                'word': correct_word
            })
        
            # 準備下一輪
            game_state['current_turn'] = (game_state['current_turn'] + 1) % len(game_state['players'])
            socketio.start_background_task(start_game_round, game_state, nickname_to_sid, socketio)
        else:
            # 如果猜錯，可以選擇通知或不通知
            socketio.emit('guess_incorrect', {'guesser': nickname, 'guess': guess}, broadcast=True)

    @socketio.on('vote_continue')
    def handle_vote_continue(data):
        sid = request.sid
        nickname = sid_to_nickname.get(sid)
        if not nickname or nickname not in game_state['waiting_continue']:
            return
    
        vote = data.get('continue')
        game_state['continue_votes'][nickname] = bool(vote)
        game_state['waiting_continue'].discard(nickname)

        # 檢查是否所有人都投票完成
        if not game_state['waiting_continue']:
            if all(game_state['continue_votes'].values()):
                # 所有人都同意繼續，重置並開始新輪
                game_state['rounds_played'] = set()
                game_state['current_turn'] = 0
                game_state['started'] = True
                socketio.emit('game_starting', {'msg': '新一輪遊戲開始！'})
                socketio.start_background_task(start_game_round, game_state, nickname_to_sid, socketio)
            else:
                # 有人不同意，遊戲結束
                game_state['started'] = False
                socketio.emit('game_over', {'scores': game_state['scores']})