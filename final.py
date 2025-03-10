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
    heures = [(8, 10), (10.25, 12.25), (14, 16)]  # Créneaux horaires
    
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
                                emploi_temps.append([j, f"{int(h[0])}h-{int(h[1])}h", c, p, s])
        return pd.DataFrame(emploi_temps, columns=['Jour', 'Heure', 'Cours', 'Professeur', 'Salle'])
    else:
        st.error("Aucune solution optimale trouvée")
        return None

def generate_pdf(emploi_temps):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(200, 10, "INSTITUT DE FORMATION ET DE RECHERCHE EN INFORMATIQUE", ln=True, align='C')
    pdf.cell(200, 10, "MASTER 1 EN GENIE LOGICIEL - SECURITE INFORMATIQUE - SYSTEME D'INFORMATION ET RESEAUX INFORMATIQUES", ln=True, align='C')
    pdf.cell(200, 10, "SEMAINE DU 10 AU 15 MARS 2025", ln=True, align='C')
    pdf.cell(200, 10, "SALLE DE COURS : EN LIGNE/PRESENTIELLE EN ZONE MASTER A2-1/2", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", style='B', size=10)
    column_widths = [40, 35, 35, 35, 35, 35]
    header = ["Heure", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    for col, width in zip(header, column_widths):
        pdf.cell(width, 10, col, border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    horaires = [("08:00-10:00"), ("10:15-12:15"), ("12:15-14:00"), ("14:00-16:00")]
    for h in horaires:
        pdf.cell(40, 10, h, border=1, align='C')
        for j in header[1:]:
            cours_info = emploi_temps.loc[(emploi_temps['Jour'] == j) & (emploi_temps['Heure'] == h)]
            texte = "\n".join([f"{row['Cours']} ({row['Professeur']} - {row['Salle']})" for _, row in cours_info.iterrows()])
            pdf.cell(35, 10, texte if texte else "PAUSE" if "12:15-14:00" in h else "", border=1, align='C')
        pdf.ln()
    
    pdf_output = "emploi_temps.pdf"
    pdf.output(pdf_output)
    return pdf_output

st.title("Générateur d'Emploi du Temps Automatisé")

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


