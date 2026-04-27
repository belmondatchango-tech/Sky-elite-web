import streamlit as st
from openai import OpenAI
import os
from duckduckgo_search import DDGS
from youtube_transcript_api import YouTubeTranscriptApi
import re

# --- CONFIGURATION AGENT ---
st.set_page_config(page_title="SKY ELITE AGENT", page_icon="🛡️", layout="wide")

# Client OpenRouter (Utilise la variable d'environnement sur Render)
client = OpenAI(
  base_url="https://openrouter.ai",
  api_key=os.environ.get("OPENROUTER_API_KEY"),
)

# --- FONCTIONS OUTILS (TOOLS) ---

def chercher_web(query):
    """Recherche temps réel sur le Web et Blogs"""
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5)]
            return "\n".join([f"Source: {r['title']}\nContenu: {r['body']}" for r in results])
    except:
        return "Erreur lors de la recherche web."

def extraire_id_youtube(url):
    """Extrait l'ID d'une vidéo YouTube depuis son URL"""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def lire_youtube(url):
    """Récupère la transcription d'une vidéo YouTube"""
    video_id = extraire_id_youtube(url)
    if not video_id: return "URL YouTube invalide."
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['fr', 'en'])
        return " ".join([t['text'] for t in transcript])[:8000] # Limite pour le contexte
    except:
        return "Transcription indisponible pour cette vidéo."

# --- INTERFACE ---
st.title("🛡️ SKY ELITE v4.2 AGENT")
st.caption("Intelligence Autonome | Web Search | YouTube Analysis")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar pour les outils
with st.sidebar:
    st.header("⚙️ Paramètres Agent")
    st.info("Modèle : Gemini 2.0 Flash (Free)")
    if st.button("🧹 Clear Memory"):
        st.session_state.messages = []
        st.rerun()

# Affichage du chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Saisie Agent
if prompt := st.chat_input("Donnez un objectif à l'Agent..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        full_context = ""
        
        # LOGIQUE AGENTIQUE : Détecter si on a besoin du Web ou de YouTube
        with st.status("🛠️ Analyse de la requête...", expanded=True) as status:
            
            # Cas YouTube
            if "youtube.com" in prompt or "youtu.be" in prompt:
                status.write("📺 Détection d'un lien YouTube...")
                video_text = lire_youtube(prompt)
                full_context = f"CONTENU VIDÉO YOUTUBE :\n{video_text}\n\n"
                status.write("✅ Transcription récupérée.")
            
            # Cas Recherche Web
            else:
                status.write("🔍 Activation de la recherche Web...")
                web_results = chercher_web(prompt)
                full_context = f"RÉSULTATS WEB TEMPS RÉEL :\n{web_results}\n\n"
                status.write("✅ Données web collectées.")

            status.update(label="🤖 Synthèse et Analyse critique...", state="complete")

        # Appel OpenRouter avec le contexte enrichi
        try:
            response_placeholder = st.empty()
            full_response = ""
            
            completion = client.chat.completions.create(
                model="google/gemini-2.0-flash-001:free",
                messages=[
                    {"role": "system", "content": "Tu es SKY ELITE v4.2. Analyse les données fournies et réponds avec précision."},
                    {"role": "user", "content": f"{full_context}Question de l'utilisateur : {prompt}"}
                ],
                stream=True
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Erreur Agent : {str(e)}")
 
