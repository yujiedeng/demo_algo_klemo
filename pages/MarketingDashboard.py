import streamlit as st
from streamlit_timeline import st_timeline

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime
import os 
from helpers.auth import check_password
import pytz

if not check_password():
    st.stop()

df = pd.read_parquet(f"dataMarket/downloads.parquet")
mtime = os.path.getmtime("dataMarket/downloads.parquet")

# Create a timezone-aware datetime in UTC
utc_tz = pytz.UTC
utc_dt = utc_tz.localize(datetime.fromtimestamp(mtime))

# # Convert to CET/CEST (Europe/Paris handles DST automatically)
paris_tz = pytz.timezone("Europe/Paris")
cet_dt = str(utc_dt.astimezone(paris_tz))[:19]


df["date"] = pd.to_datetime(df["created_at_date"])
df["verified_pct"] = round(df["verified"] / df["total"] * 100, 2)

# --- Weekly aggregation ---
df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="d")
df_weekly = (
    df.groupby("week_start", as_index=False)
      .agg({"verified": "sum", "not_verified": "sum", "total": "sum"})
)
df_weekly["verified_pct"] = round(df_weekly["verified"] / df_weekly["total"] * 100, 2)


# --- Streamlit App ---
st.set_page_config(
    page_title="My Dashboard",
    layout="wide",   # ✅ Enables full-width content area
    initial_sidebar_state="collapsed"
)
st.title("KLEMO Reporting Analyse Marketing")
st.write(f"Données mises à jour le {cet_dt}")

# Calendar filter
min_date, max_date = df["date"].min(), df["date"].max()
date_range = st.date_input("Select date range:", [min_date, max_date])

mask = (df["date"] >= pd.to_datetime(date_range[0])) & (df["date"] <= pd.to_datetime(date_range[1]))
df_filtered = df.loc[mask].copy()

df_daily = (
    df_filtered.groupby("date", as_index=False)[["verified", "not_verified", "total"]]
               .sum()
)
df_daily["verified_pct"] = round(df_daily["verified"] / df_daily["total"] * 100, 2)



st.subheader("📬 Partie I: Focus Inscriptions et Vérification Mail")
# 2️⃣ Build dual-axis chart
fig_daily = go.Figure()

# Bars: verified / not verified counts
fig_daily.add_trace(go.Bar(
    x=df_daily["date"],
    y=df_daily["verified"],
    name="Verified",
    marker_color="#2ecc71",
    text=df_daily["verified"],  # ⬅️ Valeurs à afficher
    textposition="inside",       # ⬅️ Position du texte
    textangle=0,
    textfont=dict(color="white", size=12),
))
fig_daily.add_trace(go.Bar(
    x=df_daily["date"],
    y=df_daily["not_verified"],
    name="Not Verified",
    marker_color="#e74c3c",
    text=df_daily["not_verified"],  # ⬅️ Valeurs à afficher
    textposition="inside",
    textangle=0,
    textfont=dict(color="white", size=12),
))

# Line: % verified (on secondary y-axis)
fig_daily.add_trace(go.Scatter(
    x=df_daily["date"],
    y=df_daily["verified_pct"],
    name="Verification Rate (%)",
    mode="lines+markers",
    marker=dict(size=8, color="#3498db"),
    line=dict(width=2, color="#3498db"),
    yaxis="y2",
    text=df_daily["verified_pct"],  # ⬅️ Valeurs à afficher
    textposition="top center",
    textfont=dict(color="white", size=12),
)
)

# fig_daily.update_traces(
#     textangle=0,               # 👈 keep all labels horizontal
#     textposition='inside',     # or 'outside' if you want them above bars
#     textfont=dict(size=11)
# )

# 3️⃣ Layout & styling
fig_daily.update_layout(
    title="Daily Verification Funnel (Counts + %)",
    xaxis_title="Date",
    yaxis_title="Nombre d'inscriptions",
    yaxis2=dict(
        title="Verification Rate (%)",
        overlaying="y",
        side="right",
        range=[0, 100],
        showgrid=False
    ),
    barmode="stack",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    showlegend=True,
    template="plotly_white",
    autosize=True,
    height=None,  # Let Streamlit/Plotly expand naturally
    margin=dict(l=0, r=0, t=30, b=0)
)

st.plotly_chart(fig_daily, use_container_width=True)


# --- Weekly summary ---
st.subheader("🗓️ Weekly Summary")

