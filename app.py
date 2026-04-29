import streamlit as st
from openai import OpenAI
import os
from duckduckgo_search import DDGS
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json
import logging
import base64
import io

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SKY_ELITE")

# --- CONFIGURATION ---
st.set_page_config(
    page_title="SKY ELITE AGENT",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLE CUSTOM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-title {
        font-family: 'Space Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -1px;
        background: linear-gradient(135deg, #00d4ff, #7b2fff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .tool-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 2px;
    }

    .source-card {
        background: #1a1a2e;
        border-left: 3px solid #00d4ff;
        padding: 10px 14px;
        border-radius: 6px;
        margin: 6px 0;
        font-size: 0.85rem;
    }

    .stChatMessage {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- MODÈLES DISPONIBLES ---
# openrouter/free = routeur automatique : choisit le meilleur modèle gratuit dispo
MODELS = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-r1:free",
    "deepseek/deepseek-v3:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "google/gemma-3-27b-it:free",
]

# --- CLIENT OPENROUTER ---
@st.cache_resource
def get_client():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        st.error("❌ Variable d'environnement OPENROUTER_API_KEY manquante.")
        st.stop()
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

client = get_client()

# --- OUTILS ---

def chercher_web(query: str, max_results: int = 5) -> dict:
    """Recherche web temps réel via DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return {"success": False, "data": "Aucun résultat trouvé.", "sources": []}
        sources = [{"title": r["title"], "url": r.get("href", ""), "snippet": r["body"]} for r in results]
        text = "\n\n".join([f"[{r['title']}]\n{r['body']}" for r in results])
        return {"success": True, "data": text, "sources": sources}
    except Exception as e:
        logger.error(f"Erreur recherche web: {e}")
        return {"success": False, "data": f"Erreur recherche: {str(e)}", "sources": []}


def extraire_id_youtube(url: str) -> str | None:
    """Extrait l'ID d'une vidéo YouTube."""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None


def lire_youtube(url: str) -> dict:
    """Récupère et retourne la transcription d'une vidéo YouTube."""
    video_id = extraire_id_youtube(url)
    if not video_id:
        return {"success": False, "data": "URL YouTube invalide ou ID introuvable."}
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["fr", "en"])
        text = " ".join([t["text"] for t in transcript])[:10000]
        return {"success": True, "data": text, "video_id": video_id}
    except Exception as e:
        logger.error(f"Erreur transcription YouTube: {e}")
        return {"success": False, "data": f"Transcription indisponible: {str(e)}"}


def lire_fichier(uploaded_file) -> dict:
    """
    Lit et extrait le contenu d'un fichier uploadé.
    Supporte : TXT, MD, CSV, JSON, PDF (texte), PNG, JPG, JPEG, WEBP
    Retourne {"success": bool, "data": str, "type": str, "b64": str|None}
    """
    name = uploaded_file.name
    ext = name.split(".")[-1].lower()
    raw_bytes = uploaded_file.read()

    # --- Fichiers texte ---
    if ext in ["txt", "md", "csv", "json", "py", "html", "xml"]:
        try:
            text = raw_bytes.decode("utf-8", errors="ignore")
            preview = text[:15000]
            return {"success": True, "data": preview, "type": "text", "b64": None, "name": name}
        except Exception as e:
            return {"success": False, "data": f"Erreur lecture texte: {e}", "type": "text", "b64": None, "name": name}

    # --- PDF ---
    elif ext == "pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                pages_text = []
                for page in pdf.pages[:20]:  # max 20 pages
                    t = page.extract_text()
                    if t:
                        pages_text.append(t)
            full_text = "\n\n".join(pages_text)[:15000]
            if not full_text.strip():
                return {"success": False, "data": "PDF sans texte extractible (PDF scanné?).", "type": "pdf", "b64": None, "name": name}
            return {"success": True, "data": full_text, "type": "pdf", "b64": None, "name": name}
        except ImportError:
            return {"success": False, "data": "Module pdfplumber manquant. Ajoutez-le à requirements.txt.", "type": "pdf", "b64": None, "name": name}
        except Exception as e:
            return {"success": False, "data": f"Erreur lecture PDF: {e}", "type": "pdf", "b64": None, "name": name}

    # --- Images ---
    elif ext in ["png", "jpg", "jpeg", "webp", "gif"]:
        try:
            b64 = base64.b64encode(raw_bytes).decode("utf-8")
            mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}
            mime = mime_map.get(ext, "image/png")
            return {"success": True, "data": f"Image : {name}", "type": "image", "b64": b64, "mime": mime, "name": name}
        except Exception as e:
            return {"success": False, "data": f"Erreur lecture image: {e}", "type": "image", "b64": None, "name": name}

    else:
        return {"success": False, "data": f"Format non supporté : .{ext}", "type": "unknown", "b64": None, "name": name}


