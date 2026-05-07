import streamlit as st
from openai import OpenAI
import os
from duckduckgo_search import DDGS
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json
import logging

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


# --- DÉCISION AGENTIQUE ---

SYSTEM_ROUTER = """Tu es un routeur d'outils intelligent. 
Analyse la requête utilisateur et détermine quels outils utiliser.
Réponds UNIQUEMENT en JSON valide, sans markdown ni explication.

Format de réponse :
{
  "tools": ["web_search", "youtube"],  // liste vide si aucun outil nécessaire
  "web_query": "requête optimisée pour la recherche web si pertinent",
  "youtube_url": "URL YouTube extraite si présente",
  "reasoning": "explication courte en français"
}

Outils disponibles :
- "web_search" : pour les questions factuelles, actualités, recherches générales
- "youtube" : si l'utilisateur fournit un lien YouTube
- [] (aucun) : si c'est une conversation simple, un calcul, une rédaction sans besoin de données externes
"""

def decider_outils(prompt: str) -> dict:
    """Appelle le LLM pour décider quels outils utiliser."""
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001:free",
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
        # Fallback : détection basique
        has_yt = "youtube.com" in prompt or "youtu.be" in prompt
        return {
            "tools": ["youtube"] if has_yt else ["web_search"],
            "web_query": prompt,
            "youtube_url": prompt if has_yt else None,
            "reasoning": "Décision par défaut (routeur indisponible)"
        }


# --- GESTION MÉMOIRE ---

MAX_HISTORY_TURNS = 10  # Limite : 10 échanges max dans le contexte

def get_trimmed_history(messages: list) -> list:
    """Retourne les N derniers messages pour éviter le dépassement de contexte."""
    if len(messages) > MAX_HISTORY_TURNS * 2:
        return messages[-(MAX_HISTORY_TURNS * 2):]
    return messages


# --- PROMPT SYSTÈME PRINCIPAL ---

SYSTEM_MAIN = """Tu es SKY ELITE v5.0, un agent IA expert et autonome.

Règles :
- Analyse les données fournies avec précision et esprit critique
- Cite tes sources quand tu utilises des résultats web
- Réponds en français par défaut sauf si l'utilisateur écrit dans une autre langue
- Sois concis, structuré, et utile
- Si les données ne répondent pas à la question, dis-le clairement
"""


# --- INTERFACE ---

st.markdown('<div class="main-title">🛡️ SKY ELITE v5.0</div>', unsafe_allow_html=True)
st.caption("Agent IA Autonome · Recherche Web · Analyse YouTube · Mémoire contextuelle")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Agent Settings")

    model_choice = st.selectbox(
        "Modèle LLM",
        ["google/gemini-2.0-flash-001:free", "meta-llama/llama-3.1-8b-instruct:free", "mistralai/mistral-7b-instruct:free"],
        index=0
    )

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
        # Afficher les sources associées à ce message
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

        # ÉTAPE 1 : DÉCISION AGENTIQUE
        with st.status("🧠 Réflexion de l'agent...", expanded=True) as status:

            decision = decider_outils(prompt)
            tools_used = decision.get("tools", [])
            reasoning = decision.get("reasoning", "")

            status.write(f"💡 Stratégie : {reasoning}")

            # ÉTAPE 2 : EXÉCUTION DES OUTILS
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

            if not tools_used:
                status.write("💬 Réponse directe (aucun outil nécessaire).")

            status.update(label="🤖 Génération de la réponse...", state="complete")

        # ÉTAPE 3 : APPEL LLM PRINCIPAL
        try:
            response_placeholder = st.empty()
            full_response = ""

            # Construction du message utilisateur enrichi
            user_message = prompt
            if full_context:
                user_message = f"{full_context}\n---\nQuestion : {prompt}"

            # Historique tronqué + nouveau message
            history = get_trimmed_history(st.session_state.messages[:-1])  # Exclure le dernier (déjà ajouté)
            messages_to_send = [{"role": "system", "content": SYSTEM_MAIN}]
            messages_to_send += history
            messages_to_send.append({"role": "user", "content": user_message})

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

            # Afficher les sources
            if session_sources:
                with st.expander("📎 Sources utilisées"):
                    for s in session_sources:
                        st.markdown(f"""<div class="source-card">
                            <strong>{s.get('title', 'Source')}</strong><br>
                            <a href="{s.get('url', '#')}" target="_blank">{s.get('url', '')}</a>
                        </div>""", unsafe_allow_html=True)

            # Sauvegarder
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.sources.append(session_sources)

        except Exception as e:
            logger.error(f"Erreur LLM: {e}")
            st.error(f"❌ Erreur Agent : {str(e)}")
