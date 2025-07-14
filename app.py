import streamlit as st
import os
import io
import sys
import tempfile
from typing import cast
from agents.sql_agent.langgraph_agent import agent as sql_agent  # Import the SQL agent
from agents.rag_agent.langgraph_agent import agent as rag_agent  # Import the RAG agent
from agents.rag_agent.shared import AgentState as RagAgentState
from agents.sql_agent.shared import AgentState as SQLAgentState
from langchain_core.messages import HumanMessage
from utils.main import Store, delete_temp_files

# Configure Streamlit page
st.set_page_config(
    page_title="Smart Shop AI Assistant",
    page_icon="👉🛒 📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []


def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded file to temporary location and return path"""
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f"_{uploaded_file.name}"
    ) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name


def run_sql_query(question: str) -> str:
    """Run SQL agent and return formatted response"""
    try:
        response = cast(
            SQLAgentState,
            sql_agent.invoke(
                {
                    "question": question,
                    "attempts": 0,
                    "curr_question": "",
                    "sql_query": "",
                    "query_result": "",
                    "relevance": False,
                    "sql_error": [],
                }
            ),
        )

        sql_query = response.get("sql_query", "N/A")
        result = response.get("query_result", "No data found.")
        errors = response.get("sql_error", [])

        formatted = f"""
### 📊 SQL Agent Response

**🔍 Question:** {question}

**🧐 Interpreted SQL Query:**
```sql
{sql_query}
```
📄 Result:
{result}

{f"⚠️ Errors: {errors}" if errors else ""}
"""
        return formatted
    except Exception as e:
        return f"❌ Error running SQL Agent:\n{str(e)}"


def run_document_search(question: str) -> str:
    """Run RAG agent and return formatted response"""
    try:
        response = cast(
            RagAgentState,
            rag_agent.invoke(
                {
                    "messages": [HumanMessage(content=question)],
                    "route": "rag",
                    "rag": "",
                    "web": "",
                    "Rag_Citation": None,
                    "Web_Citation": None,
                }
            ),
        )

        messages = response.get("messages", [])
        rag_citation = response.get("Rag_Citation")
        web_citation = response.get("Web_Citation")

        if not messages:
            return "⚠️ No response generated from RAG agent."

        content = "\n\n".join([f"💬 {msg.content}" for msg in messages])

        citation_section = ""
        if rag_citation or web_citation:
            citation_section = "\n\n---\n#### 📚 Citations"
            if rag_citation:
                citation_section += f"\n- From Documents: {rag_citation}"
            if web_citation:
                citation_section += f"\n- From Web: {web_citation}"

        formatted = f"""
### 🔍 RAG Agent Response

**❓ Question:** {question}

{content}

{citation_section}
"""
        return formatted

    except Exception as e:
        return f"❌ Error running RAG Agent:\n{str(e)}"


def extract_text_preview(file_path: str) -> str:
    """Extract text preview from uploaded file"""
    try:
        from utils.ingestor import RobustIngestor

        ingestor = RobustIngestor(input_file=file_path)
        text = ingestor.run()
        if text:
            preview = text[:500]
            if len(text) > 500:
                preview += "..."
            return preview
        return "No text extracted"
    except ImportError:
        return "Text extraction not available (ingestor module not found)"
    except Exception as e:
        return f"Error extracting text: {str(e)}"


def main():
    # Custom CSS for dark green text and styling
    st.markdown(
        """
    <style>
    :root {
        --green-dark: #1a3e1a;  /* Darker green for all text */
        --green-main: #43a047;
        --green-deep: #2e7d32;
        --green-bg-light: #f1f8e9;
        --green-bg-sidebar: #e8f5e9;
    }

    /* Entire app text color */
    html, body, [class*="st-"], .stMarkdown p, .stMarkdown li,
    .stMarkdown strong, .stMarkdown em, .markdown-text-container,
    .stTextInput input, .stTextArea textarea, .stSelectbox select,
    .stRadio label, .stCheckbox label, .stMetric, .stExpander,
    .stAlert, .stSuccess, .stWarning, .stError, .stInfo {
        color: var(--green-dark) !important;
    }

    /* Page background */
    .stApp {
        background-color: white;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: var(--green-bg-sidebar);
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--green-dark) !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: var(--green-main);
        color: white !important;
        border: none;
        border-radius: 0.4rem;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }

    .stButton > button:hover {
        background-color: var(--green-deep);
        color: white !important;
    }

    /* Chat messages */
    .stChatMessage {
        background-color: var(--green-bg-light);
        border-radius: 0.5rem;
        padding: 1rem;
    }

    /* Text areas (Preview + Extracted) */
    .stTextArea textarea {
        background-color: var(--green-bg-light);
        border-radius: 0.4rem;
    }

    /* Expander Header */
    .stExpanderHeader {
        background-color: #c8e6c9;
        font-weight: bold;
        border-radius: 0.3rem;
    }

    /* Metrics */
    .stMetric {
        background-color: #e0f2f1;
        border-radius: 0.6rem;
        padding: 0.7rem;
        font-weight: 600;
    }

    /* File uploader */
    .stFileUploader {
        border: 2px dashed var(--green-main);
        border-radius: 8px;
    }

    /* Tabs */
    .stTabs [role="tab"] {
        color: var(--green-dark) !important;
    }
    .stTabs [role="tab"][aria-selected="true"] {
        background-color: var(--green-bg-light);
        color: var(--green-dark) !important;
    }

    /* Success messages */
    .stAlert.stSuccess {
        background-color: #e8f5e9;
        border-left: 4px solid var(--green-main);
    }
    
    div[data-testid="stChatInput"] textarea {
        color: black !important;
        background-color: white !important;
        border-radius: 0.4rem;
    }

    div[data-testid="stChatInput"] textarea::placeholder {
        color: #e0e0e0 !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.title("📂 Smart Shop AI Assistant 🤖")
    st.markdown("**Welcome to your intelligent business assistant!**")
    st.markdown("---")

    console_buffer = io.StringIO()
    sys.stdout = console_buffer

    debug_mode = st.sidebar.toggle("🧪 Show Debug Logs", value=False)

    with st.sidebar:
        st.header("📁 Document Management")

        temp_store = st.checkbox(
            "🗃️ Store Documents temporary",
            value=True,
            help="Store processed documents in the database temporaliy",
        )

        uploaded_files = st.file_uploader(
            "Upload Documents",
            type=["pdf", "docx", "pptx", "jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="Upload invoices, bills, or other business documents",
        )

        if uploaded_files:
            st.subheader("📄 Uploaded Files")
            for uploaded_file in uploaded_files:
                with st.expander(f"📎 {uploaded_file.name}"):
                    st.write(f"**Size:** {uploaded_file.size} bytes")
                    st.write(f"**Type:** {uploaded_file.type}")

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            f"📥 Process", key=f"process_{uploaded_file.name}"
                        ):
                            with st.spinner("Processing document..."):
                                temp_path = save_uploaded_file(uploaded_file)
                                preview = extract_text_preview(temp_path)
                                st.subheader("📖 Text Preview")
                                st.text_area(
                                    "Extracted Content",
                                    preview,
                                    height=150,
                                    disabled=True,
                                )

                                Store(temp_path, temp_store=temp_store)

                                st.success(
                                    f"✅ {uploaded_file.name} processed successfully!"
                                )
                                st.session_state.uploaded_files.append(
                                    uploaded_file.name
                                )
                                os.unlink(temp_path)

                    with col2:
                        if st.button(f"👁️ Preview", key=f"preview_{uploaded_file.name}"):
                            temp_path = save_uploaded_file(uploaded_file)
                            preview = extract_text_preview(temp_path)
                            st.text_area("Preview", preview, height=200, disabled=True)
                            os.unlink(temp_path)

        if st.button("🗑️ Delete Temp Chunks"):
            delete_temp_files()
            st.success("🧹 Temp chunks deleted from database.")

        st.markdown("---")
        st.header("🤖 AI Agent Selection")
        agent_type = st.radio(
            "Choose Agent Type:",
            ["🔍 RAG Agent (Document Query)", "📊 SQL Agent (Database Query)"],
            help="RAG Agent searches through uploaded documents, SQL Agent queries the database",
        )

        if st.session_state.uploaded_files:
            st.subheader("✅ Processed Documents")
            for file_name in st.session_state.uploaded_files:
                st.write(f"📄 {file_name}")

    st.header("💬 Chat with Smart Shop AI")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask me anything about your business data..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if "RAG Agent" in agent_type:
                    st.write("🔍 **Using RAG Agent** - Searching through documents...")
                    response = run_document_search(prompt)
                elif "SQL Agent" in agent_type:
                    st.write("📊 **Using SQL Agent** - Querying database...")
                    response = run_sql_query(prompt)
                st.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Processed Documents", len(st.session_state.uploaded_files))
    with col2:
        st.metric("💬 Chat Messages", len(st.session_state.messages))
    with col3:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    sys.stdout = sys.__stdout__
    if debug_mode:
        st.markdown("---")
        st.subheader("💻 Debug Terminal Output")
        st.text_area("Console Log", console_buffer.getvalue(), height=200)


if __name__ == "__main__":
    main()
