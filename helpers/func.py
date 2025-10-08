import streamlit as st
import os 
import requests
import json
import boto3
from requests_aws4auth import AWS4Auth
import pandas as pd 
import plotly.express as px
import time


def get_aws_credentials():
    """
    Get AWS credentials from either Vercel environment variables (production)
    or Streamlit secrets (local development)
    """
    # Try to get from Vercel environment variables first
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'eu-west-1')
    
    # If not found in environment variables, try Streamlit secrets (for local development)
    if not aws_access_key or not aws_secret_key:
        try:
            aws_access_key = st.secrets["AWS"]["ACCESS_KEY"]
            aws_secret_key = st.secrets["AWS"]["SECRET_KEY"]
            aws_region = st.secrets["AWS"].get("REGION", "eu-west-1")
            # st.info("📝 Using credentials from Streamlit secrets (local development)")
        except (KeyError, AttributeError):
            # secrets not available either
            aws_access_key = None
            aws_secret_key = None
            st.warning("🔐 No AWS credentials found in environment variables or secrets")
    else:
        st.info("☁️ Using credentials from environment variables (Vercel production)")
    
    return aws_access_key, aws_secret_key, aws_region


def call_api(json_payload,api_url):
    """
    call api function 
    """
    try:
        payload_ini = json.dumps({"data_ctxt":json_payload})
        # st.write(f"Calling API at {api_url} with payload: {payload_ini[:40]}...")  # Debugging information
        response = requests.post(api_url, data = payload_ini, auth = auth)
        response.raise_for_status()  # Raise an error for bad responses
        # if 'output' in response.json().keys():
        #     st.write(f"API Response having following keys: {list(response.json()['output'].keys())[-4:]}...")
        return response.json(), round(response.elapsed.total_seconds(),2)# Assuming the API returns JSON response
    except requests.exceptions.RequestException as e:
        print(f"Error calling the API: {e}")
        return None,None

# polling result 
def poll_result(api_url, request_id):
    while True:
        response = requests.get(f"{api_url}/strat_result/{request_id}",auth = auth)
        if response.status_code == 200:
            print("Result:", response.json()['output'])
            return response
            break
        elif response.status_code == 202:
            print("Processing... retrying in 5 seconds")
            time.sleep(5)
        else:
            print("Error:", response.text)
            break


def load_base_info(name_json):
    with open(f"json/{name_json}.json", "r") as f:
        return json.load(f)


aws_access_key, aws_secret_key, aws_region = get_aws_credentials()
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

##### test nom du domaine ####
FILL_SCORE_URL   = "https://algo.yde.core.techklemo.com/v1/fill-score"
PROJ_URL         = "https://algo.yde.core.techklemo.com/v1/proj"
STRAT_URL        = "https://algo.yde.core.techklemo.com/v1"
STRAT_INIT_URL   = f"{STRAT_URL}/strat_init"

OBJECTIF_CHOICES = {
    "investir" : ["regulier", "rp", "rl", "optimiser"],
    "projet"   : ["projet","immo"],
    "completer": ["revenus_supplementaires","optimiser"],
    "impots"  : ["reduction_impots","fiscalite_revenus"]
}


