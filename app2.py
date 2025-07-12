import streamlit as st
import os
import io
import sys
import tempfile
from typing import cast
from agents.sql_agent.langgraph_agent import agent as sql_agent
from agents.rag_agent.langgraph_agent import agent as rag_agent
from agents.rag_agent.shared import AgentState as RagAgentState
from agents.sql_agent.shared import AgentState as SQLAgentState
from langchain_core.messages import HumanMessage
from utils.main import Store, delete_temp_files


# =============================================
# CUSTOM STYLING
# =============================================
def apply_custom_style():
    st.markdown(
        """
    <style>
        /* Main background */
        .stApp {
            background-color: #ffffff;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #f0f9f0 !important;
            border-right: 1px solid #e1e1e1;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #2e7d32 !important;
        }
        
        /* Buttons */
        .stButton>button {
            background-color: #4caf50 !important;
            color: white !important;
            border-radius: 8px;
            border: none;
            font-weight: 500;
        }
        
        .stButton>button:hover {
            background-color: #388e3c !important;
        }
        
        /* File uploader */
        [data-testid="stFileUploader"] {
            border: 2px dashed #81c784;
            border-radius: 8px;
            padding: 20px;
            background-color: #f5fff5;
        }
        
        /* Chat messages */
        [data-testid="stChatMessage"] {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
        }
        
        /* User message */
        [data-testid="stChatMessage"][aria-label="user"] {
            background-color: #e8f5e9;
        }
        
        /* Assistant message */
        [data-testid="stChatMessage"][aria-label="assistant"] {
            background-color: #f1f8e9;
            border-left: 4px solid #4caf50;
        }
        
        /* Expanders */
        [data-testid="stExpander"] {
            border: 1px solid #c8e6c9;
            border-radius: 8px;
        }
        
        /* Metrics */
        [data-testid="stMetric"] {
            background-color: #f5fff5;
            border-radius: 8px;
            padding: 15px;
        }
        
        /* Text input */
        [data-testid="stTextInput"] input {
            border: 1px solid #a5d6a7 !important;
        }
        
        /* Tabs */
        [role="tab"] {
            color: #2e7d32 !important;
        }
        
        [role="tab"][aria-selected="true"] {
            background-color: #e8f5e9 !important;
            font-weight: bold;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


# =============================================
# APP CONFIGURATION
# =============================================
st.set_page_config(
    page_title="Smart Shop AI Assistant",
    page_icon="🍏",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_style()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []


# =============================================
# HELPER FUNCTIONS (keep your existing functions)
# =============================================
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
<div style='background-color:#f1f8e9; padding:15px; border-radius:8px; border-left:4px solid #4caf50; margin-bottom:15px;'>
<h3 style='color:#2e7d32;'>📊 SQL Agent Response</h3>

<p><strong style='color:#2e7d32;'>🔍 Question:</strong> {question}</p>

<p><strong style='color:#2e7d32;'>🧐 Interpreted SQL Query:</strong></p>
<pre style='background-color:#e8f5e9; padding:10px; border-radius:5px;'>
{sql_query}
</pre>

<p><strong style='color:#2e7d32;'>📄 Result:</strong><br>
{result}</p>

{f"<p style='color:#c62828;'>⚠️ Errors: {errors}</p>" if errors else ""}
</div>
"""
        return formatted
    except Exception as e:
        return f"<div style='background-color:#ffebee; padding:10px; border-radius:5px;'>❌ Error running SQL Agent:<br>{str(e)}</div>"


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
            return "<div style='background-color:#fff8e1; padding:10px; border-radius:5px;'>⚠️ No response generated from RAG agent.</div>"

        content = "\n\n".join([f"💬 {msg.content}" for msg in messages])

        citation_section = ""
        if rag_citation or web_citation:
            citation_section = "<hr style='border-color:#c8e6c9;'>\n<h4 style='color:#2e7d32;'>📚 Citations</h4>"
            if rag_citation:
                citation_section += f"\n<p>📄 From Documents: {rag_citation}</p>"
            if web_citation:
                citation_section += f"\n<p>🌐 From Web: {web_citation}</p>"

        formatted = f"""
<div style='background-color:#f1f8e9; padding:15px; border-radius:8px; border-left:4px solid #4caf50; margin-bottom:15px;'>
<h3 style='color:#2e7d32;'>🔍 RAG Agent Response</h3>

<p><strong style='color:#2e7d32;'>❓ Question:</strong> {question}</p>

{content}

{citation_section}
</div>
"""
        return formatted

    except Exception as e:
        return f"<div style='background-color:#ffebee; padding:10px; border-radius:5px;'>❌ Error running RAG Agent:<br>{str(e)}</div>"


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


# =============================================
# MAIN APP FUNCTION
# =============================================
def main():
    st.title("📂 Smart Shop AI Assistant")
    st.markdown(
        "<p style='color:#2e7d32; font-size:18px;'>Welcome to your intelligent business assistant!</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    console_buffer = io.StringIO()
    sys.stdout = console_buffer

    debug_mode = st.sidebar.toggle("🧪 Show Debug Logs", value=False)

    with st.sidebar:
        st.header("📁 Document Management")

        # Custom styled checkbox
        st.markdown(
            """
        <div style='background-color:#e8f5e9; padding:10px; border-radius:8px; margin-bottom:15px;'>
            <label style='color:#2e7d32; font-weight:500;'>
                <input type='checkbox' checked> 🗃️ Store Documents temporarily
            </label>
            <p style='color:#689f38; font-size:12px; margin-top:5px;'>Store processed documents in the database temporarily</p>
        </div>
        """,
            unsafe_allow_html=True,
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
                with st.expander(f"📎 {uploaded_file.name}", expanded=False):
                    st.write(
                        f"<span style='color:#2e7d32;'>📏 <strong>Size:</strong> {uploaded_file.size} bytes</span>",
                        unsafe_allow_html=True,
                    )
                    st.write(
                        f"<span style='color:#2e7d32;'>📝 <strong>Type:</strong> {uploaded_file.type}</span>",
                        unsafe_allow_html=True,
                    )

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

                                Store(temp_path, temp_store=True)

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
                st.write(
                    f"<span style='color:#2e7d32;'>📄 {file_name}</span>",
                    unsafe_allow_html=True,
                )

    st.header("💬 Chat with Smart Shop AI")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

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
