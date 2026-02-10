import streamlit as st
import asyncio
import time
from google import genai
from google.genai import types
from main import mcp 

st.set_page_config(page_title="Skylark Drone AI", layout="wide", page_icon="🛸") 

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("🛸 System Control")
    api_key = st.text_input("Gemini API Key", type="password") # should remove the sidebar and make it production ready 
    if st.button("Reset Session"):
        st.session_state.messages = []
        if "chat_session" in st.session_state:
            del st.session_state.chat_session
        st.rerun()

st.title("🛸 Skylark Drone Operations Agent")
st.caption("2-Way Google Sheets Sync | Operational Fleet Intelligence")

if api_key:
    try:
        if "client" not in st.session_state:
            st.session_state.client = genai.Client(api_key=api_key)
        
        if "final_tools" not in st.session_state:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            with st.spinner("Connecting to Google Sheets..."):
                mcp_tools_raw = loop.run_until_complete(mcp.get_tools())
                st.session_state.final_tools = list(mcp_tools_raw.values()) if isinstance(mcp_tools_raw, dict) else mcp_tools_raw

        if "chat_session" not in st.session_state:
            st.session_state.chat_session = st.session_state.client.chats.create(
                model="gemini-2.5-flash", 
                config=types.GenerateContentConfig(
                    system_instruction="""
                    You are the MASTER FLIGHT COORDINATOR.
                    - YOU HAVE ACTUAL WRITE ACCESS. When asked to update, call 'update_pilot_status'.
                    - If a tool call fails or returns 'None', you MUST retry.
                    - Never 'hallucinate' or simulate a JSON response. 
                    - Only confirm an update AFTER the tool returns a 'VERIFIED_SYNC' message.
                    """,
                    tools=st.session_state.final_tools,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig()
                )
            )

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Command: Update P001 to On Leave"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    # RECOVERY & RETRY LOGIC
                    max_retries = 2
                    for i in range(max_retries):
                        try:
                            response = st.session_state.chat_session.send_message(prompt)
                            final_text = response.text
                            
                            # Catching Hallucinations or Silent Tool-Calls
                            if not final_text or "print(" in final_text or "update_pilot_status(" in final_text:
                                recovery = st.session_state.chat_session.send_message(
                                    "The previous tool call results were not summarized. Please check the actual tool output and confirm the database state."
                                )
                                final_text = recovery.text

                            st.markdown(final_text)
                            st.session_state.messages.append({"role": "assistant", "content": final_text})
                            break 
                        except Exception as e:
                            if i < max_retries - 1:
                                st.warning("Connection Reset. Retrying in 2 seconds...")
                                time.sleep(2)
                            else:
                                st.error(f"System Error: {e}")

    except Exception as e:
        st.error(f"Initialization Error: {e}")
else:
    st.info("👈 Enter your Gemini API Key in the sidebar to begin.")