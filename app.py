import streamlit as st
import google.generativeai as genai
import json
import re

# --- 頁面設定 ---
st.set_page_config(page_title="AI 小說神器 Ultimate", page_icon="🚀", layout="wide")
st.title("🚀 長篇小說輔助器 (顯示修復版)")

# --- 初始化 Session State ---
default_keys = ["world_setting", "char_setting", "story_summary", "style_setting", "chat_history", "redo_stack", "suggested_options"]

# 初始化一個計數器，用來強制刷新摘要框
if "summary_key_id" not in st.session_state: st.session_state.summary_key_id = 0

for key in default_keys:
    if key not in st.session_state:
        if key == "chat_history": st.session_state[key] = []
        elif key == "redo_stack": st.session_state[key] = [] 
        elif key == "suggested_options": st.session_state[key] = [] 
        elif key == "world_setting": st.session_state[key] = "例如：賽博龐克風格的2077年台北..."
        elif key == "char_setting": st.session_state[key] = "例如：主角-阿明..."
        elif key == "story_summary": st.session_state[key] = "例如：第一章主角剛偷到了晶片..."
        elif key == "style_setting": st.session_state[key] = "平衡推動劇情，交代背景、對話與情節發展。"

# --- 核心功能 1：自動更新摘要 (含強制刷新邏輯) ---
def update_summary_automatically(new_content, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        summary_prompt = f"""
        你是專業的小說編輯。
        【舊的摘要】：{st.session_state.story_summary}
        【剛剛新產生的劇情】：{new_content}
        【任務】：請將「新劇情」的重點合併進「舊摘要」中，形成一份最新的劇情大綱。
        1. 保持精簡（約 300-500 字）。
        2. 直接輸出新的摘要內容。
        """
        response = model.generate_content(summary_prompt)
        new_summary = response.text.strip()

        # 更新資料
        st.session_state.story_summary = new_summary
        # 關鍵：讓 ID + 1，這樣 Streamlit 認為這是一個全新的輸入框，就會重新讀取 value
        st.session_state.summary_key_id += 1
        
        return True
    except Exception as e:
        st.error(f"自動摘要失敗: {e}")
        return False

# --- 核心功能 2：生成劇情 ---
def handle_generation(user_input, api_key):
    st.session_state.redo_stack = []
    st.session_state.suggested_options = [] 
    
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    full_prompt = f"""
    你是一個專業的小說家協作 AI。
    【世界觀】：{st.session_state.world_setting}
    【角色】：{st.session_state.char_setting}
    【前情提要】：{st.session_state.story_summary}
    【指令/風格】：{st.session_state.style_setting}
    【當前任務】：{user_input}
    請繼續撰寫故事。
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        with st.spinner("AI 正在撰寫故事..."):
            response = model.generate_content(full_prompt)
            ai_reply = response.text
            
        st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
        
        # 自動更新摘要
        with st.status("🤖 正在自動整理劇情摘要...", expanded=True) as status:
            success = update_summary_automatically(ai_reply, api_key)
            if success:
                status.update(label="✅ 摘要已自動更新！", state="complete", expanded=False)
        
        st.rerun() 

    except Exception as e:
        st.error(f"API 錯誤: {e}")

# --- 側邊欄 ---
with st.sidebar:
    st.header("🎮 劇情控制")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↩️ 撤銷 (Undo)"):
            if len(st.session_state.chat_history) >= 2:
                last_ai = st.session_state.chat_history.pop()
                last_user = st.session_state.chat_history.pop()
                st.session_state.redo_stack.append([last_user, last_ai])
                st.session_state.suggested_options = []
                st.rerun() 
    with col2:
        if st.button("↪️ 重做 (Redo)"):
            if st.session_state.redo_stack:
                pair = st.session_state.redo_stack.pop()
                st.session_state.chat_history.extend(pair)
                st.rerun()

    api_key = "AIzaSyDH2QtA3OGja1DpAGTqgGr0U280zWSrMlE"

    st.markdown("---")
    
    # 🔮 幫我想三個後續
    st.header("💡 靈感助手")
    if st.button("🔮 幫我想 3 個後續發展", use_container_width=True):
        if not api_key:
            st.error("請先輸入 API Key")
        else:
            with st.spinner("正在構思劇情分支..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-pro')
                    brainstorm_prompt = f"""
                    你是一個小說劇情策劃。
                    【前情提要】：{st.session_state.story_summary}
                    【世界觀】：{st.session_state.world_setting}
                    請構思 **3 個截然不同的後續發展**。
                    請嚴格回傳 JSON 格式：["選項A內容", "選項B內容", "選項C內容"]
                    """
                    response = model.generate_content(brainstorm_prompt)
                    text = re.sub(r"```json|```", "", response.text).strip()
                    options = json.loads(text)
                    if isinstance(options, list):
                        st.session_state.suggested_options = options[:3]
                        st.rerun()
                except Exception as e:
                    st.error(f"生成選項失敗: {e}")

    st.markdown("---")
    st.header("📖 匯出與存檔")
    with st.expander("匯出 TXT (預覽)"):
        full_txt = "".join([m["content"]+"\n\n" for m in st.session_state.chat_history if m["role"] == "assistant"])
        edited_txt = st.text_area("編輯內容", full_txt, height=200)
        if edited_txt:
            st.download_button("📥 下載 TXT", edited_txt, "story.txt", "text/plain")

    save_data = {k: st.session_state[k] for k in default_keys}
    st.download_button("💾 下載 JSON (存檔)", json.dumps(save_data, indent=4, ensure_ascii=False), "save.json", "application/json")
    
    uploaded_file = st.file_uploader("📂 載入 JSON", type=["json"])
    if uploaded_file:
        try:
            data = json.load(uploaded_file)
            for k in default_keys: 
                if k in data: st.session_state[k] = data[k]
            # 讀檔成功後，也要強制刷新 ID，確保顯示正確
            st.session_state.summary_key_id += 1
            st.success("讀檔成功")
            st.rerun()
        except: pass

    st.markdown("---")
    st.header("📝 設定與風格")
    st.text_area("🌍 世界觀", key="world_setting", height=100)
    st.text_area("👥 角色卡", key="char_setting", height=100)
    
    # === [關鍵修改：動態 Key] ===
    # 定義一個 callback 函數，當用戶手動打字時，存回主變數
    def on_summary_change():
        current_widget_key = f"summary_widget_{st.session_state.summary_key_id}"
        st.session_state.story_summary = st.session_state[current_widget_key]

    st.text_area(
        "📖 當前摘要 (AI 自動更新 + 可手動修訂)", 
        value=st.session_state.story_summary, 
        key=f"summary_widget_{st.session_state.summary_key_id}", # 動態 ID
        on_change=on_summary_change,
        height=150
    )
    # ==========================
    
    style_map = {
        "普通模式": "平衡推動劇情，交代背景、對話與情節發展。",
        "重甜模式": "專注於戀愛氛圍、肢體接觸、心理悸動及感官描寫。",
        "熱血模式": "專注於戰鬥、招式破壞力、節奏緊湊及爽快感。",
        "催淚模式": "專注於情感宣洩、遺憾與悲傷的環境烘托。"
    }
    sel_style = st.selectbox("風格", list(style_map.keys()))
    extra = st.text_input("補充風格", placeholder="例：第一人稱")
    st.session_state.style_setting = style_map[sel_style] + (f" ({extra})" if extra else "")

# --- 主畫面 ---
for msg in st.session_state.chat_history:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

if st.session_state.suggested_options:
    st.info("👇 點擊下方按鈕選擇劇情走向：")
    cols = st.columns(3)
    for i, opt in enumerate(st.session_state.suggested_options):
        with cols[i]:
            if st.button(f"選項 {i+1}\n\n{opt}", use_container_width=True):
                if not api_key: st.warning("請輸入 API Key")
                else: handle_generation(f"請依照此方向發展：{opt}", api_key)

if prompt := st.chat_input("輸入劇情指令..."):
    if not api_key: st.warning("請輸入 API Key")
    else: handle_generation(prompt, api_key)