fig_weekly = px.bar(
    df_weekly,
    x="week_start",
    y="verified_pct",
    text="verified_pct",
    title="Weekly Verification Rate (%)",
)
fig_weekly.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
st.plotly_chart(fig_weekly, use_container_width=True)

# --- KPIs ---
st.subheader("📊 Key Metrics")
col1, col2 = st.columns(2)
col1.metric("Total Verified", int(df_filtered["verified"].sum()))
col2.metric("Average Verification Rate", f"{df_filtered['verified_pct'].mean():.2f}%")


st.subheader("📬 Partie II: Focus Analyse Conversion")
st.subheader("⏳️ Analyse Funnel: toute période confondue")

df_ana = pd.read_parquet(f"dataMarket/analysis.parquet")
stages = ['Total Inscrits', 'Verified Email', 'Started Chat', 'Ended Chat','Bilan Generated', 'Answered Target Qst', 'Answered Knowledge Qst', 'Answered Risk Qst', 'Answered ESG Qst', 'Begin Mission Letter', 'Signed Mission Letter ', 'Generated Recommendations', 'KYC Approved', 'Consulted Recommendations']
counts = [
    len(df_ana), 
    df_ana['step_1_mail_verified'].sum(),  
    df_ana['step_2_chat_started'].sum(),   
    df_ana['step_3_chat_end'].sum(),
    df_ana['step_4_bilan'].sum(),
    df_ana['step_5_qst_target'].sum(),
    df_ana['step_6_qst_fin'].sum(),
    df_ana['step_7_qst_risk'].sum(),
    df_ana['step_8_esg'].sum(),
    df_ana['step_9_lettre_mission'].sum(),
    df_ana['step92_status_sign_signed'].sum(),
    df_ana['step_10_generated_reco'].sum(),
    df_ana['step_11_kyc'].sum(),
    df_ana['step_12_reco_consulted'].sum()
]

# Calculate losses (absolute and percentage drop from previous step)
losses_abs = [0] + [counts[i-1] - counts[i] for i in range(1, len(counts))]
losses_pct = [0] + [(losses_abs[i] / counts[i-1] * 100) if counts[i-1] > 0 else 0 for i in range(1, len(counts))]

# Create text labels with counts, % of total, and loss info
text_labels = [
    f"{counts[0]}<br>{(counts[0] / counts[0] * 100):.1f}% of total<br>(Start)",
    f"{counts[1]}<br>{(counts[1] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[1]} ({losses_pct[1]:.1f}%)",
    f"{counts[2]}<br>{(counts[2] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[2]} ({losses_pct[2]:.1f}%)",
    f"{counts[3]}<br>{(counts[3] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[3]} ({losses_pct[3]:.1f}%)",
    f"{counts[4]}<br>{(counts[4] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[4]} ({losses_pct[4]:.1f}%)",
    f"{counts[5]}<br>{(counts[5] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[5]} ({losses_pct[5]:.1f}%)",
    f"{counts[6]}<br>{(counts[6] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[6]} ({losses_pct[6]:.1f}%)",
    f"{counts[7]}<br>{(counts[7] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[7]} ({losses_pct[7]:.1f}%)",
    f"{counts[8]}<br>{(counts[8] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[8]} ({losses_pct[8]:.1f}%)",
    f"{counts[9]}<br>{(counts[9] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[9]} ({losses_pct[9]:.1f}%)",
    f"{counts[10]}<br>{(counts[10] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[10]} ({losses_pct[10]:.1f}%)",
    f"{counts[11]}<br>{(counts[11] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[11]} ({losses_pct[11]:.1f}%)",
    f"{counts[12]}<br>{(counts[12] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[12]} ({losses_pct[12]:.1f}%)",
    f"{counts[13]}<br>{(counts[13] / counts[0] * 100):.1f}% of total<br>Loss: {losses_abs[13]} ({losses_pct[13]:.1f}%)",
]

# Create the funnel plot using Plotly with enhanced text
fig = go.Figure(data=[go.Funnel(
    y=stages,
    x=counts,
    text=text_labels,
    textinfo="text",  # Use custom text labels
    marker={"color": ["#D5DBDB","#DAE3E5","#DFEAF0", "#EDE3D8","#AED6F1", "#CBD0D8","#A9DFBF", "#FAD7A0","#D5D2C7","#D5F2C7", "#F5B7B1", "#BB8FCE", "#7FB3D5", "#76D7C4"]},
)])


