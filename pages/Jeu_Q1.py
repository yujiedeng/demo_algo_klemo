import streamlit as st
import json 
import requests
from helpers.auth import check_password
from helpers import func
from datetime import datetime

# if not check_password():
#     st.stop()

st.title("♟️ Question 1 - KLEMO LIFE GAME")
st.write("Vous avez 25 ans, un premier boulot et aucune connaissance en investissement.")
st.write("Pour débuter, quelle option choisissez-vous ?")

# --- Step 1: Initialize session_state ---
if "base_info_1" not in st.session_state:
    st.session_state.base_info_1 = func.load_base_info("q1")

# --- Step 2: Show editable section ---
with st.expander("👤 Information", expanded=True):
    col1,col2,col3  = st.columns(3)

    with col1:
        age = st.number_input("Mon Age", min_value=18, max_value=100, value=datetime.today().year - int(st.session_state.base_info_1["Client"]["PatClientDetail"][0]["dateNaissance"][:4]))
        situation = st.selectbox("Ma Situation Personnelle", ["Célibataire", "Union Libre", "Pacsé(e)", "Marié(e)"], index=["Célibataire", "Union Libre", "Pacsé(e)", "Marié(e)"].index(st.session_state.base_info_1["Client"]["PatClientDetail"][0]["typeUnion"]))
        charge = st.number_input("Mes dépenses courantes mensuelles (€)", min_value=0, step=100, value=int(st.session_state.base_info_1["Cashflow"]["PatCashflowDetail"][0]["depensesCourantes"]))

    with col2:
        loyer = st.number_input("Mon loyer mensuel (€)", min_value=0, step=100, value=int(st.session_state.base_info_1["Cashflow"]["PatCashflowDetail"][0]["loyerHabitationPrincipale"]))
        emprunt = st.number_input("Mon emprunt étudiant (€)", min_value=0, step=1000, value=int(st.session_state.base_info_1["Emprunt"]["PatEmpruntDetail"][0]["montantRestantDu"]))

    with col3:
        fin = st.number_input("Mon épargne Livret A (€)", min_value=0, step=1000, value=int(st.session_state.base_info_1["Fin"]["PatFinDetail"][0]["value"]))
        salaire = st.number_input("Mon salaire brut annuel (€)", min_value=0, step=1000, value=int(st.session_state.base_info_1["Cashflow"]["PatCashflowDetail"][0]["revenusActivite"])) 
    
    # Save modifications
    if st.button("💾 Enregistrer"):
        st.session_state.base_info_1["Client"]["PatClientDetail"][0]["dateNaissance"] = f"{datetime.today().year - age}-01-01"
        st.session_state.base_info_1["Client"]["PatClientDetail"][0]["typeUnion"] = situation
        st.session_state.base_info_1["Emprunt"]["PatEmpruntDetail"][0]["montantRestantDu"] = emprunt
        st.session_state.base_info_1["Emprunt"]["PatEmpruntDetail"][0]["quotePart"] = emprunt
        st.session_state.base_info_1["Fin"]["PatFinDetail"][0]["value"] = fin
        st.session_state.base_info_1["Fin"]["PatFinDetail"][0]["quotePart"] = fin
        st.session_state.base_info_1["Cashflow"]["PatCashflowDetail"][0]["loyerHabitationPrincipale"] = loyer
        st.session_state.base_info_1["Cashflow"]["PatCashflowDetail"][0]["depensesCourantes"] = charge
        st.session_state.base_info_1["Cashflow"]["PatCashflowDetail"][0]["revenusActivite"] = salaire
        
        with open("json/q1.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state.base_info_1, f, ensure_ascii=False, indent=4)
        st.success(f"✅ Info Enregistrée")


# --- Step 2: Show editable section ---
with st.expander("🕒 BILAN KLEMO", expanded=True):

    if st.button("LANCER LA SIMULATION KLEMO"):
        
        json_proj, time_elapsed = func.call_api(st.session_state.base_info_1,func.FILL_SCORE_URL)
        st.session_state.json_proj = json_proj["output"]
        
        json_synth, time_elapsed = func.call_api(st.session_state.json_proj,func.PROJ_URL)
        
        st.session_state.json_synth = json_synth
                   
        st.session_state.json_synth_id = json_synth["requestId"]
        st.session_state.json_synth_key = json_synth["requestKey"]
        
        st.session_state.simulation_ready = True
        st.success("✅ Simulation Bilan exécutée avec succès !")

        # st.subheader(f"Temps de réponse BilanPat: {time_elapsed} secondes")
                # st.write(f"Résultats json enregistrés dans un bucket s3 avec suffix:{json_synth['requestKey']}")

    if "simulation_ready" in st.session_state and st.session_state.simulation_ready:
        func.display_bilan_synth(st.session_state.json_synth)
    else:
        st.info("👉 Cliquez sur **LANCER LA SIMULATION KLEMO** pour commencer.")

with st.expander("💡 RECOS KLEMO", expanded=True):
    if 'json_synth_id' not in st.session_state:
        st.session_state.json_synth_id = None

    with st.expander("📝 FORMULAIRE OBJECTIF", expanded=True):
            # Text area for the next API call
            # st.subheader("RECOS KLEMO ")
            # st.text_area("Payload for API Bilan Pat", json.dumps(json_proj, indent=2), height=300, key="bilanpat_content")
            # st.text_area(":black_nib: Enter Json:", value=json.dumps(st.session_state.json_proj, indent=2),height = 200, key = "bilanpat_content")
            # payload_strat_txt = st.text_area(":black_nib: Enter JSON payload of Strat Pat:", height=200)
            
        col1, col2 = st.columns(2)

        with col1:
            # Objective selection
            selected_objectif = st.selectbox(
                "Choisir un Objectif",
                options=list(func.OBJECTIF_CHOICES.keys()),
                key="objectif_select"
            )
        
        with col2:
            # Sub-objective selection (dynamic based on objective)
            selected_sous_objectif = st.selectbox(
                "Choisir un Objectif Détaillé",
                options=func.OBJECTIF_CHOICES[selected_objectif],
                key="sous_objectif_select"
            )
        
        paramObj = st.text_area(":black_nib: entrer des paramètres d'objectif (optionnel):",value='{"debut":"2029-10-31", "montantRegulier":400,"horizon":24}', height=200)
        
    if st.button("LANCER SIMULATION RECOS KLEMO"):
        # Build the payload
        st.session_state.payload_strat = {
            "requestId": st.session_state.json_synth_id, 
            "requestKey": st.session_state.json_synth_key,
            "objectif": func.MAPPINGS_OBJECTIF_CHOICES[selected_objectif],
            "sousObjectif": func.MAPPINGS_OBJECTIF_CHOICES[selected_sous_objectif],
            "paramObjectif": json.loads(paramObj),
            "investorProfile":{"level":"Balanced","esg":"Neutral"}
        }

    # json_proj = json.loads(json_proj)
    # if st.button("Send Request to our API StratPat"):
        if st.session_state.json_synth_id: 
            # Call the API with the parsed JSON
            init_strat, time_elapsed = func.call_api(st.session_state.payload_strat,func.STRAT_INIT_URL)
    
            if init_strat:
                request_id     = st.session_state.payload_strat.get("requestId")
                strat_result   = func.poll_result(func.STRAT_URL,request_id)
                print("debugging: strat_result",strat_result)
                strat_output = strat_result.json()["output"]
                func.display_strat_output(selected_objectif,selected_sous_objectif, st.session_state.payload_strat, strat_output,5)

# streamlit, pre-save a json, show in a pliable section base info: age, situation, emprunt, give possibility to change it and save to state session, then add a button to launch a api call

# "25 ans"
# Célibataire
# Emprunt étudiant 9800 €
# Loyer 900 €
# Charges et dépense annuel 800 €
# Salaire 40000 € Brut Annuel 

  
# 25 ans 1er boulot 1ers investissements (Générer un revenu supp) 

# Vous n’y connaissez pas grand chose on vous conseille d’investir sur 

# - option A : Ton banquier te suggère une AV, tu signes !
#     - tu prends des frais énormes
# - option B : Un CGP te vend des parts de SCPI
#     - la SCPI s’effondre et tu perds ton invest.
# - option C : tu remplis ton livret A comme un écureuil
#     - ton argent n’avance pas, l’inflation le bats.

# la réponse Klemo : on te mesure une réponse concrète adaptée, à bas frais et diversifiée en fonction de ta situation