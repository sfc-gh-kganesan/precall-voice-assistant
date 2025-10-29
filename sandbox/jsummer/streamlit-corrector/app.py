import logging
import os

import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Joke Generator",
    page_icon="😄",
    layout="centered"
)

if 'llm' not in st.session_state:
    if not os.getenv("SNOWFLAKE_PAT"):
        st.error("🔑 Set SNOWFLAKE_PAT environment variable.")
        logger.error("SNOWFLAKE_PAT environment variable not set")
    if not os.getenv("SNOWFLAKE_ACCOUNT"):
        st.error("🔑 Set SNOWFLAKE_ACCOUNT environment variable.")
        logger.error("SNOWFLAKE_ACCOUNT environment variable not set")
    else:
        st.session_state.llm = ChatOpenAI(
            model="claude-3-5-sonnet",
            temperature=0.9,
            api_key=os.getenv("SNOWFLAKE_PAT"),
            base_url = f"https://{os.getenv("SNOWFLAKE_ACCOUNT")}.snowflakecomputing.com/api/v2/cortex/openai"
        )
        logger.info(f"LLM initialized")

# Initialize session state
if "joke" not in st.session_state:
    st.session_state.joke = None
if "feedback" not in st.session_state:
    st.session_state.feedback = None
if "comment" not in st.session_state:
    st.session_state.comment = ""

# Title
st.title("🎭 AI Joke Generator")
st.markdown("Generate jokes on any theme using AI!")

system_prompt = """You are a witty comedian who creates clever, family-friendly jokes. 
Generate a single joke based on the theme provided by the user. Keep it concise and funny."""

# Main content area
st.markdown("---")

# Theme input
theme = st.text_input(
    "Enter a joke theme:",
    placeholder="e.g., programming, cats, coffee, etc.",
    help="What should the joke be about?"
)

# Generate button
col1, col2 = st.columns([1, 3])
with col1:
    generate_button = st.button("🎲 Generate Joke", type="primary", use_container_width=True)
    if generate_button:
        logger.info(f"Joke generator button clicked")

# Generate joke
if generate_button:
    logger.info(f"Theme: {theme}")
    st.session_state.feedback = None
    st.session_state.comment = ""
    st.session_state.joke = None
    if not theme:
        st.warning("⚠️ Please enter a theme first!")
        logger.warning("No theme entered")
    else:
        with st.spinner("🤔 Thinking of a joke..."):
            logger.info(f"Generating joke for theme: {theme}")
            try:

           
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=f"Tell me a joke about: {theme}")
                ]
       
                try:
                    response = st.session_state.llm.invoke(messages)
                    st.session_state.joke = response.content
                    logger.info(f"Joke generated: {st.session_state.joke}")
                except Exception as e:
                    logger.error(f"Error generating joke: {str(e)}")
                    st.error(f"❌ Error generating joke: {str(e)}")
                        
            except Exception as e:
                st.error(f"❌ Error generating joke: {str(e)}")

# Display joke and feedback section
if st.session_state.joke:
    st.markdown("---")
    st.markdown("### 😄 Your Joke:")
    
    # Display joke in a nice container
    st.info(st.session_state.joke)
    
    st.markdown("---")
    st.markdown("### 💭 Feedback")
    
    # Thumbs up/down buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("👍 Thumbs Up", use_container_width=True):
            st.session_state.feedback = 1
            logger.info(f"Feedback: {st.session_state.feedback}")
    
    with col2:
        if st.button("👎 Thumbs Down", use_container_width=True):
            st.session_state.feedback = 0
            logger.warning(f"Feedback: {st.session_state.feedback}")

    with col3:
        if st.session_state.feedback == 1:
            st.success("✅ Thanks for the positive feedback!")
        if st.session_state.feedback == 0:
            st.warning("📝 Thanks for your feedback. Let us know how we can improve!")
    
    # Comment section
    comment = st.text_area(
        "Additional comments (optional):",
        value=st.session_state.comment,
        placeholder="What did you think about this joke? Any suggestions?",
        height=100,
        key="comment_input"
    )
    
    # Submit feedback button
    if st.button("📤 Submit Feedback"):
        logger.info(f"Feedback submitted: {comment}")
        st.session_state.comment = comment
        
        # Here you would typically save the feedback to a database
        feedback_data = {
            "theme": theme,
            "joke": st.session_state.joke,
            "rating": st.session_state.feedback,
            "comment": comment
        }
        logger.info(f"Feedback data: {feedback_data}")
        st.success("✅ Feedback submitted! Thank you for helping us improve!")
        
        # Display what was submitted (in a real app, this would be saved to a database)
        with st.expander("📊 Submitted Feedback"):
            st.json(feedback_data)