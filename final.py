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
    heures = list(range(8, 19))
    
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
                if h == 13:
                    emploi_temps.append([j, f"{h}h - {h+1}h", "PAUSE DÉJEUNER", "", ""])
                else:
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
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=14)

    #pdf.image("logo_gauche.png", 10, 8, 33)
    #pdf.image("logo_droite.png", 160, 8, 33)
    
    pdf.cell(200, 10, "INSTITUT DE FORMATION ET DE RECHERCHE EN INFORMATIQUE", ln=True, align='C')
    pdf.cell(200, 10, "MASTER 1 - GENIE LOGICIEL - SECURITE INFORMATIQUE", ln=True, align='C')
    pdf.cell(200, 10, "SEMAINE DU 10 AU 15 MARS 2025", ln=True, align='C')
    pdf.cell(200, 10, "SALLE DE COURS : EN LIGNE/PRESENTIELLE", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(40, 10, "Jour", border=1, fill=True)
    pdf.cell(40, 10, "Heure", border=1, fill=True)
    pdf.cell(70, 10, "Cours", border=1, fill=True)
    pdf.cell(70, 10, "Professeur", border=1, fill=True)
    pdf.cell(50, 10, "Salle", border=1, fill=True)
    pdf.ln()
    
    for index, row in emploi_temps.iterrows():
        if "PAUSE" in row['Cours']:
            pdf.set_fill_color(255, 200, 200)  # Rouge clair pour les pauses
        else:
            pdf.set_fill_color(255, 255, 255)  # Blanc pour les cours
        pdf.cell(40, 10, row['Jour'], border=1, fill=True)
        pdf.cell(40, 10, row['Heure'], border=1, fill=True)
        pdf.cell(70, 10, row['Cours'], border=1, fill=True)
        pdf.cell(70, 10, row['Professeur'], border=1, fill=True)
        pdf.cell(50, 10, row['Salle'], border=1, fill=True)
        pdf.ln()
    
    pdf_output = "emploi_temps.pdf"
    pdf.output(pdf_output)
    return pdf_output

st.title("Générateur d'Emploi à l'IFRI (Groupe 13)")

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

