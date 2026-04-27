import streamlit as st
from groq import Groq
import os

# 1. Configuration de la page
st.set_page_config(page_title="SkyElite AI", page_icon="🚀")

# 2. Récupération de la clé API
API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=API_KEY)

# 3. Initialisation de l'historique
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. Interface
st.title("💬 SkyElite Messenger")

# Affichage des messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie
if prompt := st.chat_input("Écrivez votre message..."):
    # Afficher le message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Réponse de l'IA
    with st.chat_message("assistant"):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            )
            response = completion.choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Erreur : {e}")
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
