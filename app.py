import os
import json
from datetime import datetime, timedelta
import streamlit as st
from google import genai

# --- 1. 設定と準備 ---
DATA_FILE = "diary_data.json"

# APIキーはStreamlit Secretsから取得する
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# --- 2. データ保存・読み込み関数 (JSON利用) ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"streak": 0, "last_date": "", "logs": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 3. 連続日数（ストリーク）の更新ロジック ---
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

# --- 4. 画面レイアウト ---
st.title("📖 Gemini AI 日記アプリ")

db = load_data()
st.metric(label="🔥 連続投稿日数", value=f"{db['streak']} 日")
st.divider()

today_str = datetime.now().strftime("%Y-%m-%d")
st.subheader(f"📅 今日の日記 ({today_str})")

user_entry = st.text_area("今日あったことや感じたことを自由に書いてね", height=120)

if st.button("AIに共有して保存する", type="primary"):
    if not user_entry.strip():
        st.warning("日記本文を入力してください！")
    else:
        with st.spinner("Geminiが日記を読んでいます..."):
            prompt = f"""
            以下はユーザーが書いた今日の出来事や日記です。
            温かく親身な友人・ライフコーチとして、共感を示しながら100〜150文字程度でポジティブなフィードバックや労いの言葉を返してください。

            【日記本文】
            {user_entry}
            """
            
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt
            )
            ai_comment = response.text

            new_streak = update_streak(db, today_str)
            
            db["logs"].append({
                "date": today_str,
                "entry": user_entry,
                "ai_comment": ai_comment
            })
            
            save_data(db)

            st.success(f"日記を記録しました！🔥 連続 {new_streak} 日達成！")
            st.markdown(f"**🤖 Geminiからのコメント:**\n\n{ai_comment}")

st.divider()

st.subheader("📚 過去の日記履歴")
if db["logs"]:
    for log in reversed(db["logs"]):
        with st.expander(f"🗓️ {log['date']}"):
            st.write("**【あなたの日記】**")
            st.write(log["entry"])
            st.write("**【AIコメント】**")
            st.info(log["ai_comment"])
else:
    st.write("まだ日記の記録がありません。最初の1日目を記録してみよう！")