def display_bilan_synth(json_synth):

    pat_synth = json_synth["output"]["patSynth"]
    # --- Buttons to switch views ---
    col1, col2, col3 = st.columns(3)
    with col1:
        show1 = st.button("📊 Répartition")
    with col2:
        show2 = st.button("📈 Revenus et Charges")
    with col3:
        show4 = st.button("⚖️ Impôts")

    # --- Track which one is active in session_state ---
    if "current_graph" not in st.session_state:
        st.session_state.current_graph = 1

    if show1:
        st.session_state.current_graph = 1
    elif show2:
        st.session_state.current_graph = 2
    # elif show3:
    #     st.session_state.current_graph = 3
    # elif show4:
    #     st.session_state.current_graph = 4

    # --- Single display area ---

    if st.session_state.current_graph == 1:
        asset_data = {
            "Category": ["Financier", "Immobilier", "Professionnel", "Emprunts"],
            "Value": [pat_synth["patFin"], pat_synth["patImmo"], pat_synth["patPro"], pat_synth["patEmprunt"]],
            "Color": ["#4E79A7", "#F28E2B", "#E15759", "#59A14F"]  # Professional color palette
        }

        df = pd.DataFrame(asset_data)

        # Calculate percentages
        df['Percentage'] = (df['Value'].abs() / pat_synth["patBrut"]) * 100
        df['Label'] = df.apply(lambda x: f"{x['Category']}<br>{x['Value']:,.0f}€ ({x['Percentage']:.1f}%)", axis=1)

        # Create donut chart
        fig = px.pie(df,
                    values='Value',
                    names='Label',
                    color='Category',
                    color_discrete_map=dict(zip(df['Category'], df['Color'])),
                    hole=0.4,  # Creates the donut hole
                    title="<b>Projection de votre patrimoine brut</b><br><sup>Répartition par catégorie</sup>")

        # Customize layout
        fig.update_layout(
            margin=dict(t=100, b=30),  # Adjust top/bottom margins
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            annotations=[dict(
                text=f"Total brut<br>{pat_synth['patBrut']:,.0f}€",
                x=0.5, y=0.5,
                font_size=16,
                showarrow=False
            )]
        )

        # Style the traces
        fig.update_traces(
            textposition='inside',
            textinfo='percent',
            insidetextorientation='radial',
            marker=dict(line=dict(color='white', width=1))
        )

        # Display in Streamlit
        st.plotly_chart(fig, use_container_width=True)

        valueComment=f"Valeur nette des biens: {pat_synth['patNet']}€"
        st.write("")
        st.write("")
        st.markdown(
            f"""
            <div style="
                background-color: #e6f9ea;   /* very light green */
                color: #0b7a3f;              /* dark green text */
                padding: 12px 16px;
                border-radius: 8px;
                border: 1px solid #c7eed0;
                font-weight: 500;
                ">
            {valueComment}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("Estimation future de la valeur de vos investissements:")
        df_assetSynth = pd.DataFrame(json_synth["output"]["assetSynth"]).copy()
        df_assetSynth_graphe = df_assetSynth.copy().rename(
            columns={
                "TotalPct5": "Scénario favorable",
                "TotalPct50": "Scénario médian",
                "TotalPct95": "Scénario défavorable"
            }
        )
        fig = px.line(df_assetSynth_graphe, x='dates', y=["Scénario favorable","Scénario médian", "Scénario défavorable"],
            title="Vos 3 scénarios d'évolution de votre patrimoine dans les années à venir",
            labels={'value': 'Montant (€)', 'variable': 'Scénarios'},
            color_discrete_map={
                'Scénario favorable': '#2E8B57',
                'Scénario médian': '#87CEEB', 
                'Scénario défavorable': '#FFD700'
            })
        # --- Style each line separately ---
        fig.update_traces(selector=dict(name='Scénario favorable'), line=dict(width=3, dash='dot'))
        fig.update_traces(selector=dict(name='Scénario median'), line=dict(width=6, dash='solid'))
        fig.update_traces(selector=dict(name='Scénario défavorable'), line=dict(width=3, dash='dot'))


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

        st.write("Aperçu de la synthèse des biens actifs et passifs")
        st.dataframe(df_assetSynth[["dates","FinPct5","FinPct50","FinPct95","ImmoPct5","ImmoPct50","ImmoPct95","ScpiPct5","ScpiPct50","ScpiPct95","EmpruntPct5","EmpruntPct50","EmpruntPct95","ProPct5","ProPct50","ProPct95", "TresoPct5","TresoPct50","TresoPct95","TotalPct5","TotalPct50","TotalPct95"]].head(11))

        st.write("Aperçu de la synthèse du cashflow")
        st.dataframe(pd.DataFrame(json_synth["output"]["cashflowSynth"])[["dates","RevenusActivite","RetraiteRentePension","RetraitDivActifFinancier",	"RevenusImmobilier",	"DepensesCourantes",	"Emprunt", "RevenusScpiNet","RevenusProNet","ImpotsBareme","ImpotsAutres"	]].head(11))


    elif st.session_state.current_graph == 2:

        st.write("Evolution de vos revenus et charges: ")
        df_rev = pd.DataFrame(json_synth["output"]["cashflowCourantReel"])
        df_rev_graphe = df_rev.copy().rename(
            columns={
                "RevenusActiviteReel": "Revenus",
                "DepensesActiviteReel": "Charges"
            }
        )

        fig = px.line(df_rev_graphe, x='dates', y=["Revenus", "Charges"],
            # title="Revenus et charges ajustés de l'inflation au fil des années",
            labels={'value': 'Montant (€)', 'variable': 'Scénarios'},
            color_discrete_map={
                'Revenus': '#2E8B57',
                'Charges': '#FFD700'
            })
        # --- Style each line separately ---
        fig.update_traces(selector=dict(name='Revenus'), line=dict(width=6, dash='solid'))
        fig.update_traces(selector=dict(name='Charges'), line=dict(width=6, dash='solid'))

        # --- Layout ---
        fig.update_layout(
            title={
                'text': "Revenus et charges ajustés de l'inflation au fil des années",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            xaxis_title='Date',
            yaxis_title='Montant (€)',
            hovermode='x unified',
            template='plotly_white'
        )

        st.plotly_chart(fig, use_container_width=True)
        
        st.write("Aperçu de l'évolution des revenus et des charges")
        st.dataframe(df_rev_graphe)
    #     fig = px.scatter(df, x="gdpPercap", y="lifeExp", color="continent", title="Graph 2: GDP vs Life Expectancy")
    # elif st.session_state.current_graph == 3:
    #     fig = px.pie(df, names="continent", values="pop", title="Graph 3: Population Share")
    # else:
    #     fig = px.line(df, x="gdpPercap", y="lifeExp", color="continent", title="Graph 4: Trend Example")







def display_strat_output(payload_strat, strat_output,debut=0):
    with st.container():
        st.markdown("**ℹ️ Détails de l'Objectif Client**")
        cols = st.columns(2)
        cols[0].metric("Objectif Principal", payload_strat.get('objectif', 'N/A'))
        cols[1].metric("Sous-Objectif", payload_strat.get('sousObjectif', 'N/A'))

    # Display all available recommendations
    st.subheader("✨ Recommendations disponibles")
    if not strat_output:
        st.warning("Pas de recommendations valides.")
        return
    
    # Create tabs for each recommendation
    tabs = st.tabs([f"Reco {i+1}" for i in range(len(strat_output))])
    
    for idx, content_strat in enumerate(strat_output):
        with tabs[idx]:
            # Recommendation card
            with st.container():
                st.markdown(f"""
                <div style='
                    padding: 1rem;
                    border-radius: 0.5rem;
                    background: #f8f9fa;
                    margin-bottom: 1rem;
                '>
                    <h3 style='color: #2e86c1; margin-top: 0;'>{content_strat["texteStrat"]["titre"]}</h3>
                    <p>{content_strat["texteStrat"]["description"]}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Metrics display
                cols = st.columns(2)
                cols[0].metric(
                    label=content_strat["attribut"]["metrique1"]["description"],
                    value=f"{content_strat['attribut']['metrique1']['value']} €",
                    delta=None
                )
                
                if "metrique2" in content_strat["attribut"]:
                    cols[1].metric(
                        label=content_strat["attribut"]["metrique2"]["description"],
                        value=f"{content_strat['attribut']['metrique2']['value']} €",
                        delta=None
                    )

    # Best recommendation section
    if strat_output:
        best_element = next(strat_ele for strat_ele in strat_output if strat_ele["attribut"]["prioGlobal"] == 0)
        bestIndex    = best_element["attribut"]["bestVarIndex"]
        st.subheader("🏆 Meilleure Recommendation")
        with st.container():
            st.markdown(f"### {best_element['variantesResult'][0]['metriques']['libVariante']}")
            st.markdown(f"**Pourquoi cette recommendation?** {best_element['texteStrat']['description']}")
            
            metric_cols = st.columns(2)
            with metric_cols[0]:
                st.markdown("**Metrique Principale**")
                st.markdown(f"<h2 style='text-align: center;'>{best_element['attribut']['metrique1']['value']} €</h2>", unsafe_allow_html=True)
                st.markdown(best_element['attribut']['metrique1']['description'])
            
            with metric_cols[1]:
                st.markdown("**Metrique Secondaire**")
                st.markdown(f"<h2 style='text-align: center;'>{best_element['attribut']['metrique2']['value']} €</h2>", unsafe_allow_html=True)
                st.markdown(best_element['attribut']['metrique2']['description'])
        
        st.write(f"preview de la metrique 1: {best_element['attribut']['metrique1']['name']}")
        if "pct5" in pd.DataFrame(best_element["variantesResult"][bestIndex]["metriques"][best_element["attribut"]['metrique1']['name']]).columns:
            st.dataframe(pd.DataFrame(best_element["variantesResult"][bestIndex]["metriques"][best_element["attribut"]['metrique1']['name']])[["index","horizon","pct5","pct50","pct95"]].iloc[debut:debut+20])
        else:
            st.dataframe(pd.DataFrame(best_element["variantesResult"][bestIndex]["metriques"][best_element["attribut"]['metrique1']['name']])[["dates","horizon","pct50"]].iloc[debut:debut+20])
                
        # st.write(f"preview de la metrique 2: {best_element['attribut']['metrique2']['name']}")
        # st.dataframe(pd.DataFrame(best_element["variantesResult"][bestIndex]["metriques"][best_element["attribut"]['metrique2']['name']])[["index","horizon","pct5","pct50","pct95"]].head(10))
        
        lastCost = best_element["variantesResult"][bestIndex]["metriques"]["difCout"][-1]
        st.write(f"Coût et frais: A l'horizon de {lastCost['horizon']} ans, l'ensemble des coûts et de frais associés s'élève à  {lastCost['CoutsFraisTotal']} € (soit {round(lastCost['PctCoutsFraisTotal']*100,0)}%)")