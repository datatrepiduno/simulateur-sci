import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration de la page
st.set_page_config(page_title="Simulateur SCI Expert", layout="wide", initial_sidebar_state="expanded")

# CSS personnalisé
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; font-weight: 700; color: #1f77b4; margin-bottom: 1rem;}
    .sub-header {font-size: 1.3rem; font-weight: 600; color: #2c3e50; margin-top: 1.5rem;}
    .metric-card {background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">📊 Simulateur SCI : Analyse Comparative IR vs IS</p>', unsafe_allow_html=True)

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.markdown("### 🏗️ Projet & Acquisition")
    prix_achat = st.number_input("Prix d'achat FAI (€)", value=640000.0, step=10000.0, format="%0.0f")
    tx_notaire = st.number_input("Frais de Notaire (%)", value=8.3, step=0.1, format="%.1f") / 100
    travaux = st.number_input("Travaux Initiaux (€)", value=0.0, step=5000.0, format="%0.0f")
    frais_bancaires = st.number_input("Frais bancaires (€)", value=2000.0, step=100.0, format="%0.0f")
    apport = st.number_input("Apport Personnel (€)", value=100000.0, step=5000.0, format="%0.0f")

    st.markdown("---")
    st.markdown("### 🏦 Financement")
    duree_pret = st.slider("Durée du prêt (années)", 5, 30, 25)
    taux_interet = st.number_input("Taux d'Intérêt annuel (%)", value=3.6, step=0.1, format="%.2f") / 100
    assurance_tx = st.number_input("Assurance emprunteur (%)", value=0.5, step=0.05, format="%.2f") / 100

    st.markdown("---")
    st.markdown("### 📈 Exploitation")
    loyer_hc_annuel_saisi = st.number_input("Loyer HC annuel (€)", value=51000.0, step=1000.0, format="%0.0f")
    revalorisation = st.number_input("Revalorisation loyer annuelle (%)", value=1.0, step=0.1, format="%.1f") / 100
    vacance = st.number_input("Vacance locative (%)", value=5.0, step=1.0, format="%.1f") / 100
    taxe_fonciere = st.number_input("Taxe Foncière annuelle (€)", value=4500.0, step=100.0, format="%0.0f")
    frais_gestion_pct = st.number_input("Frais de gestion (%)", value=10.0, step=0.5, format="%.1f") / 100
    compta_is = st.number_input("Honoraires Expert Comptable IS (€/an)", value=1200.0, step=100.0, format="%0.0f")
    
    st.markdown("---")
    st.markdown("### ⚖️ Fiscalité")
    tmi = st.selectbox("Votre TMI (%)", [0, 11, 30, 41, 45], index=2) / 100
    ps_applicable = st.checkbox("Soumis aux Prélèvements Sociaux (17.2%)", value=True)

# --- CALCULS ---
frais_notaire_eur = prix_achat * tx_notaire
total_projet = prix_achat + frais_notaire_eur + travaux + frais_bancaires
montant_emprunt = max(0.0, total_projet - apport)

if montant_emprunt > 0:
    r, n = taux_interet / 12, duree_pret * 12
    mens_credit = (montant_emprunt * r) / (1 - (1 + r)**-n) if r > 0 else montant_emprunt / n
    mens_assu = (montant_emprunt * assurance_tx) / 12
else:
    mens_credit = mens_assu = 0.0

base_immo = prix_achat * 0.90
amort_an = (base_immo * 0.54 / 35) + (base_immo * 0.09 / 20) + (base_immo * 0.14 / 15) + (base_immo * 0.14 / 10)
tx_ps = 0.172 if ps_applicable else 0.0

# --- PROJECTION ---
data_ir, data_is = [], []
solde_emp = montant_emprunt
stock_def_is = 0.0
cumul_cf_ir = cumul_cf_is = 0.0

for year in range(1, 31):
    loyer_an = loyer_hc_annuel_saisi * ((1 + revalorisation)**(year-1)) * (1 - vacance)
    ch_exploit_base = (loyer_an * frais_gestion_pct) + taxe_fonciere
    
    if year <= duree_pret:
        int_an = solde_emp * taux_interet
        assu_an = mens_assu * 12
        cap_remb = (mens_credit * 12) - int_an
        solde_emp = max(0.0, solde_emp - cap_remb)
        mens_totale = (mens_credit * 12) + assu_an
    else:
        int_an = assu_an = cap_remb = solde_emp = mens_totale = 0.0

    # SCI IR
    res_fonc = loyer_an - ch_exploit_base - assu_an - int_an
    impot_ir = max(0.0, res_fonc * (tmi + tx_ps))
    cf_ir = loyer_an - mens_totale - ch_exploit_base - impot_ir
    cumul_cf_ir += cf_ir
    data_ir.append({"Année": year, "Loyer": loyer_an, "Charges": ch_exploit_base + assu_an, "Intérêts": int_an, "Capital": cap_remb, "Impôt": impot_ir, "Cashflow": cf_ir, "Cumul": cumul_cf_ir})

    # SCI IS
    res_is = loyer_an - ch_exploit_base - assu_an - int_an - compta_is - amort_an
    if res_is < 0:
        stock_def_is += abs(res_is)
        base_is = 0.0
    else:
        base_is = max(0.0, res_is - stock_def_is)
        stock_def_is = max(0.0, stock_def_is - res_is)
    impot_is = (min(base_is, 42500) * 0.15) + (max(0, base_is - 42500) * 0.25)
    cf_is = loyer_an - mens_totale - ch_exploit_base - compta_is - impot_is
    cumul_cf_is += cf_is
    data_is.append({"Année": year, "Loyer": loyer_an, "Charges": ch_exploit_base + assu_an + compta_is, "Intérêts": int_an, "Capital": cap_remb, "Impôt": impot_is, "Cashflow": cf_is, "Cumul": cumul_cf_is})

df_ir, df_is = pd.DataFrame(data_ir), pd.DataFrame(data_is)

# --- KPI DASHBOARD ---
st.markdown('<p class="sub-header">📌 Indicateurs Clés du Projet</p>', unsafe_allow_html=True)
def fmt_eur(val): return f"{val:,.0f} €".replace(",", " ")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💰 Prix d'achat FAI", fmt_eur(prix_achat))
    st.metric("🏗️ Coût total Projet", fmt_eur(total_projet))
with col2:
    st.metric("💳 Apport personnel", fmt_eur(apport))
    st.metric("📊 Taux d'apport", f"{(apport/total_projet*100):.1f}%")
with col3:
    st.metric("🏦 Montant emprunté", fmt_eur(montant_emprunt))
    st.metric("⏱️ Durée du prêt", f"{duree_pret} ans")
with col4:
    st.metric("💵 Mensualité totale", fmt_eur(mens_credit + mens_assu))
    st.metric("📈 Amort. annuel IS", fmt_eur(amort_an))

# --- GRAPHIQUES ET ONGLETS ---
st.markdown("---")
st.markdown('<p class="sub-header">📈 Analyse Graphique sur 30 ans</p>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["💰 Cashflow Détaillé", "📊 Cumuls", "💡 Décomposition Fiscale"])

with tab1:
    fig1 = go.Figure()
    # Barres superposées
    fig1.add_trace(go.Bar(x=df_is["Année"], y=df_is["Loyer"], name="Loyers annuels", marker_color='rgba(40, 167, 69, 0.4)'))
    fig1.add_trace(go.Bar(x=df_is["Année"], y=-df_is["Charges"], name="Charges annuelles", marker_color='orange'))
    fig1.add_trace(go.Bar(x=df_is["Année"], y=-df_is["Intérêts"], name="Intérêts annuels", marker_color='red'))
    fig1.add_trace(go.Bar(x=df_is["Année"], y=-df_is["Capital"], name="Remboursement Capital", marker_color='blue'))
    
    # Courbes MODIFIÉES : plus fines, mode lines+markers et nouvelles couleurs
    fig1.add_trace(go.Scatter(x=df_ir["Année"], y=df_ir["Cashflow"], name="Net IR", mode='lines+markers', line=dict(color='purple', width=2), marker=dict(size=6)))
    fig1.add_trace(go.Scatter(x=df_is["Année"], y=df_is["Cashflow"], name="Net IS", mode='lines+markers', line=dict(color='black', width=2), marker=dict(size=6)))
    
    fig1.update_layout(barmode='relative', height=550, hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_ir["Année"], y=df_ir["Cumul"], name="Cumul IR", fill='tozeroy', line=dict(color='purple')))
    fig2.add_trace(go.Scatter(x=df_is["Année"], y=df_is["Cumul"], name="Cumul IS", fill='tozeroy', line=dict(color='black')))
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    fig3 = make_subplots(rows=1, cols=2, subplot_titles=("Composantes IR", "Composantes IS"))
    fig3.add_trace(go.Bar(x=df_ir["Année"], y=df_ir["Loyer"], name="Loyers", marker_color='lightgreen'), row=1, col=1)
    fig3.add_trace(go.Bar(x=df_ir["Année"], y=-df_ir["Impôt"], name="Impôts IR+PS", marker_color='purple'), row=1, col=1)
    fig3.add_trace(go.Bar(x=df_is["Année"], y=df_is["Loyer"], showlegend=False, marker_color='lightgreen'), row=1, col=2)
    fig3.add_trace(go.Bar(x=df_is["Année"], y=-df_is["Impôt"], name="Impôts IS", marker_color='black'), row=1, col=2)
    st.plotly_chart(fig3, use_container_width=True)

# --- TABLEAUX ---
st.markdown('<p class="sub-header">📅 Simulations Détaillées</p>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown("**🟣 SCI à l'IR**")
    st.dataframe(df_ir.style.format("{:,.0f} €", subset=df_ir.columns[1:]), height=400)
with c2:
    st.markdown("**⚫ SCI à l'IS**")
    st.dataframe(df_is.style.format("{:,.0f} €", subset=df_is.columns[1:]), height=400)

# Comparaison finale
diff = cumul_cf_is - cumul_cf_ir
if diff > 0:
    st.success(f"✅ L'IS est plus avantageux de {fmt_eur(diff)} sur 30 ans en termes de trésorerie cumulée.")
else:
    st.info(f"ℹ️ L'IR est plus avantageux de {fmt_eur(abs(diff))} sur 30 ans en termes de trésorerie cumulée.")
