import streamlit as st
import plotly.express as px
import pandas as pd
import requests
import json
import boto3
from requests_aws4auth import AWS4Auth
import time
from datetime import datetime
from helpers.jsonGen import situation_dict,montants_fin,montants_immo,montants_emprunt,montants_pro,ENUM_OPTIONS
from helpers.simul_contraint_main_sous_cat_v2 import simul_obj_client_from_dicts,import_json,impute_json


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
            st.info("📝 Using credentials from Streamlit secrets (local development)")
        except (KeyError, AttributeError):
            # secrets not available either
            aws_access_key = None
            aws_secret_key = None
            st.warning("🔐 No AWS credentials found in environment variables or secrets")
    else:
        st.info("☁️ Using credentials from environment variables (Vercel production)")
    
    return aws_access_key, aws_secret_key, aws_region

aws_access_key, aws_secret_key, aws_region = get_aws_credentials()
session     = boto3.Session(aws_access_key_id=aws_access_key,
                            aws_secret_access_key=aws_secret_key,
                            region_name = region_name)
credentials = session.get_credentials()

auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region_name,
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

def render_dict_inputs(name, data):
    updated = {}
    st.subheader(name)
    for key, val in data.items():
        if isinstance(val, dict):
            updated[key] = render_dict_inputs(key, val)
        
        elif key in ENUM_OPTIONS: 
            updated[key] = st.selectbox(
                f"{name} - {key}",
                options=ENUM_OPTIONS[key],
                index=ENUM_OPTIONS[key].index(val) if val in ENUM_OPTIONS[key] else 0,
                key=f"{name}_{key}"
            )
        elif isinstance(val, list) and len(val) == 1 and isinstance(val[0], (int, float)):
            updated[key] = [st.number_input(f"{name} - {key}", value=val[0], step=100)]

        elif isinstance(val, bool):
            updated[key] = st.radio(
                f"{name} - {key}", options=[True, False], index=0 if val else 1,
                horizontal=True,
                key=f"{name}_{key}"
            )
        elif isinstance(val, (int, float)):
            updated[key] = st.number_input(f"{name} - {key}", value=val, step=100)
        elif isinstance(val, str):
            updated[key] = st.text_input(f"{name} - {key}", value=val)


        else:
            updated[key] = val
    return updated

def display_customer_info(client_data):
    client = client_data["Client"]["PatClientDetail"][0]
    civilite = "M." if client["civilite"] == "M" else "Mme"
    age = datetime.now().year - datetime.strptime(client["dateNaissance"], "%Y-%m-%d").year
    
    # Safely get values with defaults
    type_union          = client.get('typeUnion', 'Non renseigné')
    regime_matrimonial  = client.get('regimeMatrimonial', 'Non renseigné')
    nbEnfants           = client.get('nbEnfants') or 0
    statut_conjoint     = client.get('statutProConjoint', 'Non renseigné')
    # ppe                 = 'Oui'if client.get('ppe') else 'Non' 
    
    cashflow            = client_data["Cashflow"]["PatCashflowDetail"][0]
    revenus             = cashflow.get('revenusActivite', 0) or 0
    depenses            = cashflow.get('depensesCourantes',0) or 0
    

    with st.container():
        # Header section
        st.caption(f"{age} ans • {civilite} *** • {type_union}")
        
        # Create columns for the grid layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Situation Familiale:** {type_union}")
            st.markdown(f"**Régime Matrimonial:** {regime_matrimonial}")
        
        with col2:
            st.markdown(f"**Statut Pro Conjoint:** {statut_conjoint}")
            st.markdown(f"**Nombre d'enfant:** {nbEnfants}")

        
        # Financial section
        st.subheader("Situation financière")
        
        col3, col4 = st.columns(2)
        with col3:
            st.markdown(f"**Revenus d'activité /an:** {revenus}€")
        with col4:
            st.markdown(f"**Dépenses courantes /an:** {depenses*12}€")
        # with col5:
        #     st.markdown(f"**PPE:** {ppe}")
        
        # Add some styling
        st.markdown("""
        <style>
            div[data-testid="column"] {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                margin: 5px;
            }
        </style>
        """, unsafe_allow_html=True)

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