# --- DÉCISION AGENTIQUE ---

SYSTEM_ROUTER = """Tu es un routeur d'outils intelligent. 
Analyse la requête utilisateur et détermine quels outils utiliser.
Réponds UNIQUEMENT en JSON valide, sans markdown ni explication.

Format de réponse :
{
  "tools": ["web_search", "youtube"],
  "web_query": "requête optimisée pour la recherche web si pertinent",
  "youtube_url": "URL YouTube extraite si présente",
  "reasoning": "explication courte en français"
}

Outils disponibles :
- "web_search" : pour les questions factuelles, actualités, recherches générales
- "youtube" : si l'utilisateur fournit un lien YouTube
- [] (aucun) : si c'est une conversation simple, un calcul, une rédaction, ou si un fichier est fourni
"""

def decider_outils(prompt: str, has_file: bool = False) -> dict:
    """Appelle le LLM pour décider quels outils utiliser."""
    if has_file:
        return {
            "tools": [],
            "web_query": None,
            "youtube_url": None,
            "reasoning": "Fichier détecté — analyse directe sans outil externe."
        }
    try:
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {"role": "system", "content": SYSTEM_ROUTER},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Erreur routeur: {e}")
        has_yt = "youtube.com" in prompt or "youtu.be" in prompt
        return {
            "tools": ["youtube"] if has_yt else ["web_search"],
            "web_query": prompt,
            "youtube_url": prompt if has_yt else None,
            "reasoning": "Décision par défaut (routeur indisponible)"
        }


# --- GESTION MÉMOIRE ---

MAX_HISTORY_TURNS = 10

def get_trimmed_history(messages: list) -> list:
    if len(messages) > MAX_HISTORY_TURNS * 2:
        return messages[-(MAX_HISTORY_TURNS * 2):]
    return messages


# --- PROMPT SYSTÈME PRINCIPAL ---

SYSTEM_MAIN = """Tu es SKY ELITE v5.0, un agent IA expert et autonome.

Règles :
- Analyse les données fournies avec précision et esprit critique
- Cite tes sources quand tu utilises des résultats web
- Si un fichier est fourni, analyse-le en profondeur et réponds aux questions de l'utilisateur à son sujet
- Réponds en français par défaut sauf si l'utilisateur écrit dans une autre langue
- Sois concis, structuré, et utile
- Si les données ne répondent pas à la question, dis-le clairement
"""


# --- INTERFACE ---

st.markdown('<div class="main-title">🛡️ SKY ELITE v5.0</div>', unsafe_allow_html=True)
st.caption("Agent IA Autonome · Recherche Web · Analyse YouTube · Analyse de Fichiers · Mémoire contextuelle")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Agent Settings")

    model_choice = st.selectbox("Modèle LLM", MODELS, index=0)

    st.divider()
    st.subheader("📁 Uploader un fichier")
    uploaded_file = st.file_uploader(
        "PDF, TXT, CSV, JSON, Image...",
        type=["pdf", "txt", "md", "csv", "json", "py", "html", "xml", "png", "jpg", "jpeg", "webp"],
        help="Le fichier sera analysé par l'agent."
    )

    if uploaded_file:
        st.success(f"✅ Fichier prêt : {uploaded_file.name}")
        if st.button("🗑️ Retirer le fichier"):
            uploaded_file = None
            st.rerun()

    st.divider()
    st.subheader("📊 Session Stats")
    msg_count = len(st.session_state.get("messages", []))
    st.metric("Messages", msg_count)
    st.metric("Turns (max)", f"{msg_count // 2}/{MAX_HISTORY_TURNS}")

    st.divider()
    if st.button("🧹 Vider la mémoire", use_container_width=True):
        st.session_state.messages = []
        st.session_state.sources = []
        st.rerun()

    st.divider()
    st.caption("SKY ELITE v5.0 · OpenRouter · DuckDuckGo")


# --- INIT SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sources" not in st.session_state:
    st.session_state.sources = []


