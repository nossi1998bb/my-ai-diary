import os
import json
import base64
import calendar
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
from google import genai

# --- 1. 設定と準備 ---
DATA_FILE = "diary_data.json"

# APIキーの取得
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# プロフィールの取得
user_profile = st.secrets.get("USER_PROFILE", "ユーザー情報未設定")

# ページ基本設定
st.set_page_config(
    page_title="達希のAIパートナー日記",
    page_icon="📖",
    layout="centered"
)

# --- CSS設定: スマホ用カレンダー ---
st.markdown("""
<style>
.calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    text-align: center;
    margin-bottom: 10px;
}
.calendar-header {
    font-weight: bold;
    background-color: #f0f2f6;
    padding: 6px 0;
    border-radius: 4px;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

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

# --- 3. 動的ファビコン設定 ---
def set_dynamic_favicon(streak_count):
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

set_dynamic_favicon(current_streak)

st.title("📖 達希の専属AIパートナー日記")
st.metric(label="🔥 連続投稿日数 (タブ/アイコンと連動)", value=f"{current_streak} 日")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "達希さん、今日もお疲れ様です！今日はどんな1日でしたか？お仕事のこと、趣味や街歩きの発見など、何でも気軽に教えてください😊"}
    ]

st.divider()

# --- 6. チャット履歴表示 ---
st.subheader("💬 AI相棒と対話して日記を作成")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# --- 7. 統合型（音声入力＋送信ボタン一体化）フォーム ---
integrated_input_html = """
<div style="background-color: #ffffff; border: 1.5px solid #d1d5db; border-radius: 16px; padding: 12px 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); font-family: sans-serif; margin-bottom: 10px;">
  <textarea id="unified-input" placeholder="メッセージを入力、またはマイクをタップして吹き込んでください..." style="width: 100%; height: 70px; border: none; outline: none; resize: none; font-size: 15px; color: #1f2937; line-height: 1.4; background: transparent;"></textarea>
  
  <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; border-top: 1px solid #f3f4f6; padding-top: 8px;">
    <div style="display: flex; align-items: center; gap: 8px;">
      <button id="mic-btn" style="background: #f3f4f6; border: none; border-radius: 50%; width: 38px; height: 38px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;">
        <span id="mic-icon" style="font-size: 18px;">🎙️</span>
      </button>
      <span id="mic-status" style="font-size: 12px; color: #6b7280;"></span>
    </div>
    
    <button id="send-btn" style="background-color: #FF4B4B; color: white; border: none; padding: 8px 18px; border-radius: 20px; font-size: 14px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 4px; transition: background 0.2s;">
      送信 ⬆️
    </button>
  </div>
</div>

<script>
  const micBtn = document.getElementById('mic-btn');
  const micIcon = document.getElementById('mic-icon');
  const unifiedInput = document.getElementById('unified-input');
  const micStatus = document.getElementById('mic-status');
  const sendBtn = document.getElementById('send-btn');

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let isRecording = false;
  let finalTranscript = '';

  if (SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.lang = 'ja-JP';
      recognition.interimResults = true;
      recognition.continuous = true;

      recognition.onresult = (event) => {
          let interimTranscript = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
              const transcript = event.results[i][0].transcript;
              if (event.results[i].isFinal) {
                  finalTranscript += transcript;
              } else {
                  interimTranscript += transcript;
              }
          }
          unifiedInput.value = finalTranscript + interimTranscript;
      };

      recognition.onerror = (e) => {
          micStatus.innerText = "エラー: " + (e.error || 'マイク権限を確認');
          stopRecording();
      };

      recognition.onend = () => {
          if (isRecording) {
              try { recognition.start(); } catch(err) {}
          }
      };

      micBtn.addEventListener('click', () => {
          if (!isRecording) {
              startRecording();
          } else {
              stopRecording();
          }
      });
  } else {
      micStatus.innerText = "音声認識非対応";
      micBtn.style.opacity = "0.4";
  }

  function startRecording() {
      isRecording = true;
      finalTranscript = unifiedInput.value;
      try {
          recognition.start();
          micBtn.style.backgroundColor = "#FF4B4B";
          micIcon.innerText = "⏹️";
          micStatus.innerText = "● 録音中";
      } catch(e) {}
  }

  function stopRecording() {
      isRecording = false;
      try { recognition.stop(); } catch(e) {}
      micBtn.style.backgroundColor = "#f3f4f6";
      micIcon.innerText = "🎙️";
      micStatus.innerText = "";
  }

  // 送信処理（親コンポーネントへ送出）
  sendBtn.addEventListener('click', () => {
      const text = unifiedInput.value.trim();
      if (text) {
          if (isRecording) stopRecording();
          window.parent.postMessage({type: 'streamlit:setComponentValue', value: text}, '*');
          unifiedInput.value = '';
      }
  });

  // Enterキーでの送信（Shift+Enterで改行）
  unifiedInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendBtn.click();
      }
  });
