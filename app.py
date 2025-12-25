import streamlit as st
import google.generativeai as genai

# --- 頁面設定 ---
st.set_page_config(page_title="AI 小說產生器", page_icon="📝")
st.title("📝 長篇小說輔助器 (Gemini版)")

# --- 側邊欄：設定與記憶 ---
with st.sidebar:
    st.header("🔧 設定")
    # 這裡讓你在網頁上輸入 API Key，比較安全
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    
    st.header("🧠 劇情記憶庫")
    # 這是核心：手動或自動更新的劇情摘要
    summary = st.text_area("目前劇情摘要 (World State)", 
                           value="主角：李明，剛穿越到異世界，身無分文。", 
                           height=200,
                           help="AI 會根據這裡的內容來寫下一章，寫完一章記得更新這裡。")
    
    st.header("🎨 風格設定")
    style = st.text_input("寫作風格", value="王道熱血，節奏明快，第三人稱")

# --- 初始化 Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 顯示歷史對話 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 主要邏輯區 ---
if prompt := st.chat_input("請輸入指令 (例如：寫第一章，主角遇到了史萊姆)"):
    
    if not api_key:
        st.error("請先在側邊欄輸入 API Key")
        st.stop()

    # 1. 顯示使用者輸入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 組合 Prompt (RAG 的簡易版)
    # 我們把「摘要」+「風格」+「使用者指令」打包在一起
    full_prompt = f"""
    你是專業小說家。
    【長期記憶/劇情摘要】：
    {summary}
    
    【寫作風格】：
    {style}
    
    【當前任務】：
    {prompt}
    
    請根據記憶和風格繼續撰寫故事。
    """

    # 3. 呼叫 Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro') # 建議用 Pro，上下文更長
        
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_text = ""
            
            # 使用串流 (Streaming) 讓字一個個跑出來，更有感
            response = model.generate_content(full_prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    response_text += chunk.text
                    response_placeholder.markdown(response_text)
            
            # 4. 儲存 AI 回覆
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # 5. 提醒使用者更新摘要
            st.info("💡 提示：如果劇情有重大進展，請手動更新側邊欄的「劇情摘要」，以免 AI 之後忘記。")

    except Exception as e:
        st.error(f"發生錯誤: {e}")