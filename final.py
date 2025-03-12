import streamlit as st
import pandas as pd
from ortools.linear_solver import pywraplp
from fpdf import FPDF

def create_schedule(profs, cours, salles, cours_heures, profs_dispo):
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        st.error("Erreur: Impossible de créer le solveur GLOP")
        return None

    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    heures = list(range(8, 19))  # De 8h à 18h

    # Variables de décision : X[p, c, s, j, h] = 1 si le cours c est donné par p en salle s, jour j, heure h
    X = {}
    for p in profs:
        for c in cours:
            for s in salles:
                for j in jours:
                    for h in heures:
                        X[p, c, s, j, h] = solver.NumVar(0, 1, f'X_{p}_{c}_{s}_{j}_{h}')

    # ✅ Contrainte 1 : Un prof ne peut pas être programmé sur plusieurs cours en même temps
    for p in profs:
        for j in jours:
            for h in heures:
                solver.Add(sum(X[p, c, s, j, h] for c in cours for s in salles) <= 1)

    # ✅ Contrainte 2 : Chaque cours doit être enseigné sur toute sa durée
    for c in cours:
        required_hours = cours_heures[c]  # Durée du cours (3 à 6 heures)
        solver.Add(sum(X[p, c, s, j, h] for p in profs for s in salles for j in jours for h in heures) == required_hours)

    # ✅ Contrainte 3 : Un prof ne doit enseigner que lorsqu'il est disponible
    for p in profs:
        for c in cours:
            if p in profs_dispo:
                for j in jours:
                    if j not in profs_dispo[p]:  # Si le prof n'est pas dispo ce jour-là, on bloque les cours
                        for s in salles:
                            for h in heures:
                                solver.Add(X[p, c, s, j, h] == 0)

    # ✅ Fonction objectif : Minimiser les heures totales utilisées
    solver.Minimize(sum(X[p, c, s, j, h] for p in profs for c in cours for s in salles for j in jours for h in heures))

    # Résolution du problème
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        emploi_temps = []
        for j in jours:
            for h in heures:
                if h == 13:  # Pause déjeuner
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


# === Interface Streamlit ===
st.title("📅 Générateur d'Emploi du Temps Automatisé IFRI-UAC")

nb_cours = st.number_input("Nombre de cours", min_value=1, max_value=10, step=1)
nb_profs = st.number_input("Nombre de professeurs", min_value=1, max_value=10, step=1)
nb_salles = st.number_input("Nombre de salles", min_value=1, max_value=10, step=1)

# Saisie des cours et de leur durée
cours = []
cours_heures = {}
for i in range(nb_cours):
    cours_name = st.text_input(f"Nom du cours {i+1}")
    cours_duree = st.slider(f"Durée du cours {cours_name} (heures)", 3, 6, 3)
    cours.append(cours_name)
    cours_heures[cours_name] = cours_duree

# Saisie des professeurs et de leur disponibilité
profs = []
profs_dispo = {}
for i in range(nb_profs):
    prof_name = st.text_input(f"Nom du professeur {i+1}")
    jours_dispo = st.multiselect(f"Jours disponibles pour {prof_name}", ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'])
    profs.append(prof_name)
    profs_dispo[prof_name] = jours_dispo

# Saisie des salles
salles = [st.text_input(f"Nom de la salle {i+1}") for i in range(nb_salles)]

# Bouton de génération
if st.button("🛠 Générer l'Emploi du Temps"):
    emploi_temps = create_schedule(profs, cours, salles, cours_heures, profs_dispo)
    if emploi_temps is not None:
        st.write("### 📌 Emploi du Temps Généré")
        st.dataframe(emploi_temps)
        pdf_file = generate_pdf(emploi_temps)
        with open(pdf_file, "rb") as f:
            st.download_button("Télécharger l'Emploi du Temps en PDF", f, file_name=pdf_file)

st.markdown("<br><br><br><br><br><br><br><br>", unsafe_allow_html=True)

st.write("##### Plateforme de gestion d'emploi du temps automatisé réalisé au cours Recherche et Optimisation (RO) Groupe 13 M1: 2024-2025")
st.write("#### Sous la supervision du DR Ratheil HOUNDJI")

st.write(" Réalisé par:")
st.write("##### 📌 AGONMA Singbo Davy GL (0154073727)")
st.write("##### 📌 AGUESSY Adékoun-Ibidou  Gloria Ambroisine SIRI")
st.write("##### 📌 EstOmps GL")
st.write("##### 📌 AGBELETE Wilfried SIRI")
st.write("##### 📌 Owen GL")