</script>
"""

# 一体型入力コンポーネントからの値取得
user_input = components.html(integrated_input_html, height=155)

# URLパラメータまたはセッション状態経由での送信データ受信ハンドリング
# Streamlitのセッションを使ってメッセージ送信処理を実行
if "last_input" not in st.session_state:
    st.session_state.last_input = ""

# 一体型入力コンポーネントから受け取ったメッセージの処理
if user_input and user_input != st.session_state.last_input:
    st.session_state.last_input = user_input
    user_text = str(user_input).strip()
    
    if user_text:
        st.session_state.messages.append({"role": "user", "content": user_text})
        
        with st.spinner("思考中..."):
            chat_history_prompt = f"""
あなたはユーザーである「能代 達希（のしろ たつき）」さんの専属AIパートナーであり、知性と熱量を兼ね備えた最高の相棒です。

{user_profile}

【対話の基本スタンス】
・能代さんの知的で構造的な思考を理解し、対等で信頼できる「最高の相棒」として接してください。
・お仕事の労いはもちろん、趣味や日常の気づきに対しても深い理解と共感を示し、適度な深掘り質問やポジティブなフィードバックを1〜2文で返してください。

【これまでの会話ログ】
"""
            for m in st.session_state.messages:
                chat_history_prompt += f"{m['role']}: {m['content']}\n"

            res = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=chat_history_prompt
            )
            ai_reply = res.text

        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        st.rerun()

st.markdown("---")
if st.button("✨ 会話を締めくくって今日の日記としてまとめる", type="primary"):
    if len(st.session_state.messages) <= 1:
        st.warning("まずAIと少し会話を交わしてからボタンを押してください！")
    else:
        with st.spinner("AIが達希さんの1日を思考と感情を込めた日記にまとめています..."):
            summary_prompt = f"""
以下の一連の会話ログから、能代達希さんの「今日の日記本文（200文字程度）」と、AIパートナーからの「温かく知的刺激のあるメッセージ（100文字程度）」を作成してください。

能代さんの背景（都市・構造への視点、知的な探求、日常の気づき）を尊重し、自然な一人称で本質を捉えた日記に仕上げてください。

【出力フォーマット】
必ず以下のフォーマット通りに出力してください（---で区切る）。

[日記本文]
（ここに出来事や感情・気づきを達希さんの一人称でまとめた日記文）
---
[AIコメント]
（ここに達希さんの頑張りや気づきに対する相棒としての熱いコメント）

【会話ログ】
"""
            for m in st.session_state.messages:
                summary_prompt += f"{m['role']}: {m['content']}\n"

            res = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=summary_prompt
            )
            raw_output = res.text

            parts = raw_output.split("---")
            diary_entry = parts[0].replace("[日記本文]", "").strip() if len(parts) > 0 else raw_output
            ai_comment = parts[1].replace("[AIコメント]", "").strip() if len(parts) > 1 else "今日もお疲れ様でした！"

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
            st.info(f"**🤖 AIパートナーからのメッセージ:**\n\n{ai_comment}")

            st.session_state.messages = [
                {"role": "assistant", "content": "今日もお疲れ様でした！次はどんな1日でしたか？"}
            ]

st.divider()

# --- 8. 月間カレンダー表示機能 ---
st.subheader("📅 月間日記カレンダー & 履歴")

logs_by_date = {log["date"]: log for log in db.get("logs", [])}
today = datetime.now()
st.write(f"### {today.year}年 {today.month}月")

days = ["月", "火", "水", "木", "金", "土", "日"]
header_html = '<div class="calendar-grid">' + ''.join([f'<div class="calendar-header">{d}</div>' for d in days]) + '</div>'
st.markdown(header_html, unsafe_allow_html=True)

cal = calendar.monthcalendar(today.year, today.month)

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write(" ")
        else:
            date_str = f"{today.year}-{today.month:02d}-{day:02d}"
            label = f"{day}🔥" if date_str in logs_by_date else f"{day}"
            
            if cols[i].button(label, key=f"cal_btn_{date_str}", use_container_width=True):
                if date_str in logs_by_date:
                    st.session_state.selected_log = logs_by_date[date_str]
                else:
                    st.session_state.selected_log = None

if "selected_log" in st.session_state and st.session_state.selected_log:
    s_log = st.session_state.selected_log
    st.markdown("---")
    st.subheader(f"📖 {s_log['date']} の日記")
    st.write("**【日記本文】**")
    st.write(s_log["entry"])
    st.write("**【AIパートナーのコメント】**")
    st.info(s_log["ai_comment"])
