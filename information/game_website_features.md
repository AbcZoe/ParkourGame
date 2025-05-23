# 🎮 遊戲網頁功能規劃文件

本文件說明使用 Flask、SocketIO、MySQL 與 Session 所開發之多人互動遊戲網頁的主要功能模組與細節。

---

## 🔧 技術架構

- **後端框架**：Flask
- **即時通訊**：Flask-SocketIO
- **資料庫**：MySQL
- **使用者驗證與狀態管理**：Flask-Session
- **前端技術**：HTML / CSS / JavaScript (可搭配 Bootstrap 或 Vue.js)

---

## 🔑 使用者系統模組

- 使用者註冊/登入/登出功能
- Session 管理使用者登入狀態
- 使用者資料儲存於 MySQL（帳號、密碼（加密）、暱稱、積分等）

---

## 🕹️ 遊戲大廳與配對系統

- 顯示線上使用者清單
- 創建與加入遊戲房間
- 即時房間列表更新（透過 SocketIO）
- 準備/開始遊戲按鈕與狀態顯示

---

## 🧩 遊戲進行模組

- 遊戲邏輯（你畫我猜，單人時就與 ai玩）
- 即時遊戲狀態同步（玩家操作即時傳送至其他用戶）
- 支援多位玩家互動
- 遊戲結束、勝負判定、積分更新

---

## 💬 即時聊天室功能

- 房間內即時聊天（SocketIO 廣播）
- 系統訊息提示（如某位玩家加入/離開）
- 可選擇是否加入全站公共聊天室功能

---

## 📊 使用者資料與排行榜

- 個人資料頁面（查看歷史對戰紀錄、積分、勝率等）
- 全站排行榜（以答對題數排行）
- MySQL 儲存並查詢相關資料

---

## 🛡️ 安全性考量

- 密碼加密儲存（使用 bcrypt）
- 防止 XSS / CSRF 攻擊
- Session 驗證避免未登入操作遊戲

---

## 📁 目錄架構
NetGame/
│
├─ app.py                  # 主入口，負責路由、SocketIO事件註冊
├─ db_config.py            # 資料庫連線與關閉
├─ game_logic.py           # 遊戲邏輯（回合、倒數、狀態管理）
├─ user_service.py         # 使用者相關操作（註冊、登入、查詢等）
├─ socket_events.py        # SocketIO事件處理（可選，讓 app.py 更精簡）
│
├─ static/
│    └─ game.js            # 前端遊戲邏輯
│
├─ templates/
│    ├─ index.html
│    ├─ lobby.html
│    └─ game.html
│
└─ requirements.txt        # 套件需求
