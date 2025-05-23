const socket = io();
const canvas = document.getElementById('drawingBoard');
const ctx = canvas.getContext('2d');
let drawing = false;
let isDrawer = false;
let gameStarted = false;

// 等待第二位玩家加入
socket.on('game_waiting', function(data) {
    document.getElementById('gameStatus').innerText = data.msg;
    document.getElementById('waitingMask').style.display = 'flex';
    setGameEnabled(false);
});

// 禁用互動
function setGameEnabled(enabled) {
    document.getElementById('guessInput').disabled = !enabled;
    document.getElementById('guessBtn').disabled = !enabled;
    document.getElementById('clearBtn').disabled = !enabled;
    canvas.style.pointerEvents = enabled ? 'auto' : 'none';
}

setGameEnabled(false);

canvas.addEventListener('mousedown', (e) => {
    if (!isDrawer || !gameStarted) return;
    drawing = true;
    draw(e.offsetX, e.offsetY, false);
});

canvas.addEventListener('mousemove', (e) => {
    if (!isDrawer || !drawing || !gameStarted) return;
    draw(e.offsetX, e.offsetY, true);
});

canvas.addEventListener('mouseup', () => drawing = false);
canvas.addEventListener('mouseout', () => drawing = false);

function draw(x, y, dragging) {
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = 'black';

    if (dragging) {
        ctx.lineTo(x, y);
        ctx.stroke();
    } else {
        ctx.beginPath();
        ctx.moveTo(x, y);
    }

    socket.emit('drawing', { x, y, dragging });
}

function clearCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (isDrawer && gameStarted) {
        socket.emit('clear_canvas');
    }
}

function submitGuess() {
    const guess = document.getElementById('guessInput').value;
    if (guess.trim() !== '') {
        socket.emit('guess_word', { guess });
        document.getElementById('guessInput').value = '';
    }
}

socket.on('drawing', (data) => {
    const { x, y, dragging } = data;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = 'black';

    if (dragging) {
        ctx.lineTo(x, y);
        ctx.stroke();
    } else {
        ctx.beginPath();
        ctx.moveTo(x, y);
    }
});

socket.on('clear_canvas', () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
});

socket.on('your_turn_to_draw', (data) => {
    isDrawer = true;
    gameStarted = true;
    setGameEnabled(true);
    document.getElementById('waitingMask').style.display = 'none';
    clearCanvas();
    document.getElementById('gameStatus').innerText = `你的回合！請畫出：「${data.word}」`;
});

socket.on('game_started', (data) => {
    isDrawer = false;
    gameStarted = true;
    setGameEnabled(true);
    document.getElementById('waitingMask').style.display = 'none';
    clearCanvas();
    document.getElementById('gameStatus').innerText = data.msg;
});

socket.on('round_timeout', (data) => {
    alert(`時間到！${data.drawer} 畫的是：「${data.word}」`);
});

socket.on('correct_guess', (data) => {
    alert(`${data.guesser} 猜對了！答案是「${data.word}」`);
});

socket.on('timer_update', (data) => {
    document.getElementById('timer').innerText = data.time;
});

socket.on('ask_continue', (data) => {
    let result = confirm(`本輪結束！分數如下：\n\n${formatScores(data.scores)}\n\n要繼續下一輪嗎？`);
    socket.emit('vote_continue', { continue: result });
});

socket.on('game_over', (data) => {
    alert(`遊戲結束！最終分數：\n\n${formatScores(data.scores)}`);
    location.href = '/lobby';
});

function formatScores(scores) {
    return Object.entries(scores).map(([player, score]) => `${player}：${score}`).join('\n');
}

// 進入頁面自動通知後端
socket.emit('start_game');