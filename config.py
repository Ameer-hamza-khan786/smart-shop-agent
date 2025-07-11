from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OLLAMA_URL = "http://localhost:11434"  # Local Ollama API
DATABASE_URL = "postgresql://postgres:hamza@localhost:5432/smartinventory"
V_DATABASE_URL = "postgresql://postgres:hamza@localhost:5432/vector_db"

SHOP_KEEPER_SHOP_TYPE = "Auto_Parts_Shop"
LANGUAGE_PREFER = "Hindi"

EMBEDDING_MODEL = "nomic-embed-text"

# GLOBAL_LLM = ChatOllama(temperature=0, model="llama3.2", base_url=OLLAMA_URL)

GLOBAL_LLM = ChatGroq(model="gemma2-9b-it", temperature=0, api_key=GROQ_API_KEY)
# GLOBAL_LLM_G = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

# GLOBAL_LLM = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
EMBEDDING_MODEL = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
