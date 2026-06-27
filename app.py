import os
import io
import streamlit as st
import anthropic
import PyPDF2
import docx

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Doc Summarizer AI",
    page_icon="📄",
    layout="centered"
)

# ── Styles ───────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 760px; }
    .stButton > button {
        width: 100%;
        background: #7C3AED;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-size: 1rem;
        font-weight: 600;
    }
    .stButton > button:hover { background: #6D28D9; color: white; }
    .result-box {
        background: #F5F3FF;
        border-left: 4px solid #7C3AED;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        margin-top: 1rem;
    }
    .mode-badge {
        display: inline-block;
        background: #7C3AED;
        color: white;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────
st.title("📄 Document Summarizer")
st.caption("Upload any document and get an AI-powered summary instantly.")
st.divider()

# ── Prompts ──────────────────────────────────────────────────
PROMPTS = {
    "🔹 Bullet Points": (
        "Read the document below and produce a clean bullet-point summary.\n"
        "- Use 8-12 bullets\n"
        "- Each bullet is one clear, concise sentence\n"
        "- Start each bullet with a dash (-)\n\n"
        "Document:\n{text}"
    ),
    "📋 Executive Summary": (
        "Write a concise executive summary of the document below.\n"
        "- 3-4 short paragraphs\n"
        "- Start with the core topic/purpose\n"
        "- Cover main findings or arguments\n"
        "- End with conclusions or recommendations\n"
        "- Professional, formal tone\n\n"
        "Document:\n{text}"
    ),
    "💡 Key Takeaways": (
        "Extract the most valuable insights from the document below.\n\n"
        "Output exactly this structure:\n\n"
        "## Key Takeaways\n"
        "1. [Most important insight]\n"
        "2. [Second insight]\n"
        "3. [Third insight]\n"
        "4. [Fourth insight]\n"
        "5. [Fifth insight]\n\n"
        "## Action Items\n"
        "- [Actionable recommendations]\n\n"
        "## One-Line Summary\n"
        "[The entire document in one sentence]\n\n"
        "Document:\n{text}"
    ),
}

# ── File text extractor ──────────────────────────────────────
def extract_text(uploaded_file) -> str:
    ext = uploaded_file.name.split(".")[-1].lower()
    if ext == "txt":
        return uploaded_file.read().decode("utf-8")
    elif ext == "pdf":
        reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        return "".join([p.extract_text() or "" for p in reader.pages])
    elif ext == "docx":
        doc = docx.Document(io.BytesIO(uploaded_file.read()))
        return "\n".join([p.text for p in doc.paragraphs])
    return ""

# ── API key (from Streamlit secrets or manual input) ─────────
api_key = st.secrets.get("ANTHROPIC_API_KEY", "") if hasattr(st, "secrets") else ""
if not api_key:
    api_key = st.sidebar.text_input("🔑 Anthropic API Key", type="password",
                                     help="Get yours at console.anthropic.com")

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    mode = st.radio("Summary Style", list(PROMPTS.keys()))
    model = st.selectbox("Model", ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"],
                         help="Haiku = faster & cheaper. Sonnet = higher quality.")
    max_chars = st.slider("Max document length (chars)", 5000, 50000, 20000, step=5000)
    st.divider()
    st.markdown("**Supported formats**")
    st.markdown("📝 `.txt` &nbsp; 📄 `.pdf` &nbsp; 📃 `.docx`")

# ── Main UI ──────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload your document",
    type=["txt", "pdf", "docx"],
    label_visibility="collapsed"
)

if uploaded:
    with st.spinner("Reading document..."):
        raw_text = extract_text(uploaded)
        truncated = raw_text[:max_chars]

    col1, col2, col3 = st.columns(3)
    col1.metric("Characters", f"{len(raw_text):,}")
    col2.metric("Words (est.)", f"{len(raw_text.split()):,}")
    col3.metric("Sent to AI", f"{len(truncated):,}")

    st.divider()

    if not api_key:
        st.warning("Add your Anthropic API key in the sidebar to summarize.")
    else:
        if st.button("✨ Summarize Now"):
            with st.spinner(f"Claude is reading your document..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    prompt = PROMPTS[mode].format(text=truncated)
                    msg = client.messages.create(
                        model=model,
                        max_tokens=1024,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    result = msg.content[0].text

                    st.markdown(f'<div class="mode-badge">{mode}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="result-box">{result}</div>', unsafe_allow_html=True)

                    st.divider()
                    st.download_button(
                        "⬇️ Download Summary",
                        data=result,
                        file_name=f"summary_{uploaded.name}.txt",
                        mime="text/plain"
                    )
                except anthropic.AuthenticationError:
                    st.error("Invalid API key. Check your key and try again.")
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
else:
    st.markdown("""
    <div style='text-align:center; padding: 3rem 1rem; color: #6B7280;'>
        <div style='font-size: 3rem;'>📂</div>
        <div style='font-size: 1.1rem; margin-top: 0.5rem;'>Drop your file above to get started</div>
        <div style='font-size: 0.9rem; margin-top: 0.3rem;'>Supports PDF, DOCX, and TXT</div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────
st.divider()

