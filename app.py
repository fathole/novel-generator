import streamlit as st
import google.generativeai as genai
import json

# --- 頁面設定 ---
st.set_page_config(page_title="AI 小說神器 Pro", page_icon="📚", layout="wide")
st.title("📚 長篇小說輔助器 Pro (寫作模式版)")

# --- 初始化 Session State ---
default_keys = ["world_setting", "char_setting", "story_summary", "style_setting", "chat_history", "redo_stack"]

for key in default_keys:
    if key not in st.session_state:
        if key == "chat_history": st.session_state[key] = []
        elif key == "redo_stack": st.session_state[key] = [] 
        elif key == "world_setting": st.session_state[key] = "例如：賽博龐克風格的2077年台北..."
        elif key == "char_setting": st.session_state[key] = "例如：主角-阿明..."
        elif key == "story_summary": st.session_state[key] = "例如：第一章主角剛偷到了晶片..."
        elif key == "style_setting": st.session_state[key] = "平衡推動劇情，交代背景、對話與情節發展。" # 預設為普通模式

# --- 側邊欄：控制與設定 ---
with st.sidebar:
    st.header("🎮 劇情控制")
    
    col1, col2 = st.columns(2)
    
    # --- Undo 按鈕 ---
    with col1:
        if st.button("↩️ 撤銷 (Undo)", help="刪除上一輪對話"):
            if len(st.session_state.chat_history) >= 2:
                last_ai = st.session_state.chat_history.pop()
                last_user = st.session_state.chat_history.pop()
                st.session_state.redo_stack.append([last_user, last_ai])
                st.rerun() 
            else:
                st.warning("沒有對話可以撤銷了")

    # --- Redo 按鈕 ---
    with col2:
        if st.button("↪️ 重做 (Redo)", help="恢復剛剛撤銷的對話"):
            if st.session_state.redo_stack:
                pair = st.session_state.redo_stack.pop()
                st.session_state.chat_history.extend(pair)
                st.rerun()
            else:
                st.info("沒有可以重做的紀錄")

    # =========== 匯出小說功能 ===========
    st.markdown("---")
    st.header("📖 匯出小說 (Export)")
    
    with st.expander("點擊預覽與匯出 txt"):
        full_story_text = ""
        for msg in st.session_state.chat_history:
            if msg["role"] == "assistant":
                full_story_text += msg["content"] + "\n\n"
        
        edited_story = st.text_area(
            "全書預覽 (可在此直接編輯)", 
            value=full_story_text, 
            height=300,
            help="這裡顯示的是整本小說內容。你可以手動刪除多餘的對話，整理好後再按下載。"
        )
        
        if edited_story:
            st.download_button(
                label="📥 下載成純文字檔 (.txt)",
                data=edited_story,
                file_name="my_full_novel.txt",
                mime="text/plain"
            )

    # =========== 存檔系統 ===========
    st.markdown("---")
    st.header("💾 存檔系統 (JSON)")
    
    # 讀檔
    uploaded_file = st.file_uploader("📂 載入進度", type=["json"])
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            st.session_state.world_setting = data.get("world", "")
            st.session_state.char_setting = data.get("chars", "")
            st.session_state.story_summary = data.get("summary", "")
            # 注意：讀檔時我們不讀取 style，或者你可以選擇讀取。
            # 這裡為了配合新的選單邏輯，我們讓使用者讀檔後自己重新選模式，或者讀取文字描述
            st.session_state.style_setting = data.get("style", "平衡推動劇情...") 
            st.session_state.chat_history = data.get("history", [])
            st.session_state.redo_stack = [] 
            st.success("✅ 讀檔成功！")
        except Exception as e:
            st.error(f"讀檔失敗: {e}")

    # 下載
    save_data = {
        "world": st.session_state.world_setting,
        "chars": st.session_state.char_setting,
        "summary": st.session_state.story_summary,
        "style": st.session_state.style_setting,
        "history": st.session_state.chat_history
    }
    json_str = json.dumps(save_data, indent=4, ensure_ascii=False)
    st.download_button("💾 下載進度", json_str, "novel_save.json", "application/json")

    st.markdown("---")
    
    # =========== 設定區 (含寫作模式) ===========
    st.header("📝 設定區")
    st.text_area("🌍 世界觀", key="world_setting", height=100)
    st.text_area("👥 角色卡", key="char_setting", height=100)
    st.text_area("📖 當前摘要", key="story_summary", height=100)
    
    # --- 新增：寫作模式選擇 ---
    st.header("🎨 寫作模式選擇")
    
    style_options = {
        "普通模式 (Normal)": "平衡推動劇情，交代背景、對話與情節發展。",
        "重甜模式 (Sweet)": "專注於戀愛氛圍、肢體接觸、心理悸動及感官描寫。",
        "熱血模式 (Action)": "專注於戰鬥、招式破壞力、節奏緊湊及爽快感。",
        "催淚模式 (Emotional)": "專注於情感宣洩、遺憾與悲傷的環境烘托。"
    }
    
    selected_style_name = st.selectbox(
        "請選擇本章節的氛圍：",
        options=list(style_options.keys()),
        index=0
    )
    
    # 將主要模式指令寫入 Session State
    base_style = style_options[selected_style_name]
    
    # 額外補充輸入框
    additional_style = st.text_input("➕ 額外補充 (例如：第一人稱)", placeholder="無則留空")
    
    # 組合最終風格指令
    final_style_instruction = base_style
    if additional_style:
        final_style_instruction += f" (補充要求：{additional_style})"
    
    # 更新到 Session State 供主程式使用
    st.session_state.style_setting = final_style_instruction
    
    st.info(f"當前 AI 指令：\n{st.session_state.style_setting}")

    # API Key 處理 (為了安全，請優先使用 Secrets 或輸入框)
    api_key = "AIzaSyDH2QtA3OGja1DpAGTqgGr0U280zWSrMlE"
# --- 主畫面 ---

# 顯示歷史對話
for message in st.session_state.chat_history:
    role_icon = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=role_icon):
        st.markdown(message["content"])

# 輸入區
if prompt := st.chat_input("輸入劇情指令..."):
    
    if not api_key:
        st.warning("請先輸入 API Key")
        st.stop()

    st.session_state.redo_stack = [] # 清空 Redo

    # 1. 記錄 User 輸入
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # 2. 構建 Prompt
    full_prompt = f"""
    你是一個專業的小說家協作 AI。
    【世界觀】：{st.session_state.world_setting}
    【角色】：{st.session_state.char_setting}
    【前情提要】：{st.session_state.story_summary}
    
    【當前寫作風格與指令】：
    {st.session_state.style_setting}
    
    【使用者指令】：
    {prompt}
    
    請繼續撰寫故事。
    """

    # 3. 呼叫 Gemini
    try:
        genai.configure(api_key=api_key)
        # 修正：目前 Gemini 穩定版為 1.5-pro，2.5-pro 尚未公開或不穩定
        model = genai.GenerativeModel('gemini-2.5-pro') 
        
        with st.chat_message("assistant", avatar="🤖"):
            response_placeholder = st.empty()
            response_text = ""
            
            response = model.generate_content(full_prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    response_text += chunk.text
                    response_placeholder.markdown(response_text)
            
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})

    except Exception as e:
        st.error(f"API 錯誤: {e}")