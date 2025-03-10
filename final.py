import streamlit as st
import pandas as pd
from ortools.linear_solver import pywraplp
from fpdf import FPDF

# Fonction de génération d'emploi du temps

def create_schedule(profs, cours, salles):
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        st.error("Erreur: Impossible de créer le solveur GLOP")
        return None
    
    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
    heures = [(8, 10), (10, 12), (14, 16)]  # Créneaux horaires
    
    X = {}
    for p in profs:
        for c in cours:
            for s in salles:
                for j in jours:
                    for h in heures:
                        X[p, c, s, j, h] = solver.NumVar(0, 1, f'X_{p}_{c}_{s}_{j}_{h}')
    
    for p in profs:
        for j in jours:
            for h in heures:
                solver.Add(sum(X[p, c, s, j, h] for c in cours for s in salles) <= 1)
    
    for c in cours:
        solver.Add(sum(X[p, c, s, j, h] for p in profs for s in salles for j in jours for h in heures) >= 1)
    
    solver.Minimize(sum(X[p, c, s, j, h] for p in profs for c in cours for s in salles for j in jours for h in heures))
    status = solver.Solve()
    
    if status == pywraplp.Solver.OPTIMAL:
        emploi_temps = []
        for j in jours:
            for h in heures:
                for p in profs:
                    for c in cours:
                        for s in salles:
                            if X[p, c, s, j, h].solution_value() > 0.5:
                                emploi_temps.append([f"{h[0]}h-{h[1]}h", j, c, p, s])
        return emploi_temps
    else:
        st.error("Aucune solution optimale trouvée")
        return None

# Fonction de génération de PDF

def generate_pdf(emploi_temps):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style='', size=12)
    
    pdf.image("logo_gauche.png", 10, 8, 33)
    pdf.image("logo_droite.png", 160, 8, 33)
    
    pdf.cell(200, 10, "INSTITUT DE FORMATION ET DE RECHERCHE EN INFORMATIQUE", ln=True, align='C')
    pdf.cell(200, 10, "MASTER 1 - GENIE LOGICIEL - SECURITE INFORMATIQUE", ln=True, align='C')
    pdf.cell(200, 10, "SEMAINE DU 10 AU 15 MARS 2025", ln=True, align='C')
    pdf.cell(200, 10, "SALLE DE COURS : EN LIGNE/PRESENTIELLE", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10)
    pdf.cell(30, 10, "Heure", border=1)
    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
    for jour in jours:
        pdf.cell(40, 10, jour, border=1)
    pdf.ln()
    
    horaires = ["08:00-10:00", "10:15-12:15", "14:00-16:00"]
    emploi_dict = {h: {j: "" for j in jours} for h in horaires}
    
    for h, j, c, p, s in emploi_temps:
        emploi_dict[h][j] = f"{c} ({p} - {s})"
    
    for h in horaires:
        pdf.cell(30, 10, h, border=1)
        for j in jours:
            pdf.cell(40, 10, emploi_dict[h][j], border=1)
        pdf.ln()
    
    pdf_file = "emploi_temps.pdf"
    pdf.output(pdf_file)
    return pdf_file

# Interface Streamlit

st.title("Générateur d'Emploi du Temps Automatisé (Groupe 13)")

nb_cours = st.number_input("Nombre de cours", min_value=1, max_value=10, step=1)
nb_profs = st.number_input("Nombre de professeurs", min_value=1, max_value=10, step=1)
nb_salles = st.number_input("Nombre de salles", min_value=1, max_value=10, step=1)

cours = [st.text_input(f"Nom du cours {i+1}") for i in range(nb_cours)]
profs = [st.text_input(f"Nom du professeur {i+1}") for i in range(nb_profs)]
salles = [st.text_input(f"Nom de la salle {i+1}") for i in range(nb_salles)]

if st.button("Générer l'Emploi du Temps"):
    emploi_temps = create_schedule(profs, cours, salles)
    if emploi_temps:
        emploi_df = pd.DataFrame(emploi_temps, columns=['Heure', 'Jour', 'Cours', 'Professeur', 'Salle'])
        st.write("### Emploi du Temps Généré")
        st.dataframe(emploi_df)
        pdf_file = generate_pdf(emploi_temps)
        with open(pdf_file, "rb") as f:
            st.download_button("Télécharger l'Emploi du Temps en PDF", f, file_name=pdf_file)
