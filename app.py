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
import urllib.parse

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SKY_ELITE")

# --- CONFIGURATION ---
st.set_page_config(
    page_title="SKY ELITE v6.0",
    page_icon="✝️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main-title {
        font-family: 'Space Mono', monospace;
        font-size: 2rem; font-weight: 700; letter-spacing: -1px;
        background: linear-gradient(135deg, #00d4ff, #7b2fff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .source-card {
        background: #1a1a2e; border-left: 3px solid #00d4ff;
        padding: 10px 14px; border-radius: 6px; margin: 6px 0; font-size: 0.85rem;
    }
    .stChatMessage { border-radius: 12px; }
    .mic-container {
        display: flex; align-items: center; gap: 14px;
        background: #0f0f1a; border: 1px solid #2a2a4a;
        border-radius: 14px; padding: 10px 16px; margin: 8px 0;
    }
    #micBtn {
        background: linear-gradient(135deg, #00d4ff, #7b2fff);
        color: white; border: none; border-radius: 50%;
        width: 52px; height: 52px; font-size: 1.4rem;
        cursor: pointer; box-shadow: 0 4px 15px rgba(0,212,255,0.35);
        transition: all 0.3s; flex-shrink: 0;
    }
    #micBtn:hover { transform: scale(1.1); }
    #micBtn.recording {
        background: linear-gradient(135deg, #ff4444, #ff0080);
        animation: pulse 1s infinite;
    }
    @keyframes pulse {
        0%,100% { box-shadow: 0 0 0 0 rgba(255,68,68,0.5); }
        50% { box-shadow: 0 0 0 14px rgba(255,68,68,0); }
    }
    #micStatus { color: #aaa; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# --- MODÈLES ---
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
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

client = get_client()

# ============================================================
# OUTILS
# ============================================================

def chercher_web(query: str, max_results: int = 5) -> dict:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return {"success": False, "data": "Aucun résultat.", "sources": []}
        sources = [{"title": r["title"], "url": r.get("href", ""), "snippet": r["body"]} for r in results]
        text = "\n\n".join([f"[{r['title']}]\n{r['body']}" for r in results])
        return {"success": True, "data": text, "sources": sources}
    except Exception as e:
        return {"success": False, "data": f"Erreur: {e}", "sources": []}


def extraire_id_youtube(url: str):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None


def lire_youtube(url: str) -> dict:
    video_id = extraire_id_youtube(url)
    if not video_id:
        return {"success": False, "data": "URL YouTube invalide."}
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["fr", "en"])
        text = " ".join([t["text"] for t in transcript])[:10000]
        return {"success": True, "data": text, "video_id": video_id}
    except Exception as e:
        return {"success": False, "data": f"Transcription indisponible: {e}"}


def lire_fichier(uploaded_file) -> dict:
    name = uploaded_file.name
    ext = name.split(".")[-1].lower()
    raw_bytes = uploaded_file.read()

    if ext in ["txt", "md", "json", "py", "html", "xml"]:
        text = raw_bytes.decode("utf-8", errors="ignore")[:15000]
        return {"success": True, "data": text, "type": "text", "b64": None, "name": name}

    elif ext == "csv":
        try:
            import pandas as pd
            df = pd.read_csv(io.BytesIO(raw_bytes))
            preview = df.to_string(max_rows=100)
            return {"success": True, "data": preview, "type": "csv", "b64": None, "name": name, "df": df}
        except Exception as e:
            return {"success": False, "data": f"Erreur CSV: {e}", "type": "csv", "b64": None, "name": name}

    elif ext in ["xlsx", "xls"]:
        try:
            import pandas as pd
            df = pd.read_excel(io.BytesIO(raw_bytes))
            preview = df.to_string(max_rows=100)
            return {"success": True, "data": preview, "type": "excel", "b64": None, "name": name, "df": df}
        except Exception as e:
            return {"success": False, "data": f"Erreur Excel: {e}", "type": "excel", "b64": None, "name": name}

    elif ext == "pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                pages_text = [p.extract_text() for p in pdf.pages[:20] if p.extract_text()]
            full_text = "\n\n".join(pages_text)[:15000]
            if not full_text.strip():
                return {"success": False, "data": "PDF sans texte extractible.", "type": "pdf", "b64": None, "name": name}
            return {"success": True, "data": full_text, "type": "pdf", "b64": None, "name": name}
        except ImportError:
            return {"success": False, "data": "pdfplumber manquant dans requirements.txt", "type": "pdf", "b64": None, "name": name}
        except Exception as e:
            return {"success": False, "data": f"Erreur PDF: {e}", "type": "pdf", "b64": None, "name": name}

    elif ext in ["png", "jpg", "jpeg", "webp", "gif"]:
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}
        return {"success": True, "data": f"Image: {name}", "type": "image",
                "b64": b64, "mime": mime_map.get(ext, "image/png"), "name": name}

    return {"success": False, "data": f"Format non supporté: .{ext}", "type": "unknown", "b64": None, "name": name}


