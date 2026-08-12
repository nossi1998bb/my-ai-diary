import os
import json
import base64
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
from google import genai

# --- 1. 設定と準備 ---
DATA_FILE = "diary_data.json"

# APIキーの取得
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# ページ基本設定
st.set_page_config(
    page_title="AI日記",
    page_icon="📖",
    layout="centered"
)

# --- 2. データ保存・読み込み関数 ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"streak": 0, "last_date": "", "logs": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 3. 動的ファビコン（動的アイコン）設定 ---
def set_dynamic_favicon(streak_count):
    """ストリーク数値を描画したSVGアイコンをファビコン・タブ等に反映"""
    svg_icon = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r="48" fill="#FF4B4B" />
      <text x="50" y="42" font-size="32" text-anchor="middle" fill="white">🔥</text>
      <text x="50" y="78" font-size="32" font-weight="bold" text-anchor="middle" fill="white">{streak_count}</text>
    </svg>
    """
    b64_svg = base64.b64encode(svg_icon.encode('utf-8')).decode('utf-8')
    js_code = f"""
    <script>
        let link = document.querySelector("link[rel*='icon']") || document.createElement('link');
        link.type = 'image/svg+xml';
        link.rel = 'shortcut icon';
        link.href = 'data:image/svg+xml;base64,{b64_svg}';
        document.getElementsByTagName('head')[0].appendChild(link);
    </script>
    """
    components.html(js_code, height=0, width=0)

# --- 4. ストリーク（連続日数）更新ロジック ---
def update_streak(data, today_str):
    last_date_str = data.get("last_date", "")
    if last_date_str == today_str:
        return data["streak"]

    today = datetime.strptime(today_str, "%Y-%m-%d").date()
    if last_date_str:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        if today - last_date == timedelta(days=1):
            data["streak"] += 1
        else:
            data["streak"] = 1
    else:
        data["streak"] = 1

    data["last_date"] = today_str
    return data["streak"]

# --- 5. アプリの初期化 ＆ UI ---
db = load_data()
current_streak = db.get("streak", 0)

# 動的アイコン適用
set_dynamic_favicon(current_streak)

st.title("📖 Gemini AI インタビュー日記")
st.metric(label="🔥 連続投稿日数 (タブ/アイコンと連動)", value=f"{current_streak} 日")

# セッション状態（対話履歴など）の初期化
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "こんにちは！今日もお疲れ様でした。今日はどんな1日でしたか？楽しかったことや印象に残ったことを教えてください😊"}
    ]

st.divider()

# --- 6. 音声認識（Web Speech API）コンポーネント ---
st.subheader("🎙️ 音声入力 (スマホマイク対応)")
speech_html = """
<div style="margin-bottom:15px;">
  <button id="start-btn" style="background-color:#FF4B4B; color:white; border:none; padding:10px 18px; border-radius:8px; font-weight:bold; cursor:pointer;">
    🎙️ 話して入力（タップで開始）
  </button>
  <span id="status" style="margin-left:10px; font-size:14px; color:#666;"></span>
  <p id="result-text" style="background:#f0f2f6; padding:10px; border-radius:5px; margin-top:8px; min-height:40px; color:#333; font-size:14px;">話した言葉がここに表示されます...</p>
</div>

<script>
  const startBtn = document.getElementById('start-btn');
  const resultText = document.getElementById('result-text');
  const status = document.getElementById('status');

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
      resultText.innerText = "お使いのブラウザは音声認識非対応です（Chrome / Safari 推奨）";
  } else {
      const recognition = new SpeechRecognition();
      recognition.lang = 'ja-JP';
      recognition.interimResults = true;

      startBtn.addEventListener('click', () => {
          recognition.start();
          status.innerText = "録音中...お話しください";
          startBtn.style.backgroundColor = "#28a745";
      });

      recognition.onresult = (event) => {
          let transcript = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
              transcript += event.results[i].transcript;
          }
          resultText.innerText = transcript;
      };

      recognition.onerror = (e) => {
          status.innerText = "エラーが発生しました";
          startBtn.style.backgroundColor = "#FF4B4B";
      };

      recognition.onend = () => {
          status.innerText = "録音完了！上のテキストをコピーして下のチャットに貼ってください。";
          startBtn.style.backgroundColor = "#FF4B4B";
      };
  }
