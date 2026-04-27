import streamlit as st
from groq import Groq
import os
import platform
import sys

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="SKY ELITE v4.1", page_icon="🛡️", layout="wide")

# Initialisation Groq
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- IDENTITÉ ET CAPACITÉS (System Prompt) ---
SYSTEM_PROMPT = """Tu es SKY ELITE v4.1, un bot multi-tâche PRO. 
Tes capacités incluent :
- 📊 Analyse système (OS, RAM, CPU)
- 💻 exécution de code Python/Shell sécurisé
- 🌐 Scan réseau et APIs
- 🔍 Recherche web et scraping
- 🛡️ Gestion de fichiers et dossiers
Réponds toujours de manière professionnelle, précise et propose du code si nécessaire."""

# --- LOGIQUE DE L'HISTORIQUE ---
if "messages" not in st.session_state:
    # On commence avec le prompt système (caché pour l'utilisateur)
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# --- INTERFACE (SIDEBAR) ---
with st.sidebar:
    st.title("🛠️ PANNEAU DE CONTRÔLE")
    st.info(f"**OS**: {platform.system()} {platform.release()}\n\n**Python**: {sys.version.split()[0]}")
    
    st.divider()
    uploaded_file = st.file_uploader("📎 JOINDRE UN FICHIER (Analyse)", type=['csv', 'txt', 'pdf', 'py'])
    
    if st.button("🧹 NETTOYER L'HISTORIQUE"):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.rerun()

# --- AFFICHAGE DU CHAT ---
st.title("🚀 SKY ELITE v4.1")
st.caption("Interface Web Professionnelle - Mode Cloud Actif")

# On affiche les messages (en sautant le premier qui est le système)
for m in st.session_state.messages:
    if m["role"] != "system":
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

# --- ZONE DE SAISIE ---
if prompt := st.chat_input("Entrez une commande ou une question..."):
    # Ajout du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Réponse de SKY ELITE
    with st.chat_message("assistant"):
        try:
            # Préparation du contexte avec fichier si présent
            file_info = f"\n[INFO: L'utilisateur a joint le fichier : {uploaded_file.name}]" if uploaded_file else ""
            
            # Appel API
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=st.session_state.messages, # Envoie tout l'historique + prompt système
                temperature=0.3
            )
            
            response = completion.choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            st.error(f"❌ Erreur de connexion au noyau SkyElite : {e}")

# --- PIED DE PAGE ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>SKY ELITE v4.1 PRO - Sécurisé par Chiffrement Cloud</p>", unsafe_allow_html=True)