def generer_image(prompt_img: str) -> str:
    """Génère une image via Pollinations.ai (gratuit, sans clé API)."""
    encoded = urllib.parse.quote(prompt_img)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=512&nologo=true"


def tts_gtts(text: str, lang: str = "fr") -> bytes:
    """Synthèse vocale gTTS — retourne bytes MP3."""
    try:
        from gtts import gTTS
        clean = re.sub(r"[*_`#>\[\]|\\]", "", text)
        clean = re.sub(r"\n+", ". ", clean).strip()[:1200]
        tts = gTTS(text=clean, lang=lang, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        logger.error(f"TTS erreur: {e}")
        return None


def detecter_langue(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["the ", " is ", " are ", "what", "how ", "hello", "hi ", "thank"]):
        return "en"
    elif any(w in t for w in ["hola", " es ", "gracias", "buenos", "como "]):
        return "es"
    elif any(w in t for w in ["wie ", " das ", " ist ", "bitte", "danke"]):
        return "de"
    return "fr"


def afficher_graphique(df):
    try:
        import plotly.express as px
        num_cols = df.select_dtypes(include="number").columns.tolist()
        str_cols = df.select_dtypes(include="object").columns.tolist()
        if not num_cols:
            st.info("Aucune colonne numérique pour le graphique.")
            return
        if str_cols and num_cols:
            fig = px.bar(df.head(25), x=str_cols[0], y=num_cols[0],
                         title=f"📊 {num_cols[0]} par {str_cols[0]}")
        elif len(num_cols) >= 2:
            fig = px.scatter(df, x=num_cols[0], y=num_cols[1],
                             title=f"📊 {num_cols[0]} vs {num_cols[1]}")
        else:
            fig = px.line(df[num_cols].head(50), title="📊 Évolution")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        logger.error(f"Graphique: {e}")


def exporter_conversation(messages: list) -> bytes:
    lines = ["SKY ELITE v6.0 — Conversation exportée\n" + "="*50 + "\n\n"]
    for m in messages:
        role = "👤 Vous" if m["role"] == "user" else "🤖 SKY"
        lines.append(f"{role}:\n{m['content']}\n\n{'─'*50}\n\n")
    return "".join(lines).encode("utf-8")


# ============================================================
# ROUTEUR AGENTIQUE
# ============================================================

SYSTEM_ROUTER = """Tu es un routeur d'outils. Réponds UNIQUEMENT en JSON valide sans markdown.

{
  "tools": [],
  "web_query": "requête si web_search",
  "youtube_url": "URL si youtube",
  "image_prompt": "description en anglais si generate_image",
  "reasoning": "explication courte"
}

Outils disponibles:
- "web_search" : questions factuelles, actualités, informations récentes
- "youtube" : si URL YouTube présente dans le message
- "generate_image" : si l'utilisateur demande de créer/générer/dessiner/illustrer une image
- [] : conversation simple, calcul, rédaction, fichier fourni
"""

def decider_outils(prompt: str, has_file: bool = False) -> dict:
    if has_file:
        return {"tools": [], "web_query": None, "youtube_url": None, "image_prompt": None,
                "reasoning": "Fichier détecté — analyse directe."}
    try:
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {"role": "system", "content": SYSTEM_ROUTER},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300, temperature=0.1
        )
        raw = re.sub(r"```json|```", "", response.choices[0].message.content.strip()).strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Routeur: {e}")
        has_yt = "youtube.com" in prompt or "youtu.be" in prompt
        return {
            "tools": ["youtube"] if has_yt else ["web_search"],
            "web_query": prompt, "youtube_url": prompt if has_yt else None,
            "image_prompt": None, "reasoning": "Décision par défaut"
        }


