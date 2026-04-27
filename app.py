import streamlit as st
from groq import Groq
import os
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="SkyElite AI", page_icon="🚀", layout="centered")

# Récupération de la clé API
API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=API_KEY)

# Initialisation de l'historique (style Messenger)
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- INTERFACE ---
st.title("💬 SkyElite Messenger")
st.caption("Propulsé par Llama 3.3 & Streamlit Cloud")

# Barre latérale pour les fonctionnalités bonus
with st.sidebar:
    st.header("⚙️ Options")
    uploaded_file = st.file_uploader("📎 Analyser un fichier (CSV/TXT)", type=["csv", "txt"])
    if uploaded_file is not None:
        st.success("Fichier chargé avec succès !")
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
            st.write("Aperçu des données :", df.head())
    
    if st.button("🧹 Effacer la discussion"):
        st.session_state.messages = []
        st.rerun()

# Affichage des messages de l'historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie (Chat Input style Messenger)
if prompt := st.chat_input("Écrivez votre message ici..."):
    # 1. Afficher le message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Réponse de l'IA SkyElite
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # On envoie tout l'historique pour que l'IA se souvienne du contexte
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=False
            )
            full_response = completion.choices[0].message.content
            message_placeholder.markdown(full_response)
        except Exception as e:
            full_response = f"❌ Erreur : {str(e)}"
            st.error(full_response)
            
    st.session_state.messages.append({"role": "assistant", "content": full_response})
            style={'flex': '4', 'padding': '15px', 'borderRadius': '8px', 'border': 'none', 'backgroundColor': '#222', 'color': 'white'}
        ),
        html.Button('ENVOYER', id='send-btn', n_clicks=0, style={
            'flex': '1', 'backgroundColor': '#00ffcc', 'border': 'none', 'borderRadius': '8px', 'fontWeight': 'bold', 'cursor': 'pointer'
        })
    ]),

    dcc.Loading(id="loading-1", type="circle", children=html.Div(id="loading-output")),
    dcc.Store(id='chat-store', data=[]) 
])

# --- LOGIQUE ---
@app.callback(
    [Output('chat-display', 'children'), 
     Output('user-input', 'value'), 
     Output('chat-store', 'data'),
     Output('loading-output', 'children')],
    [Input('send-btn', 'n_clicks')],
    [State('user-input', 'value'), 
     State('chat-store', 'data')],
    prevent_initial_call=True
)
def handle_chat(n_clicks, text, history):
    if not text:
        return no_update, "", no_update, ""

    # Message utilisateur
    history.append(html.Div([
        html.B("👤 Vous: ", style={'color': '#00ffcc'}),
        html.Span(text)
    ], style={'marginBottom': '15px'}))

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": text}],
            temperature=0.2,
            max_tokens=1000
        )
        rep_text = completion.choices[0].message.content
        
        # Réponse Assistant
        history.append(html.Div([
            html.B("🤖 SkyElite: ", style={'color': '#ff007f'}),
            html.Span(rep_text)
        ], style={'marginBottom': '25px', 'padding': '10px', 'backgroundColor': '#1a1a1a', 'borderRadius': '5px'}))
        
    except Exception as e:
        history.append(html.Div(f"❌ Erreur API: Vérifiez votre clé Groq", style={'color': 'red'}))

    return history, "", history, ""

if __name__ == '__main__':
    app.run(debug=False)
