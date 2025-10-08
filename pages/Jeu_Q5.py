# 55 ans
# Marié 2 enfants
# RP acheté à 35 ans 
# Emprunt RP remoboursé
# immo à 360k 
# Charges et dépense annuel 1200 €
# Salaire 85000 € Brut Annuel iso 
# fin : PEA 20k 
#       livret 3k   
#       PERO 30k
#       PER 42k : Versement 375 par mois, jusqu'à 2045

# envisage des retrait d'investissement 


# PER 22k : Versement 375 par mois, jusqu'à 2045 

import streamlit as st
import json 
import requests
from helpers.auth import check_password
from helpers import func
from datetime import datetime

# if not check_password():
#     st.stop()

st.title("♟️ Question 5 - KLEMO LIFE GAME")
st.write("Vous avez 60 ans")
st.write("Vous avez envie de sentir le vent dans vos cheveux et vous partez faire le tour du monde en voilier.")
st.write("Comment financer votre épopée ?")

# --- Step 1: Initialize session_state ---
if "base_info_5_5" not in st.session_state:
    st.session_state.base_info_5 = func.load_base_info("q5")

# --- Step 2: Show editable section ---
with st.expander("👤 Information", expanded=True):
    col1,col2,col3  = st.columns(3)

    with col1:
        age = st.number_input("Mon Age", min_value=18, max_value=100, value=datetime.today().year - int(st.session_state.base_info_5["Client"]["PatClientDetail"][0]["dateNaissance"][:4]))
        situation = st.selectbox("Ma Situation Personnelle", ["Célibataire", "Union Libre", "Pacsé(e)", "Marié(e)"], index=["Célibataire", "Union Libre", "Pacsé(e)", "Marié(e)"].index(st.session_state.base_info_5["Client"]["PatClientDetail"][0]["typeUnion"]))
        charge = st.number_input("Mes dépenses courantes mensuelles (€)", min_value=0, step=100, value=int(st.session_state.base_info_5["Cashflow"]["PatCashflowDetail"][0]["depensesCourantes"]))

    with col2:
        loyer = st.number_input("Mon loyer mensuel (€)", min_value=0, step=100, value=int(st.session_state.base_info_5["Cashflow"]["PatCashflowDetail"][0]["loyerHabitationPrincipale"]))
        emprunt = st.number_input("Mon emprunt étudiant (€)", min_value=0, step=1000, value=int(st.session_state.base_info_5["Emprunt"]["PatEmpruntDetail"][0]["montantRestantDu"]))

    with col3:
        fin = st.number_input("Mon épargne Livret A (€)", min_value=0, step=1000, value=int(st.session_state.base_info_5["Fin"]["PatFinDetail"][0]["value"]))
        salaire = st.number_input("Mon salaire brut annuel (€)", min_value=0, step=1000, value=int(st.session_state.base_info_5["Cashflow"]["PatCashflowDetail"][0]["revenusActivite"])) 
    
    # Save modifications
    if st.button("💾 Enregistrer"):
        st.session_state.base_info_5["Client"]["PatClientDetail"][0]["dateNaissance"] = f"{datetime.today().year - age}-01-01"
        st.session_state.base_info_5["Client"]["PatClientDetail"][0]["typeUnion"] = situation
        st.session_state.base_info_5["Emprunt"]["PatEmpruntDetail"][0]["montantRestantDu"] = emprunt
        st.session_state.base_info_5["Emprunt"]["PatEmpruntDetail"][0]["quotePart"] = emprunt
        st.session_state.base_info_5["Fin"]["PatFinDetail"][0]["value"] = fin
        st.session_state.base_info_5["Fin"]["PatFinDetail"][0]["quotePart"] = fin
        st.session_state.base_info_5["Cashflow"]["PatCashflowDetail"][0]["loyerHabitationPrincipale"] = loyer
        st.session_state.base_info_5["Cashflow"]["PatCashflowDetail"][0]["depensesCourantes"] = charge
        st.session_state.base_info_5["Cashflow"]["PatCashflowDetail"][0]["revenusActivite"] = salaire
        
        with open("json/q5.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state.base_info_5, f, ensure_ascii=False, indent=4)
        st.success(f"✅ Info Enregistrée")


# --- Step 2: Show editable section ---
with st.expander("🕒 BILAN KLEMO", expanded=True):

    if st.button("LANCER LA SIMULATION KLEMO"):
        
        json_proj, time_elapsed = func.call_api(st.session_state.base_info_5,func.FILL_SCORE_URL)
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

