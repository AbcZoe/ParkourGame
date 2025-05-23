from flask import request, session
from game_logic import start_game_round

def register(socketio, session_obj, online_users, sid_to_nickname, nickname_to_sid, game_state):
    @socketio.on('connect')
    def handle_connect(auth):
        nickname = session.get('nickname')
        sid = request.sid
        print(f"[CONNECT] SID={request.sid}, Nickname from session: {nickname}")
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

    @socketio.on('start_game')
    def handle_start_game():
        sid = request.sid
        nickname = sid_to_nickname.get(sid)
        print(f"[CONNECT] SID={request.sid}, Nickname from session: {nickname}")
        if not nickname:
            return

        if nickname not in game_state['players']:
            game_state['players'].append(nickname)
            game_state['scores'][nickname] = 0

        # 只有兩人以上才開始遊戲
        if len(game_state['players']) < 2:
            socketio.emit('game_waiting', {'msg': '等待其他玩家加入...'}, room=sid)
            return

        if game_state['started']:
            return

        game_state['started'] = True
        socketio.emit('game_starting', {'msg': '遊戲開始！'})
        socketio.start_background_task(start_game_round, game_state, nickname_to_sid, socketio)

    @socketio.on('drawing')
    def handle_drawing(data):
        # 廣播畫圖資料給所有人
        socketio.emit('drawing', data, include_self=False)

    @socketio.on('clear_canvas')
    def handle_clear_canvas():
        socketio.emit('clear_canvas')

    @socketio.on('guess_word')
    def handle_guess_word(data):
        # 這裡應根據你的 game_logic 判斷猜測是否正確
        pass

    @socketio.on('vote_continue')
    def handle_vote_continue(data):
        # 這裡應根據你的 game_logic 處理繼續投票
        pass