# --- AFFICHAGE HISTORIQUE ---
for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant" and i < len(st.session_state.sources):
            srcs = st.session_state.sources[i // 2] if (i // 2) < len(st.session_state.sources) else []
            if srcs:
                with st.expander("📎 Sources utilisées"):
                    for s in srcs:
                        st.markdown(f"""<div class="source-card">
                            <strong>{s.get('title', 'Source')}</strong><br>
                            <a href="{s.get('url', '#')}" target="_blank">{s.get('url', '')}</a>
                        </div>""", unsafe_allow_html=True)


# --- CHAT INPUT ---
if prompt := st.chat_input("Posez une question ou collez un lien YouTube..."):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        full_context = ""
        session_sources = []
        file_result = None
        has_file = uploaded_file is not None

        with st.status("🧠 Réflexion de l'agent...", expanded=True) as status:

            # --- TRAITEMENT FICHIER ---
            if has_file:
                status.write(f"📁 Analyse du fichier : *{uploaded_file.name}*")
                uploaded_file.seek(0)
                file_result = lire_fichier(uploaded_file)
                if file_result["success"]:
                    if file_result["type"] == "image":
                        status.write("🖼️ Image détectée — envoi au modèle vision.")
                    else:
                        full_context += f"=== CONTENU DU FICHIER : {file_result['name']} ===\n{file_result['data']}\n\n"
                        status.write(f"✅ Fichier lu ({len(file_result['data'])} caractères).")
                else:
                    status.write(f"⚠️ {file_result['data']}")
                    full_context += f"⚠️ Fichier : {file_result['data']}\n\n"

            # --- DÉCISION OUTILS ---
            decision = decider_outils(prompt, has_file=has_file)
            tools_used = decision.get("tools", [])
            reasoning = decision.get("reasoning", "")
            status.write(f"💡 Stratégie : {reasoning}")

            # --- EXÉCUTION OUTILS ---
            if "youtube" in tools_used:
                url = decision.get("youtube_url") or prompt
                status.write("📺 Lecture de la vidéo YouTube...")
                result = lire_youtube(url)
                if result["success"]:
                    full_context += f"=== TRANSCRIPTION YOUTUBE ===\n{result['data']}\n\n"
                    status.write("✅ Transcription récupérée.")
                else:
                    full_context += f"⚠️ YouTube : {result['data']}\n\n"
                    status.write(f"⚠️ {result['data']}")

            if "web_search" in tools_used:
                query = decision.get("web_query") or prompt
                status.write(f"🔍 Recherche : *{query}*")
                result = chercher_web(query)
                if result["success"]:
                    full_context += f"=== RÉSULTATS WEB ===\n{result['data']}\n\n"
                    session_sources = result.get("sources", [])
                    status.write(f"✅ {len(session_sources)} sources trouvées.")
                else:
                    full_context += f"⚠️ Web : {result['data']}\n\n"
                    status.write(f"⚠️ {result['data']}")

            if not tools_used and not has_file:
                status.write("💬 Réponse directe (aucun outil nécessaire).")

            status.update(label="🤖 Génération de la réponse...", state="complete")

        # --- APPEL LLM PRINCIPAL ---
        try:
            response_placeholder = st.empty()
            full_response = ""

            # Construction du message utilisateur
            user_message_content = []

            # Cas image : message multimodal
            if file_result and file_result["type"] == "image" and file_result.get("b64"):
                user_message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{file_result['mime']};base64,{file_result['b64']}"
                    }
                })
                user_message_content.append({
                    "type": "text",
                    "text": prompt
                })
            else:
                # Texte enrichi avec contexte
                text_content = prompt
                if full_context:
                    text_content = f"{full_context}\n---\nQuestion : {prompt}"
                user_message_content = text_content

            history = get_trimmed_history(st.session_state.messages[:-1])
            messages_to_send = [{"role": "system", "content": SYSTEM_MAIN}]
            messages_to_send += history
            messages_to_send.append({"role": "user", "content": user_message_content})

            completion = client.chat.completions.create(
                model=model_choice,
                messages=messages_to_send,
                stream=True,
                max_tokens=1500
            )

            for chunk in completion:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_response += delta
                    response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)

            if session_sources:
                with st.expander("📎 Sources utilisées"):
                    for s in session_sources:
                        st.markdown(f"""<div class="source-card">
                            <strong>{s.get('title', 'Source')}</strong><br>
                            <a href="{s.get('url', '#')}" target="_blank">{s.get('url', '')}</a>
                        </div>""", unsafe_allow_html=True)

            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.sources.append(session_sources)

        except Exception as e:
            logger.error(f"Erreur LLM: {e}")
            st.error(f"❌ Erreur Agent : {str(e)}")
