from flask import session, request
from flask_socketio import emit, join_room

def register(socketio, online_users, sid_to_nickname):
    @socketio.on('send_message')
    def handle_send_message(data):
        nickname = session.get('nickname')
        if not nickname:
            return  # 未登入者不可發言
        message = data.get('message', '').strip()
        if message:
            emit('receive_message', {'nickname': nickname, 'message': message}, room='chat')

    @socketio.on('join_chat')
    def handle_join_chat():
        nickname = session.get('nickname')
        if not nickname:
            return
        sid = request.sid
        sid_to_nickname[sid] = nickname
        join_room('chat')
        # 可選：發送歷史訊息或歡迎訊息
        emit('receive_message', {'nickname': '系統', 'message': f'{nickname} 加入聊天室'}, room='chat')