# ============================================================
# MÉMOIRE
# ============================================================

MAX_HISTORY_TURNS = 10

def get_trimmed_history(messages: list) -> list:
    if len(messages) > MAX_HISTORY_TURNS * 2:
        return messages[-(MAX_HISTORY_TURNS * 2):]
    return messages


# ============================================================
# PROMPT PRINCIPAL
# ============================================================

SYSTEM_MAIN = """Tu es SKY ELITE v6.0, un agent IA expert, autonome et polyvalent.

Capacités :
- Recherche web en temps réel
- Analyse de fichiers (PDF, CSV, Excel, images, code)
- Génération d'images via description
- Analyse de vidéos YouTube
- Conversation vocale naturelle multilingue

Règles :
- Réponds dans la langue de l'utilisateur automatiquement
- Cite tes sources quand tu utilises des résultats web
- Sois concis, structuré et utile
- Pour les fichiers, analyse-les en profondeur
- Tes réponses seront lues à voix haute : évite les symboles markdown excessifs, préfère des phrases claires
"""


# ============================================================
# INTERFACE
# ============================================================

st.markdown('<div class="main-title">🛡️ SKY ELITE v6.0</div>', unsafe_allow_html=True)
st.caption("Agent IA · Web · YouTube · Fichiers · Images · Voix · Export")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Paramètres")
    model_choice = st.selectbox("Modèle LLM", MODELS, index=0)

    st.divider()
    st.subheader("🔊 Voix")
    tts_enabled = st.toggle("Réponses vocales", value=True)
    tts_autoplay = st.toggle("Lecture automatique", value=True)

    st.divider()
    st.subheader("📁 Fichier")
    uploaded_file = st.file_uploader(
        "PDF, TXT, CSV, Excel, Image...",
        type=["pdf", "txt", "md", "csv", "xlsx", "xls", "json", "py", "html", "xml", "png", "jpg", "jpeg", "webp"],
    )
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")

    st.divider()
    st.subheader("📊 Session")
    msg_count = len(st.session_state.get("messages", []))
    st.metric("Messages", msg_count)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Vider", use_container_width=True):
            st.session_state.messages = []
            st.session_state.sources = []
            st.rerun()
    with col2:
        if msg_count > 0:
            st.download_button(
                "📥 Export",
                data=exporter_conversation(st.session_state.get("messages", [])),
                file_name="sky_elite_conversation.txt",
                mime="text/plain",
                use_container_width=True
            )

    st.divider()
    st.caption("SKY ELITE v6.0 · OpenRouter · Pollinations · gTTS")


# --- INIT SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sources" not in st.session_state:
    st.session_state.sources = []