fig.update_layout(
    title="Funnel Analysis: User Progression Through Steps (with Step Losses)",
    title_x=0.5,
    font_size=20,

)

st.plotly_chart(fig, use_container_width=True)

st.subheader("🧑‍🧑‍🧒 Analyse Cohort par semaine")

cohort_stats = df_ana.groupby('cohort').agg({
    'step_1_mail_verified': 'sum',
    'step_2_chat_started': 'sum',
    'step_3_chat_end': 'sum',
    'step_4_bilan': 'sum',
    'step_5_qst_target': 'sum',
    'step_6_qst_fin': 'sum',
    'step_7_qst_risk': 'sum',
    'step_8_esg': 'sum',
    'step_9_lettre_mission': 'sum',
    'step92_status_sign_signed':'sum',
    'step_10_generated_reco': 'sum',
    'step_11_kyc': 'sum',
    'step_12_reco_consulted': 'sum'
}).reset_index()

# Add total cohort size
cohort_stats['total'] = df_ana.groupby('cohort').size().values

# Calculate percentages relative to cohort total (100% at Total)
cohort_stats['%MailVerifie'] = (cohort_stats['step_1_mail_verified'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%DebutChat'] = (cohort_stats['step_2_chat_started'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%FinChat'] = (cohort_stats['step_3_chat_end'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%Bilan'] = (cohort_stats['step_4_bilan'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%QstObjectif'] = (cohort_stats['step_5_qst_target'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%QstFinance'] = (cohort_stats['step_6_qst_fin'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%QstRisque'] = (cohort_stats['step_7_qst_risk'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%QstESG'] = (cohort_stats['step_8_esg'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%StartedLettreMission'] = (cohort_stats['step_9_lettre_mission'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%SignLettreMission'] = (cohort_stats['step92_status_sign_signed'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%RecoGenere'] = (cohort_stats['step_10_generated_reco'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%KYC'] = (cohort_stats['step_11_kyc'] / cohort_stats['total'] * 100).round(1)
cohort_stats['%RecoConsulte'] = (cohort_stats['step_12_reco_consulted'] / cohort_stats['total'] * 100).round(1)

# Prepare data for line plot: melt to long format
steps = ['Total', 'Verified Email', 'Started Chat', 'Ended Chat', 'Bilan Generated', 'Answered Target Qst', 'Answered Knowledge Qst', 'Answered Risk Qst', 'Answered ESG Qst', 'Begin Letter Mission','Signed Mission Letter', 'Generated Recommendations', 'KYC Approved', 'Consulted Recommendations']
melted = cohort_stats.melt(
    id_vars=['cohort'],
    value_vars=['total', '%MailVerifie', '%DebutChat', '%FinChat','%Bilan','%QstObjectif','%QstFinance','%QstRisque','%QstESG','%StartedLettreMission','%SignLettreMission','%RecoGenere','%KYC','%RecoConsulte'],
    var_name='step_raw',
    value_name='value'
)

# Map step_raw to actual step names
step_mapping = {
    'total': 'Total Inscrits',
    '%MailVerifie': 'Verified Email',
    '%DebutChat': 'Started Chat',
    '%FinChat': 'Ended Chat',
    '%Bilan': 'Bilan Generated',
    '%QstObjectif': 'Answered Target Qst',
    '%QstFinance': 'Answered Knowledge Qst',
    '%QstRisque': 'Answered Risk Qst',
    '%QstESG': 'Answered ESG Qst',
    '%StartedLettreMission': 'Begin Letter Mission',
    '%SignLettreMission': 'Signed Letter of Mission',
    '%RecoGenere': 'Generated Recommendations',
    '%KYC': 'KYC Approved',
    '%RecoConsulte': 'Consulted Recommendations'

}
melted['step'] = melted['step_raw'].map(step_mapping)

# Set Total to 100% (override the count value)
melted.loc[melted['step_raw'] == 'total', 'value'] = 100

# Select relevant columns
melted = melted[['cohort', 'step', 'value']]

# Create the line plot using Plotly
fig = go.Figure()

for cohort in melted['cohort'].unique():
    cohort_data = melted[melted['cohort'] == cohort]
    fig.add_trace(go.Scatter(
        x=cohort_data['step'],
        y=cohort_data['value'],
        mode='lines+markers',
        name=cohort,
        line=dict(width=2),
        marker=dict(size=8)
    ))

fig.update_layout(
    title="Cohort Funnel Analysis: Conversion Rates by Step (Overlapping Lines)",
    title_x=0.5,
    xaxis_title="Steps",
    yaxis_title="Conversion Rate (%)",
    yaxis=dict(range=[0, 100]),
    hovermode='x unified',
    font_size=12,
    legend_title="Cohorts"
)

st.plotly_chart(fig, use_container_width=True)
st.write("Attention: etape %Ansewered Target Qst correspond à deux étapes: %Redirection vers page Reco (Target) + %Fin de Questionnaire Target")

result_bilan = df_ana.groupby("cohort", as_index=False)["step_4_bilan"].sum()
result_reco = df_ana.groupby("cohort", as_index=False)["step_10_generated_reco"].sum()

# Group by cohort and aggregate mean + median
agg_df = df_ana.groupby("cohort", as_index=False).agg(
    {
        "delta_sec_eer_bilan": ["mean", "median"],
        "delta_sec_eer_reco_generated": ["mean", "median"]
    }
)
agg_df.columns = ["cohort", "temps_bilan_mean_sec", "temps_bilan_median_sec","temps_recoGenerated_mean_sec", "temps_recoGenerated_median_sec"]
agg_df["moyenne_eer_bilan_J"] = round(agg_df["temps_bilan_mean_sec"] / (3600 * 24),3)
agg_df["mediane_eer_bilan_J"] = round(agg_df["temps_bilan_median_sec"] / (3600 * 24),3)

agg_df["moyenne_eer_recoG_J"] = round(agg_df["temps_recoGenerated_mean_sec"] / (3600 * 24),3)
agg_df["mediane_eer_recoG_J"] = round(agg_df["temps_recoGenerated_median_sec"] / (3600 * 24),3)

df_weekly["week_start"]=df_weekly["week_start"].astype(str)
df_weekly = pd.merge(df_weekly, result_bilan, left_on="week_start", right_on="cohort", how="left")
df_weekly = pd.merge(df_weekly, result_reco,  left_on="week_start", right_on="cohort", how="left")
df_weekly = pd.merge(df_weekly, agg_df[["cohort","moyenne_eer_bilan_J","mediane_eer_bilan_J","moyenne_eer_recoG_J","mediane_eer_recoG_J"]], left_on="week_start", right_on="cohort", how="left")

df_weekly.rename(columns={"total":"inscrits","verified":"mail_verified","step_4_bilan": "bilan_generated", "step_10_generated_reco": "reco_generated"}, inplace=True)

df_weekly = df_weekly[["week_start","inscrits","mail_verified","bilan_generated","moyenne_eer_bilan_J","mediane_eer_bilan_J","reco_generated","moyenne_eer_recoG_J","mediane_eer_recoG_J"]]
st.write('pour Anne')
st.dataframe(df_weekly)

df_daily_bilan = pd.read_parquet(f"dataMarket/bilan_daily.parquet")
st.dataframe(df_daily_bilan)

df_sous = pd.read_parquet("dataMarket/subscribe.parquet")
st.dataframe(df_sous)


# items = [
#     {"id": 1, "content": "Marketing: Soirée Lancement", "start": "2025-10-09"},
#     {"id": 2, "content": "Dev: Fix FireBase Mail à Vérifier", "start": "2025-03-15"},
#     {"id": 3, "content": "Marketing: 1er Campagne ", "start": "2025-10-21"},
# ]
st.subheader("📅 Project Timeline")

items = [
    {"id": 1, "content": "🥂 Soirée Lancement", "start": "2025-10-09T19:00:00", "end": "2025-10-10T00:00:00", "group": "1"},

    {"id": 2, "content": "🛠️ Fix FireBase Mail à Vérifier", "start": "2025-10-13T11:00:00",  "group": "2"},

    {"id": 3, "content": "🔊 Lancement 1er Campagne RS", "start": "2025-10-21T07:00:00", "group": "3"},

    {"id": 4, "content": "💌 Newsletter Voxe", "start": "2025-10-21T07:00:00", "group": "4"},
    
    {"id": 5, "content": "🛠️ Fix Bug Chat SSO", "start": "2025-10-28T17:00:00", "end": "2025-10-29T13:00:00", "group": "5"},

    {"id": 6, "content": "💌 Newsletter II Voxe", "start": "2025-10-29T06:00:00", "group": "6"},

    {"id": 7, "content": "🛠️ Simplify Onboarding Page", "start": "2025-11-28T017:00:00", "group": "7"},
]


# Sample editable data
if "events" not in st.session_state:
    st.session_state.events = pd.DataFrame([
        {"Start": items[0]["start"], "End": items[0]["end"], "Event": items[0]["content"], "Type": "Marketing"},
        {"Start": items[1]["start"], "Event": items[1]["content"], "Type": "Dev"},
        {"Start": items[2]["start"], "Event": items[2]["content"], "Type": "Marketing"},
        {"Start": items[3]["start"], "Event": items[3]["content"], "Type": "Marketing"},
        {"Start": items[4]["start"], "End": items[4]["end"], "Event": items[4]["content"], "Type": "Dev"},
        {"Start": items[5]["start"], "Event": items[5]["content"], "Type": "Marketing"},
        {"Start": items[6]["start"], "Event": items[6]["content"], "Type": "Dev"}
    ])

# Editable table
edited_df = st.data_editor(st.session_state.events, num_rows="dynamic", use_container_width=True)

# Save edits to session state
st.session_state.events = edited_df

# Ensure date column is datetime
edited_df["Start"] = pd.to_datetime(edited_df["Start"], errors="coerce")

# Drop invalid dates
timeline_df = edited_df.dropna(subset=["Start"])

if not timeline_df.empty:
    # Plotly timeline chart
    fig = px.scatter(
        timeline_df,
        x="Start",
        y="Event",
        color="Type",
        hover_data=["Event", "Start", "Type"],
        size_max=20,
        height=400
    )

    fig.update_layout(
        yaxis=dict(autorange="reversed"),  # So earliest events on top
        xaxis_title="Start",
        yaxis_title="Event",
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No valid events to display. Make sure all dates are valid.")



st.subheader(":hook: Target and Recommandation Analysis")
df = pd.read_parquet(f"dataMarket/recoAnalysis.parquet")

def count_and_pct(df, col):
    cnt = df.groupby(col).size().reset_index(name="count")
    cnt["pct"] = cnt["count"] / cnt["count"].sum() * 100
    return cnt.sort_values("count", ascending=False)

count_obj = count_and_pct(df, "objectif")
count_ssobj = count_and_pct(df, "sous_objectif")
count_reco = count_and_pct(df, "RECOMMENDATION_ID")


# -----------------------------------
# 2) Graphiques Plotly
# -----------------------------------

# --- Bar cat1 ---
fig1 = px.bar(
    count_obj,
    x="objectif",
    y="count",
    text= count_obj["pct"].round(1).astype(str) + "%",
    title="Répartition Objectif (count + %)"
)
fig1.update_traces(textposition="outside")
st.plotly_chart(fig1, use_container_width=True)

# --- Bar cat2 ---
fig2 = px.bar(
    count_ssobj,
    x="sous_objectif",
    y="count",
    text= count_ssobj["pct"].round(1).astype(str) + "%",
    title="Répartition Sous_objectif (count + %)"
)
fig2.update_layout(xaxis={'categoryorder':'total descending'})
fig2.update_traces(textposition="outside")
st.plotly_chart(fig2, use_container_width=True)

# --- Bar cat3 (top 20 pour lisibilité) ---
topN = 20
count_reco_top = count_reco.head(topN)

fig3 = px.bar(
    count_reco_top,
    x="RECOMMENDATION_ID",
    y="count",
    text= count_reco_top["pct"].round(1).astype(str) + "%",
    title=f"Répartition RECO (Top {topN})"
)
fig3.update_layout(xaxis={'categoryorder':'total descending'})
fig3.update_traces(textposition="outside")
st.plotly_chart(fig3, use_container_width=True)

# --- Sunburst hiérarchique (cat1 → cat2 → cat3) ---
if not isinstance(df, pd.DataFrame):
    df_pd = df.to_pandas()  # obligatoire pour Plotly
else:
    df_pd = df.copy()

# Forcer les colonnes utilisées par sunburst à être des chaînes
for col in ["objectif", "sous_objectif", "RECOMMENDATION_ID"]:
    df_pd[col] = df_pd[col].astype(str)

# Supprimer les lignes avec None / NaN (optionnel mais sûr)
df_pd = df_pd.dropna(subset=["objectif", "sous_objectif", "RECOMMENDATION_ID"])

# Créer le sunburst
fig4 = px.sunburst(
    df_pd,
    path=["objectif", "sous_objectif", "RECOMMENDATION_ID"],
    title="Vue hiérarchique"
)

# Affichage Streamlit
st.plotly_chart(fig4, use_container_width=True)