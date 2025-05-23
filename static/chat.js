// chat.js
let chatVisible = true;

function toggleChat() {
    chatVisible = !chatVisible;
    document.getElementById('chatBox').style.display = chatVisible ? 'flex' : 'none';
    document.getElementById('chatToggleBtn').innerText = chatVisible ? '隱藏聊天室' : '顯示聊天室';
}

const chatSocket = io();

function sendMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (msg) {
        chatSocket.emit('send_message', { message: msg });
        input.value = '';
    }
}

chatSocket.on('receive_message', function(data) {
    const chatList = document.getElementById('chatList');
    const li = document.createElement('li');
    li.innerHTML = `<b>${data.nickname}</b>: ${data.message}`;
    chatList.appendChild(li);
    chatList.scrollTop = chatList.scrollHeight;
});

window.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('chatBox')) {
        chatSocket.emit('join_chat');
        document.getElementById('chatInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    }
});
