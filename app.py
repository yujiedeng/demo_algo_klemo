import streamlit as st
import plotly.express as px
import pandas as pd
import requests
import json
import os
import boto3
import time
from datetime import datetime
from helpers.jsonGen import situation_dict,montants_fin,montants_immo,montants_emprunt,montants_pro,ENUM_OPTIONS
from helpers.simul_contraint_main_sous_cat_v2 import simul_obj_client_from_dicts,import_json,impute_json
from helpers.auth import check_password
from helpers.func import *


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
            updated[key] = [st.number_input(f"{name} - {key}", value=val[0], step=1)]

        elif isinstance(val, bool):
            updated[key] = st.radio(
                f"{name} - {key}", options=[True, False], index=0 if val else 1,
                horizontal=True,
                key=f"{name}_{key}"
            )
        elif isinstance(val, (int, float)):
            updated[key] = st.number_input(f"{name} - {key}", value=val, step=1)
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


def main():
    # Streamlit UI
    # Title and description
    global situation_dict,montants_fin,montants_immo,montants_emprunt,montants_pro,ENUM_OPTIONS

    if 'json_proj' not in st.session_state:
        st.session_state.json_proj = None
    if 'json_synth_id' not in st.session_state:
        st.session_state.json_synth_id = None
    # Initialize session state with your imported dictionaries
    if 'situation_dict' not in st.session_state:
        st.session_state.situation_dict = situation_dict
    if 'montants_fin' not in st.session_state:
        st.session_state.montants_fin = montants_fin
    if 'montants_immo' not in st.session_state:
        st.session_state.montants_immo = montants_immo
    if 'montants_emprunt' not in st.session_state:
        st.session_state.montants_emprunt = montants_emprunt
    if 'montants_pro' not in st.session_state:
        st.session_state.montants_pro = montants_pro
    if 'input_json' not in st.session_state:
        input_json = import_json("json/vide_new.json")
        st.session_state.input_json = input_json

    st.title("👋🏻 HOME PAGE 🏠 - API Algo Klemo")

    with st.expander("😇 PART 0.1 : Create Personnae", expanded=True):
        st.sidebar.header("Navigation FastPat")
        section = st.sidebar.radio("Choose Section", ["Situation", "Montants Financiers", "Immobilier", "Emprunts", "Pro"])

        if section == "Situation":
            updated_dict = render_dict_inputs("Situation",  st.session_state.situation_dict)
            st.session_state.situation_dict = updated_dict
        elif section == "Montants Financiers":
            updated_dict = render_dict_inputs("Montants Financiers",  st.session_state.montants_fin)
            st.session_state.montants_fin = updated_dict
        elif section == "Immobilier":
            updated_dict = render_dict_inputs("Immobilier",  st.session_state.montants_immo)
            st.session_state.montants_immo = updated_dict
        elif section == "Emprunts":
            updated_dict = render_dict_inputs("Emprunts",  st.session_state.montants_emprunt)
            st.session_state.montants_emprunt = updated_dict
        elif section == "Pro":
            updated_dict = render_dict_inputs("Pro",  st.session_state.montants_pro)
            st.session_state.montants_pro = updated_dict

        p1=simul_obj_client_from_dicts(st.session_state.situation_dict, 
                                       st.session_state.montants_fin, 
                                       st.session_state.montants_immo, 
                                       st.session_state.montants_pro, 
                                       st.session_state.montants_emprunt)
        fresh_json = import_json("json/vide_new.json")
        impute_json(fresh_json,p1)
        st.session_state.input_json = fresh_json
        
        if st.button("Generate JSON"):
            st.json(st.session_state.input_json)
            st.download_button("Download JSON", json.dumps(st.session_state.input_json, indent=2), file_name="client_situation.json", mime="application/json")
        
    with st.expander("📁 PART 1 : API FillScore", expanded=True):
        # uploaded_file = st.file_uploader("Choisir un fichier JSON", type="json")
        
        # if uploaded_file is not None:
            # Read the JSON file
            # file_contents = uploaded_file.read()
            # json_data = json.loads(file_contents)
            # display_customer_info(json_data)

            # Display the JSON data in a text area

        mode = st.radio(
            "Source des données pour la requête :",
            ["Utiliser la sortie précédente", "Entrer un JSON manuellement"]
        )

        # --- Display text area depending on mode ---
        if mode == "Entrer un JSON manuellement":
            # Show a blank (or last known) JSON to edit
            default_value = json.dumps(st.session_state.get("input_json", {}), indent=2)
            fs_content = st.text_area(
                ":black_nib: Entrer Infos JSON :",
                value=default_value,
                height=200,
                key="fs_content"
            )
        else:
            # Use previous JSON directly
            fs_content = json.dumps(st.session_state.get("input_json", {}), indent=2)
            st.code(fs_content, language="json")

        # st.text_area("Charged Payload FastPat", json.dumps(st.session_state.input_json, indent=2), height=300, key="fastpat_content")

        # Button to send the request
        if st.button("Envoyer une requête à l'API FillScore"):
            if st.session_state.input_json: 
                try:
                    # Call the API with the parsed JSON
                    json_proj, time_elapsed = call_api(st.session_state.input_json,FILL_SCORE_URL)
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
            # st.text_area(":black_nib: Entrer Infos:", value=json.dumps(st.session_state.json_proj, indent=2),height = 200, key = "bilanpat_content")
                
            mode_bilan = st.radio(
                "Source des données pour la Bilan Pat :",
                ["A - Utiliser la sortie précédente", "B - Entrer un JSON manuellement"]
            )

            # --- Display text area depending on mode ---
            if mode_bilan == "B - Entrer un JSON manuellement":
                # Show a blank (or last known) JSON to edit
                default_value = json.dumps(st.session_state.get("json_proj", {}), indent=2)
                bp_content = st.text_area(
                    ":black_nib: Entrer Infos JSON :",
                    value=default_value,
                    height=200,
                    key="bilan_default_content"
                )
            
            else:
                # Use previous JSON directly
                bp_content = json.dumps(st.session_state.get("json_proj", {}), indent=2)
                # st.code(bp_content, language="json")
            st.session_state.json_proj = json.loads(bp_content)
            
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

                            display_bilan_synth(json_synth)

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
                    "objectif": MAPPINGS_OBJECTIF_CHOICES[selected_objectif],
                    "sousObjectif": MAPPINGS_OBJECTIF_CHOICES[selected_sous_objectif],
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
                            
                            display_strat_output(selected_objectif,selected_sous_objectif,st.session_state.payload_strat, strat_output)

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
    if check_password():
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