def main():
    # Streamlit UI
    # Title and description
    global situation_dict,montants_fin,montants_immo,montants_emprunt,montants_pro,ENUM_OPTIONS
    st.title("👋🏻 Démo - API Algo Klemo")

    if 'json_proj' not in st.session_state:
        st.session_state.json_proj = None
    if 'json_synth_id' not in st.session_state:
        st.session_state.json_synth_id = None

    with st.expander("😇 PART 0.1 : Create Personnae", expanded=True):
        st.sidebar.header("Navigation")
        section = st.sidebar.radio("Choose Section", ["Situation", "Montants Financiers", "Immobilier", "Emprunts", "Pro"])

        if section == "Situation":
            situation_dict = render_dict_inputs("Situation", situation_dict)
        elif section == "Montants Financiers":
            montants_fin = render_dict_inputs("Montants Financiers", montants_fin)
        elif section == "Immobilier":
            montants_immo = render_dict_inputs("Immobilier", montants_immo)
        elif section == "Emprunts":
            montants_emprunt = render_dict_inputs("Emprunts", montants_emprunt)
        elif section == "Pro":
            montants_pro = render_dict_inputs("Pro", montants_pro)

        p1=simul_obj_client_from_dicts(situation_dict, montants_fin, montants_immo, montants_pro, montants_emprunt)
        input_json = import_json("json/vide_new.json")
        impute_json(input_json,p1)

        if st.button("Generate JSON"):
            
            st.json(input_json)
            st.download_button("Download JSON", json.dumps(input_json, indent=2), file_name="client_situation.json", mime="application/json")
        
    with st.expander("📁 PART 1 : API FillScore", expanded=True):
        # uploaded_file = st.file_uploader("Choisir un fichier JSON", type="json")
        
        # if uploaded_file is not None:
            # Read the JSON file
            # file_contents = uploaded_file.read()
            # json_data = json.loads(file_contents)
            # display_customer_info(json_data)

            # Display the JSON data in a text area
        st.text_area("Charged Payload FastPat", json.dumps(input_json, indent=2), height=300, key="fastpat_content")

        # Button to send the request
        if st.button("Envoyer une requête à l'API FillScore"):
            if input_json: 
                try:
                    # Call the API with the parsed JSON
                    json_proj, time_elapsed = call_api(input_json,FILL_SCORE_URL)
                    st.session_state.json_proj = json_proj["output"]
                    
                    if json_proj:
                        st.subheader(f"Temps de réponse FillScore: {time_elapsed} secondes")
                        score_quality = json_proj["output"].get("ScoreQuality", {})

                        if score_quality: 
                            df = pd.DataFrame({
                                'Metriques': list(score_quality.keys()),
                                'Scores': list(score_quality.values())
                            })
                            # Create the plot
                            fig = px.bar(df,
                                        x='Scores',
                                        y='Metriques',
                                        orientation='h',
                                        text='Scores',
                                        color='Metriques',  # Different color for each metric
                                        color_discrete_sequence=px.colors.qualitative.Plotly,
                                        range_x=[0, 100],  # Fixed scale to 100
                                        title='Score de qualité de remplissage')
                            
                            # Customize the layout
                            fig.update_layout(
                                height=500,
                                showlegend=False,
                                xaxis_title='Score (sur 100)',
                                yaxis_title='Metriques',
                                hovermode='y unified'
                            )
                            
                            # Format the text on bars
                            fig.update_traces(texttemplate='%{x:.1f}', 
                                            textposition='outside',
                                            marker_line_color='rgb(8,48,107)',
                                            marker_line_width=1.5)
                            
                            # Display in Streamlit
                            st.plotly_chart(fig, use_container_width=True)

                        st.write(f"Score Total des Infos Patrimoniales :{score_quality.get('Total', 0)}")

                        # Display the JSON response in a readable format
                    else:
                        st.error("Failed to get a valid response from the API.")
                except json.JSONDecodeError:
                    st.error("Invalid JSON format in the input.")
            else:
                st.error("Please enter a JSON payload.")

    with st.expander("📈 PART 2 : API Synthèse Patrimoniale (BilanPat)", expanded=True):
    # Display the full API response in another text area
        if st.session_state.json_proj: 
            # Text area for the next API call
            st.subheader("API de Projection d'un bilan patrimonial")
            # st.text_area("Payload for API Bilan Pat", json.dumps(json_proj, indent=2), height=300, key="bilanpat_content")
            st.text_area(":black_nib: Entrer Infos:", value=json.dumps(st.session_state.json_proj, indent=2),height = 200, key = "bilanpat_content")
            # json_proj = json.loads(json_proj)
            if st.button("Envoyer une Requête à l'API BilanPat (Projection)"):
                if st.session_state.json_proj: 
                    try:
                        # Call the API with the parsed JSON
                        json_synth, time_elapsed = call_api(st.session_state.json_proj,PROJ_URL)
                        
                        if json_synth:
                            st.session_state.json_synth_id = json_synth["requestId"]
                            st.session_state.json_synth_key = json_synth["requestKey"]
                        
                            st.subheader(f"Temps de réponse BilanPat: {time_elapsed} secondes")
                            st.write(f"Résultats json enregistrés dans un bucket s3 avec suffix:{json_synth['requestKey']}")

                            pat_synth = json_synth["output"]["patSynth"]
                            if pat_synth:
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
                                st.write("Preview asset synthese:")
                                st.dataframe(pd.DataFrame(json_synth["output"]["assetSynth"])[["dates","FinPct50","ImmoPct50","ScpiPct50","EmpruntPct50","ProPct50", "TresoPct50","TotalPct50"]].head(11))

                                st.write("Preview cashflow synthese:")
                                st.dataframe(pd.DataFrame(json_synth["output"]["cashflowSynth"])[["dates","RevenusActivite","RetraiteRentePension","RetraitDivActifFinancier",	"RevenusImmobilier",	"DepensesCourantes",	"Emprunt", "RevenusScpiNet","RevenusProNet","ImpotsBareme","ImpotsAutres"	]].head(11))

                    

                            # Display the JSON response in a readable format
                        else:
                            st.error("Failed to get a valid response from the API.")
                    except json.JSONDecodeError:
                        st.error("Invalid JSON format in the input.")
                else:
                    st.error("Please enter a JSON payload.")

    with st.expander("💡 PART 3 : API Recommandations (StratPat)", expanded=True):
    # Display the full API response in another text area
        if st.session_state.json_synth_id: 
            # Text area for the next API call
            st.subheader("API Recommandations: générer des données d'entrées")
            # st.text_area("Payload for API Bilan Pat", json.dumps(json_proj, indent=2), height=300, key="bilanpat_content")
            # st.text_area(":black_nib: Enter Json:", value=json.dumps(st.session_state.json_proj, indent=2),height = 200, key = "bilanpat_content")
            # payload_strat_txt = st.text_area(":black_nib: Enter JSON payload of Strat Pat:", height=200)
            
            col1, col2 = st.columns(2)
    
            with col1:
                # Objective selection
                selected_objectif = st.selectbox(
                    "Choisir un Objectif",
                    options=list(OBJECTIF_CHOICES.keys()),
                    key="objectif_select"
                )
            
            with col2:
                # Sub-objective selection (dynamic based on objective)
                selected_sous_objectif = st.selectbox(
                    "Choisir un Sous-Objective",
                    options=OBJECTIF_CHOICES[selected_objectif],
                    key="sous_objectif_select"
                )
            
            paramObj = st.text_area(":black_nib: entrer des paramètres d'objectif (optionnel):",value="{}", height=200)
          
            if st.button("Générer un Payload pour l'API StratPat et puis lui envoyer la requête"):
                # Build the payload
                st.session_state.payload_strat = {
                    "requestId": st.session_state.json_synth_id, 
                    "requestKey": st.session_state.json_synth_key,
                    "objectif": selected_objectif,
                    "sousObjectif": selected_sous_objectif,
                    "paramObjectif": json.loads(paramObj),
                    "investorProfile":{"level":"Balanced","esg":"Neutral"}
                }

            # json_proj = json.loads(json_proj)
            # if st.button("Send Request to our API StratPat"):
                if st.session_state.json_synth_id: 
                    try:
                        # Call the API with the parsed JSON
                        init_strat, time_elapsed = call_api(st.session_state.payload_strat,STRAT_INIT_URL)
                
                        if init_strat:
                            request_id     = st.session_state.payload_strat.get("requestId")
                            strat_result = poll_result(STRAT_URL,request_id)
                            print("debugging: strat_result",strat_result)
                            strat_output = strat_result.json()["output"]
                            
                            with st.container():
                                st.markdown("**ℹ️ Détails de l'Objectif Client**")
                                cols = st.columns(2)
                                cols[0].metric("Objectif Principal", st.session_state.payload_strat.get('objectif', 'N/A'))
                                cols[1].metric("Sous-Objectif", st.session_state.payload_strat.get('sousObjectif', 'N/A'))

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
                                st.dataframe(pd.DataFrame(best_element["variantesResult"][bestIndex]["metriques"][best_element["attribut"]['metrique1']['name']])[["index","horizon","pct5","pct50","pct95"]].head(10))
                                
                                st.write(f"preview de la metrique 2: {best_element['attribut']['metrique2']['name']}")
                                st.dataframe(pd.DataFrame(best_element["variantesResult"][bestIndex]["metriques"][best_element["attribut"]['metrique2']['name']])[["index","horizon","pct5","pct50","pct95"]].head(10))
                                
                                lastCost = best_element["variantesResult"][bestIndex]["metriques"]["difCout"][-1]
                                st.write(f"Coût et frais: A l'horizon de {lastCost['horizon']} ans, l'ensemble des coûts et de frais associés s'élève à  {lastCost['CoutsFraisTotal']} € (soit {round(lastCost['PctCoutsFraisTotal']*100,0)}%)")
                            # best_key, best_element = max(strat_output_cleaned.items(),key=lambda x: x[1]["attribut"]["metrique1"]["value"])

                            # st.write(f'Title of reco: {best_element["variantesResult"][0]["metriques"]["libVariante"]}')
                            # st.write(f'Main metric: {best_element["attribut"]["metrique1"]["description"]}')
                            # st.write(f'Secondary metric {best_element["attribut"]["metrique2"]["description"]}')
                            

                            # Display the JSON response in a readable format
                        else:
                            st.error("Failed to get a valid response from the API.")
                    except json.JSONDecodeError:
                        st.error("Invalid JSON format in the input.")
                else:
                    st.error("Please enter a JSON payload.")

        # # Button to call the next API
        # if st.button("Call Next API"):
        #     # Here you can add the code to call the next API with the payload from the text area
        #     st.write("Next API button clicking")  # Debugging information
        #     proj_api_response, next_time_elapsed = call_api(json.loads(json_proj), PROJ_URL)

        #     if proj_api_response:
        #         st.subheader(f"BilanPat API Response after {next_time_elapsed} seconds")
        #         st.text_area("BilanPat API Response", json.dumps(proj_api_response, indent=2), height=300, key="bilanpat_api_response")

        #     else:
        #         st.error("Failed to get a valid response from the API.")

if __name__ == "__main__":
    main()

# st.write("📁 This second part simulates the sending of a JSON payload to API Projection and returns the projection of legacy.")

# json_proj = st.text_area(":black_nib: Enter JSON payload after Fast Pat:", height=200)

# # Button to send the request
# if st.button("Send Request to our API Projection"):
#     if json:
#         try:
#             # Parse the input as JSON
#             json_a = json.loads(json_proj)
            
#             # Call the API with the parsed JSON
#             json_b , time_elapsed = call_api(json_a,PROJ_URL)
            
#             if json_b:
#                 st.subheader(f"API Response (After Proj Pat) after {time_elapsed} seconds")
#                 st.json(json_b)  # Display the JSON response in a readable format
#             else:
#                 st.error("Failed to get a valid response from the API.")
#         except json.JSONDecodeError:
#             st.error("Invalid JSON format in the input.")
#     else:
#         st.error("Please enter a JSON payload.")