# --- HISTORIQUE ---
for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant" and i < len(st.session_state.sources):
            srcs = st.session_state.sources[i // 2] if (i // 2) < len(st.session_state.sources) else []
            if srcs:
                with st.expander("📎 Sources"):
                    for s in srcs:
                        st.markdown(f"""<div class="source-card">
                            <strong>{s.get('title','Source')}</strong><br>
                            <a href="{s.get('url','#')}" target="_blank">{s.get('url','')}</a>
                        </div>""", unsafe_allow_html=True)


# ============================================================
# ENTRÉE VOCALE — Web Speech API (Chrome compatible)
# ============================================================

VOICE_HTML = """
<div class="mic-container" style="display:flex;align-items:center;gap:14px;background:#0f0f1a;
     border:1px solid #2a2a4a;border-radius:14px;padding:10px 16px;margin:8px 0;">
  <button id="micBtn" onclick="toggleMic()" title="Parler à SKY"
    style="background:linear-gradient(135deg,#00d4ff,#7b2fff);color:white;border:none;
    border-radius:50%;width:52px;height:52px;font-size:1.4rem;cursor:pointer;
    box-shadow:0 4px 15px rgba(0,212,255,0.35);transition:all 0.3s;flex-shrink:0;">🎤</button>
  <div id="micStatus" style="color:#aaa;font-size:0.9rem;">
    Appuyez sur 🎤 et parlez — Chrome requis
  </div>
</div>

<style>
  @keyframes pulse {
    0%,100%{box-shadow:0 0 0 0 rgba(255,68,68,0.5);}
    50%{box-shadow:0 0 0 14px rgba(255,68,68,0);}
  }
  #micBtn.rec {
    background:linear-gradient(135deg,#ff4444,#ff0080) !important;
    animation:pulse 1s infinite;
  }
</style>

<script>
var recog = null;
var isRec = false;

function toggleMic() {
  if (!window.webkitSpeechRecognition && !window.SpeechRecognition) {
    document.getElementById('micStatus').innerHTML = '⚠️ Utilisez Google Chrome pour la voix';
    return;
  }
  if (isRec) { recog.stop(); return; }

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recog = new SR();
  recog.lang = 'fr-FR';
  recog.continuous = false;
  recog.interimResults = true;

  recog.onstart = function() {
    isRec = true;
    document.getElementById('micBtn').classList.add('rec');
    document.getElementById('micBtn').innerHTML = '🔴';
    document.getElementById('micStatus').innerHTML = '🎙️ Écoute...';
  };

  recog.onresult = function(e) {
    var final = '', interim = '';
    for (var i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) final += e.results[i][0].transcript;
      else interim += e.results[i][0].transcript;
    }
    document.getElementById('micStatus').innerHTML = '💬 ' + (final || interim);
    if (final) {
      // Copier dans le champ texte Streamlit via le DOM
      var inputs = window.parent.document.querySelectorAll('input[type=text]');
      for (var j = 0; j < inputs.length; j++) {
        var p = inputs[j].getAttribute('placeholder') || '';
        if (p.indexOf('Parlez') !== -1 || p.indexOf('tapez') !== -1 || p.indexOf('Tapez') !== -1) {
          var nativeInput = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value');
          nativeInput.set.call(inputs[j], final);
          inputs[j].dispatchEvent(new Event('input', {bubbles: true}));
          break;
        }
      }
    }
  };

  recog.onerror = function(e) {
    document.getElementById('micStatus').innerHTML = '⚠️ Erreur: ' + e.error;
    isRec = false;
    document.getElementById('micBtn').classList.remove('rec');
    document.getElementById('micBtn').innerHTML = '🎤';
  };

  recog.onend = function() {
    isRec = false;
    document.getElementById('micBtn').classList.remove('rec');
    document.getElementById('micBtn').innerHTML = '🎤';
    var s = document.getElementById('micStatus').innerHTML;
    if (s.indexOf('💬') !== -1) {
      document.getElementById('micStatus').innerHTML = '✅ ' + s.replace('💬 ','') + ' — appuyez Envoyer';
    } else {
      document.getElementById('micStatus').innerHTML = 'Appuyez sur 🎤 et parlez';
    }
  };

  recog.start();
}
</script>
"""

st.components.v1.html(VOICE_HTML, height=90)

# Champ texte + bouton envoyer
col_input, col_send = st.columns([5, 1])
with col_input:
    voice_text = st.text_input(
        "msg",
        placeholder="Parlez avec le 🎤 ou tapez ici...",
        label_visibility="collapsed",
        key="voice_text_input"
    )
with col_send:
    send_btn = st.button("▶ Envoyer", use_container_width=True, type="primary")

# Chat input classique
chat_prompt = st.chat_input("Posez une question ou collez un lien YouTube...")

# Prompt final
prompt = None
if send_btn and voice_text.strip():
    prompt = voice_text.strip()
elif chat_prompt:
    prompt = chat_prompt


# ============================================================
# TRAITEMENT
# ============================================================

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        full_context = ""
        session_sources = []
        file_result = None
        generated_image_url = None
        df_data = None
        has_file = uploaded_file is not None

        with st.status("🧠 Réflexion...", expanded=True) as status:

            # FICHIER
            if has_file:
                status.write(f"📁 Lecture : *{uploaded_file.name}*")
                uploaded_file.seek(0)
                file_result = lire_fichier(uploaded_file)
                if file_result["success"]:
                    if file_result["type"] == "image":
                        status.write("🖼️ Image — envoi au modèle vision.")
                    else:
                        full_context += f"=== FICHIER : {file_result['name']} ===\n{file_result['data']}\n\n"
                        status.write(f"✅ Lu ({len(file_result['data'])} caractères).")
                        if file_result.get("df") is not None:
                            df_data = file_result["df"]
                else:
                    status.write(f"⚠️ {file_result['data']}")

            # DÉCISION
            decision = decider_outils(prompt, has_file=has_file)
            tools_used = decision.get("tools", [])
            status.write(f"💡 {decision.get('reasoning', '')}")

            # YOUTUBE
            if "youtube" in tools_used:
                url = decision.get("youtube_url") or prompt
                status.write("📺 Transcription YouTube...")
                result = lire_youtube(url)
                if result["success"]:
                    full_context += f"=== YOUTUBE ===\n{result['data']}\n\n"
                    status.write("✅ Transcription récupérée.")
                else:
                    status.write(f"⚠️ {result['data']}")

            # WEB
            if "web_search" in tools_used:
                query = decision.get("web_query") or prompt
                status.write(f"🔍 Recherche : *{query}*")
                result = chercher_web(query)
                if result["success"]:
                    full_context += f"=== WEB ===\n{result['data']}\n\n"
                    session_sources = result.get("sources", [])
                    status.write(f"✅ {len(session_sources)} sources.")
                else:
                    status.write(f"⚠️ {result['data']}")

            # IMAGE
            if "generate_image" in tools_used:
                img_prompt = decision.get("image_prompt") or prompt
                status.write(f"🖼️ Génération : *{img_prompt}*")
                generated_image_url = generer_image(img_prompt)
                status.write("✅ Image générée.")

            status.update(label="🤖 Génération réponse...", state="complete")

        # LLM
        try:
            response_placeholder = st.empty()
            full_response = ""

            if file_result and file_result["type"] == "image" and file_result.get("b64"):
                user_msg = [
                    {"type": "image_url", "image_url": {"url": f"data:{file_result['mime']};base64,{file_result['b64']}"}},
                    {"type": "text", "text": prompt}
                ]
            else:
                text_content = f"{full_context}\n---\nQuestion : {prompt}" if full_context else prompt
                user_msg = text_content

            history = get_trimmed_history(st.session_state.messages[:-1])
            messages_to_send = [{"role": "system", "content": SYSTEM_MAIN}] + history
            messages_to_send.append({"role": "user", "content": user_msg})

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

            # IMAGE GÉNÉRÉE
            if generated_image_url:
                st.image(generated_image_url, caption="🖼️ Générée par SKY", use_container_width=True)

            # GRAPHIQUE
            if df_data is not None:
                with st.expander("📊 Visualisation des données"):
                    afficher_graphique(df_data)

            # SOURCES
            if session_sources:
                with st.expander("📎 Sources"):
                    for s in session_sources:
                        st.markdown(f"""<div class="source-card">
                            <strong>{s.get('title','Source')}</strong><br>
                            <a href="{s.get('url','#')}" target="_blank">{s.get('url','')}</a>
                        </div>""", unsafe_allow_html=True)

            # TTS
            if tts_enabled and full_response.strip():
                lang = detecter_langue(full_response)
                audio_bytes = tts_gtts(full_response, lang=lang)
                if audio_bytes:
                    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                    autoplay_attr = "autoplay" if tts_autoplay else ""
                    st.markdown(f"""
                    <audio {autoplay_attr} controls style="width:100%;margin-top:8px;border-radius:8px;">
                        <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
                    </audio>
                    """, unsafe_allow_html=True)

            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.sources.append(session_sources)

        except Exception as e:
            logger.error(f"Erreur LLM: {e}")
            st.error(f"❌ Erreur Agent : {str(e)}")
