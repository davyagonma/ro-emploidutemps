import streamlit as st
import pandas as pd
from ortools.linear_solver import pywraplp
from fpdf import FPDF

def create_schedule(profs, cours, salles):
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        st.error("Erreur: Impossible de créer le solveur GLOP")
        return None
    
    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    heures = list(range(8, 20))
    
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
                                emploi_temps.append([j, f"{h}h - {h+1}h", c, p, s])
        return pd.DataFrame(emploi_temps, columns=['Jour', 'Heure', 'Cours', 'Professeur', 'Salle'])
    else:
        st.error("Aucune solution optimale trouvée")
        return None

def generate_pdf(emploi_temps):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style='', size=12)
    pdf.cell(200, 10, "Emploi du Temps", ln=True, align='C')
    pdf.ln(10)
    for index, row in emploi_temps.iterrows():
        pdf.cell(200, 10, f"{row['Jour']} - {row['Heure']} : {row['Cours']} ({row['Professeur']}, {row['Salle']})", ln=True)
    pdf_output = "emploi_temps.pdf"
    pdf.output(pdf_output)
    return pdf_output

st.title("Générateur d'Emploi du Temps Automatisé (Groupe 13)")

nb_cours = st.number_input("Nombre de cours", min_value=1, max_value=10, step=1)
nb_profs = st.number_input("Nombre de professeurs", min_value=1, max_value=10, step=1)
nb_salles = st.number_input("Nombre de salles", min_value=1, max_value=10, step=1)

cours = [st.text_input(f"Nom du cours {i+1}") for i in range(nb_cours)]
profs = [st.text_input(f"Nom du professeur {i+1}") for i in range(nb_profs)]
salles = [st.text_input(f"Nom de la salle {i+1}") for i in range(nb_salles)]

if st.button("Générer l'Emploi du Temps"):
    emploi_temps = create_schedule(profs, cours, salles)
    if emploi_temps is not None:
        st.write("### Emploi du Temps Généré")
        st.dataframe(emploi_temps)
        pdf_file = generate_pdf(emploi_temps)
        with open(pdf_file, "rb") as f:
            st.download_button("Télécharger l'Emploi du Temps en PDF", f, file_name=pdf_file)
