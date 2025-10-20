import streamlit as st
import json 
import requests
from helpers.auth import check_password
from helpers import func
from datetime import datetime
import boto3
from requests_aws4auth import AWS4Auth
import pandas as pd
import plotly.express as px
# if not check_password():
#     st.stop()

aws_access_key, aws_secret_key, aws_region = func.get_aws_credentials()
session     = boto3.Session(aws_access_key_id=aws_access_key,
                            aws_secret_access_key=aws_secret_key,
                            region_name = aws_region)

credentials = session.get_credentials()

auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    aws_region,
    'execute-api',
    session_token=credentials.token
)


def call_api_sous(json_payload,api_url):
    """
    call api function 
    """
    try:
        payload_ini = json.dumps(json_payload)
        # st.write(f"Calling API at {api_url} with payload: {payload_ini[:40]}...")  # Debugging information
        response = requests.post(api_url, data = payload_ini, auth = auth)
        response.raise_for_status()  # Raise an error for bad responses
        # if 'output' in response.json().keys():
            # st.write(f"API Response having following keys: {list(response.json()['output'].keys())[-4:]}...")
        return response.json(), round(response.elapsed.total_seconds(),2)# Assuming the API returns JSON response
    except requests.exceptions.RequestException as e:
        print(f"Error calling the API: {e}")
        return None,None

st.title("📝 KLEMO SOUSCRIPTION")
st.write("Simuler l'évolution de vos gains financiers")

if "base_simul" not in st.session_state:
    st.session_state.base_simul = {}
if 'json_out_sous' not in st.session_state:
    st.session_state.json_out_sous = None

with st.expander("👤 Information", expanded=True):
    col1,col2,col3  = st.columns(3)

    with col1:
        typeProduit = st.selectbox("Produit", ["KLEMO_PER", "KLEMO_VIE"])
        riskProfile = st.selectbox("Profil de risque", ["Secure", "Cautious", "Balanced", "Dynamic","Aggresive"])
    
    with col2:
        VI = st.number_input("Versement Initial", min_value=500, step=100)
        VR = st.number_input("Versement Programmé", min_value=100, step=100)
        
    with col3:
        horizon = st.number_input("Horizon", min_value=15, step=1)
    
    # Save modifications
    if st.button("💾 Enregistrer"):
        st.session_state.base_simul["type"]             = typeProduit
        st.session_state.base_simul["riskProfile"]      = riskProfile
        st.session_state.base_simul["initialAmount"]    = VI
        st.session_state.base_simul["monthlyAmount"]    = VR
        st.session_state.base_simul["horizon"]          = horizon
        
        st.write(st.session_state.base_simul)

        st.success(f"✅ Info Enregistrée")


# --- Step 2: Show editable section ---
with st.expander("🕹 SIMULATION SOUSCRIPTION", expanded=True):

    if st.button("LANCER LA SIMULATION KLEMO"):
        
        json_out, time_elapsed = call_api_sous(st.session_state.base_simul,func.SOUSCRIPTION_URL)
        st.session_state.json_out_sous = json_out["output"]
        # st.session_state.simulation_ready = True
        st.success("✅ Simulation Bilan exécutée avec succès !")


        st.subheader(f"Evolution de votre actif sur {horizon} ans: ")

        df_evol = pd.DataFrame(st.session_state.json_out_sous["evolution"]).head(horizon)
        # st.write(df_evol)
        df_evol_graphe = df_evol.copy().rename(
            columns={
                "ValuePct5": "Scénario défavorable",
                "ValuePct50": "Scénario médian",
                "ValuePct95": "Scénario favorable"
            }
        )
        fig = px.line(df_evol_graphe, x='horizon', y=["Scénario favorable","Scénario médian", "Scénario défavorable"],
            title="Vos 3 scénarios d'évolution de votre actif dans les années à venir",
            labels={'value': 'Montant (€)', 'variable': 'Scénarios'},
            color_discrete_map={
                'Scénario défavorable': '#2E8B57',
                'Scénario médian': '#87CEEB', 
                'Scénario favorable': '#FFD700'
            })
        # --- Style each line separately ---
        fig.update_traces(selector=dict(name='Scénario défavorable'), line=dict(width=3, dash='dot'))
        fig.update_traces(selector=dict(name='Scénario median'), line=dict(width=6, dash='solid'))
        fig.update_traces(selector=dict(name='Scénario favorable'), line=dict(width=3, dash='dot'))


        # --- Layout ---
        fig.update_layout(
            title={
                'text': "Vos 3 scénarios d'évolution de votre patrimoine dans les années à venir",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            xaxis_title='Date',
            yaxis_title='Montant (€)',
            legend_title='Scénario',
            hovermode='x unified',
            template='plotly_white'
        )

        st.plotly_chart(fig, use_container_width=True)

        # st.write(st.session_state.json_out_sous.keys())
        alloc = st.session_state.json_out_sous["allocation"]
        fig = px.pie(
            names=list(alloc.keys()),
            values=list(alloc.values()),
            title="Répartition Côté / Non Côté",
            color_discrete_sequence=['#2ca02c', '#d62728']
        )
        fig.update_traces(textinfo='label+percent', pull=[0, 0.05])
        # fig.show()

        st.plotly_chart(fig, use_container_width=True)
