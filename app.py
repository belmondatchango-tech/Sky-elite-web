import os
import platform
import sys
from dash import Dash, html, dcc, Input, Output, State, no_update
from groq import Groq

# --- CONFIGURATION SÉCURISÉE ---
# Render va lire la clé directement dans ses paramètres secrets
API_KEY = os.environ.get("GROQ_API_KEY") 
client = Groq(api_key=API_KEY)

app = Dash(__name__, title="SkyElite V4.1")
server = app.server  # Ligne INDISPENSABLE pour Render

# --- INTERFACE ---
app.layout = html.Div(style={'backgroundColor': '#0a0a0a', 'color': '#e0e0e0', 'padding': '15px', 'height': '100vh', 'fontFamily': 'sans-serif'}, children=[
    html.H2("🚀 SKY ELITE ONLINE", style={'color': '#00ffcc', 'textAlign': 'center', 'marginBottom': '10px'}),
    
    # Zone de Chat
    html.Div(id='chat-display', style={
        'height': '65vh', 
        'overflowY': 'scroll', 
        'border': '1px solid #333', 
        'padding': '10px', 
        'borderRadius': '10px',
        'backgroundColor': '#111',
        'marginBottom': '10px',
        'whiteSpace': 'pre-wrap'
    }),

    # Zone de saisie
    html.Div(style={'display': 'flex', 'gap': '10px'}, children=[
        dcc.Input(
            id='user-input',
            type='text',
            placeholder='Posez une question à SkyElite...',
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
