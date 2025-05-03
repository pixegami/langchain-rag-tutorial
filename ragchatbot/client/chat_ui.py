import streamlit as st
import requests
import time

# Set page title and favicon
st.set_page_config(page_title="Sales ChatBot", page_icon="🤖")

# Custom CSS to improve appearance
st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
    }
    .user-message {
        background-color: #fb8200;
    }
    .bot-message {
        background-color: #2533cc;
    }
    .message-content {
        margin-left: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# App title
st.title("🤖 سروریار")
st.markdown("دستیار فروش هوشمند ایران سرور")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f"""
            <div class="chat-message user-message">
                <div>👤</div>
                <div class="message-content">{message["content"]}</div>
            </div>
        """, unsafe_allow_html=True)
    else:  # bot message
        st.markdown(f"""
            <div class="chat-message bot-message">
                <div>🤖</div>
                <div class="message-content">{message["content"]}</div>
            </div>
        """, unsafe_allow_html=True)

# Configuration in sidebar
with st.sidebar:
    st.header("Configuration")
    api_url = st.text_input("API URL", value="http://127.0.0.1:8080", help="The URL of your FastAPI server")
    secret = st.text_input("🔑 API Secret Key", type="password", help="Secret key for authentication")

# Input form
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_area("💬 سوال خود را بپرسید:", key="user_question", height=100)
    submit_button = st.form_submit_button("ارسال")

if submit_button and user_input:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Show "thinking" message
    thinking_placeholder = st.empty()
    thinking_placeholder.markdown("🤖 در حال فکر کردن...")
    
    try:
        # Step 1: Get token
        token_resp = requests.post(f"{api_url}/get_token/", json={"secret": secret})
        if token_resp.status_code != 200:
            error_detail = token_resp.json().get("detail", {}).get("msg", "خطای نامشخص")
            st.error(f"خطای توکن: {error_detail}")
        else:
            token = token_resp.json()["token"]
            
            # Step 2: Send question with token in header
            headers = {"x-api-key": token}
            chat_resp = requests.post(
                f"{api_url}/chat", 
                json={"query": user_input},
                headers=headers
            )
            
            # Remove thinking message
            thinking_placeholder.empty()
            
            if chat_resp.status_code == 200:
                bot_response = chat_resp.json()["answer"]
                # Add bot response to chat history
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
                # Display the new response
                st.markdown(f"""
                    <div class="chat-message bot-message">
                        <div>🤖</div>
                        <div class="message-content">{bot_response}</div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                error_detail = chat_resp.json().get("detail", {}).get("msg", "خطای نامشخص")
                st.error(f"خطای گفتگو: {error_detail}")
    except Exception as e:
        thinking_placeholder.empty()
        st.error(f"خطا: {str(e)}")

# Add a small credit at the bottom
st.markdown("---")
st.markdown("Made with ❤️ by Erfan Mahmoudi")