</script>
"""
components.html(speech_html, height=130)

st.divider()

# --- 7. 対話チャット機能 (何ラリーか会話) ---
st.subheader("💬 AIと対話して日記を作成")

# 過去の会話ログを表示
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# ユーザー入力
user_input = st.chat_input("AIに今日の出来事や感情を教えてね...")

if user_input:
    # ユーザーメッセージ追加
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # Geminiへ対話継続リクエスト
    with st.spinner("Geminiが考え中..."):
        chat_history_prompt = "以下はユーザーとの会話ログです。親しみやすいインタビュー形式で、日記としてまとめるための深掘り質問や共感の返答を短い1〜2文で返してください。\n\n"
        for m in st.session_state.messages:
            chat_history_prompt += f"{m['role']}: {m['content']}\n"

        res = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=chat_history_prompt
        )
        ai_reply = res.text

    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
    st.chat_message("assistant").write(ai_reply)

# --- 8. まとめ＆日記確定保存ボタン ---
st.markdown("---")
if st.button("✨ 会話を締めくくって今日の日記としてまとめる", type="primary"):
    if len(st.session_state.messages) <= 1:
        st.warning("まずAIと少し会話を交わしてからボタンを押してください！")
    else:
        with st.spinner("AIが今日の会話を1つの綺麗な日記に整理しています..."):
            summary_prompt = f"""
            以下の一連の会話ログから、ユーザーの「今日の日記本文（200文字程度）」と「AIからの温かいメッセージ（100文字程度）」を作成してください。

            【出力フォーマット】
            必ず以下のフォーマット通りに出力してください（---で区切る）。

            [日記本文]
            （ここにユーザーの出来事や感情を一人称でまとめた日記文）
            ---
            [AIコメント]
            （ここに1日を振り返ってのねぎらいとポジティブな感想）

            【会話ログ】
            """
            for m in st.session_state.messages:
                summary_prompt += f"{m['role']}: {m['content']}\n"

            res = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=summary_prompt
            )
            raw_output = res.text

            # フォーマット解析
            parts = raw_output.split("---")
            diary_entry = parts[0].replace("[日記本文]", "").strip() if len(parts) > 0 else raw_output
            ai_comment = parts[1].replace("[AIコメント]", "").strip() if len(parts) > 1 else "今日も一日お疲れ様でした！"

            # データの保存とストリーク更新
            today_str = datetime.now().strftime("%Y-%m-%d")
            new_streak = update_streak(db, today_str)

            db["logs"].append({
                "date": today_str,
                "entry": diary_entry,
                "ai_comment": ai_comment
            })
            save_data(db)

            st.success(f"🎉 日記を保存しました！🔥 連続 {new_streak} 日達成！")
            st.markdown(f"### 📜 完成した今日の日記\n{diary_entry}")
            st.info(f"**🤖 AIコメント:**\n\n{ai_comment}")

            # チャット履歴リセット
            st.session_state.messages = [
                {"role": "assistant", "content": "今日もお疲れ様でした！次はどんな1日でしたか？"}
            ]

st.divider()

# --- 9. 月間カレンダー表示機能 ---
st.subheader("📅 月間日記カレンダー & 履歴")

# ログを日付キーの辞書に変換
logs_by_date = {log["date"]: log for log in db.get("logs", [])}

# 表示対象の年月（今月）
today = datetime.now()
st.write(f"### {today.year}年 {today.month}月")

# カレンダーグリッドの作成
import calendar
cal = calendar.monthcalendar(today.year, today.month)
cols = st.columns(7)
days = ["月", "火", "水", "木", "金", "土", "日"]

for i, d in enumerate(days):
    cols[i].caption(f"**{d}**")

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write(" ")
        else:
            date_str = f"{today.year}-{today.month:02d}-{day:02d}"
            if date_str in logs_by_date:
                # 日記が存在する日は「🔥」付きボタンにする
                if cols[i].button(f"{day}\n🔥", key=f"btn_{date_str}"):
                    log = logs_by_date[date_str]
                    st.session_state.selected_log = log
            else:
                cols[i].write(f"{day}")

# カレンダーで選択した日の詳細表示
if "selected_log" in st.session_state and st.session_state.selected_log:
    s_log = st.session_state.selected_log
    st.markdown("---")
    st.subheader(f"📖 {s_log['date']} の日記")
    st.write("**【日記本文】**")
    st.write(s_log["entry"])
    st.write("**【AIコメント】**")
    st.info(s_log["ai_comment"])
