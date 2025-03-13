import streamlit as st
import pandas as pd
from ortools.linear_solver import pywraplp
from fpdf import FPDF

def create_schedule(profs, cours, salles, cours_heures, profs_dispo):
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        st.error("Erreur: Impossible de créer le solveur SCIP")
        return None

    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    heures = list(range(8, 19))  # Plages horaires de 8h à 18h

    # Variables de décision : X[p, c, s, j, h] = 1 si le cours c est donné par p en salle s, jour j, heure h
    X = {}
    for p in profs:
        for c in cours:
            for s in salles:
                for j in jours:
                    for h in heures:
                        X[p, c, s, j, h] = solver.BoolVar(f'X_{p}_{c}_{s}_{j}_{h}')

    # ✅ Contrainte 1 : Un prof ne peut pas être assigné à plusieurs cours en même temps
    for p in profs:
        for j in jours:
            for h in heures:
                solver.Add(sum(X[p, c, s, j, h] for c in cours for s in salles) <= 1)

    # ✅ Contrainte 2 : Un cours doit être enseigné pendant le nombre exact d'heures requis
    for c in cours:
        required_hours = cours_heures[c]
        solver.Add(sum(X[p, c, s, j, h] for p in profs for s in salles for j in jours for h in heures) == required_hours)

    # ✅ Contrainte 3 : Un prof ne peut enseigner que durant ses disponibilités
    for p in profs:
        if p in profs_dispo:
            for j in jours:
                if j not in profs_dispo[p]:  # Si le prof n'est pas disponible ce jour-là
                    for c in cours:
                        for s in salles:
                            for h in heures:
                                solver.Add(X[p, c, s, j, h] == 0)

    # ✅ Fonction objectif : Minimiser le nombre total d'heures inutilisées
    solver.Minimize(sum(X[p, c, s, j, h] for p in profs for c in cours for s in salles for j in jours for h in heures))

    # Résolution du problème
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        emploi_temps = []
        for j in jours:
            for p in profs:
                for c in cours:
                    for s in salles:
                        for h in heures:
                            if X[p, c, s, j, h].solution_value() > 0.5:
                                emploi_temps.append([j, f"{h}h - {h+1}h", c, p, s])
                                if h == 13:  # Pause déjeuner
                                    emploi_temps.append([j, f"{h}h - {h+1}h", "PAUSE DÉJEUNER", "", ""])
        return pd.DataFrame(emploi_temps, columns=['Jour', 'Heure', 'Cours', 'Professeur', 'Salle'])
    else:
        st.error("Aucune solution optimale trouvée")
        return None

from fpdf import FPDF

from fpdf import FPDF

class EmploiTempsPDF(FPDF):
    def header(self):
        self.set_font("Arial", style='B', size=14)
        self.cell(280, 10, "INSTITUT DE FORMATION ET DE RECHERCHE EN INFORMATIQUE", ln=True, align='C')
        self.cell(280, 10, "MASTER 1 - GENIE LOGICIEL - SECURITE INFORMATIQUE", ln=True, align='C')
        self.cell(280, 10, "SEMAINE DU 10 AU 15 MARS 2025", ln=True, align='C')
        self.cell(280, 10, "SALLE DE COURS : EN LIGNE/PRESENTIELLE", ln=True, align='C')
        self.ln(10)

def generate_pdf(emploi_temps):
    pdf = EmploiTempsPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Jours et heures
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
    heures = list(range(8, 19))

    # Entête du tableau
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(40, 10, "Heure/Jour", border=1, fill=True, align="C")
    for j in jours:
        pdf.cell(40, 10, j, border=1, fill=True, align="C")
    pdf.ln()

    # Construction du tableau
    for h in heures:
        pdf.cell(40, 10, f"{h}h - {h+1}h", border=1, align="C")  # Colonne des heures

        for j in jours:
            # Récupérer les informations du cours
            cours_info = emploi_temps[(emploi_temps["Jour"] == j) & (emploi_temps["Heure"].str.startswith(f"{h}h"))]
            
            if not cours_info.empty:
                row = cours_info.iloc[0]
                cours = row['Cours']
                prof = row['Professeur']
                salle = row['Salle']
                texte = f"{cours}\n{prof}\n({salle})"
            else:
                texte = ""  # Case vide

            pdf.multi_cell(40, 10, texte, border=1, align="C")  # Affichage sans fusion

        pdf.ln()

    # Sauvegarde
    pdf_output = "emploi_temps_corrige.pdf"
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

st.markdown("<br><br><br>", unsafe_allow_html=True)
st.write("##### Plateforme réalisée pour la Recherche Opérationnelle (RO) - M1 2024-2025")
st.write("#### Sous la supervision du DR Ratheil HOUNDJI")

st.write(" Réalisé par:")
st.write("📌 AGONMA Singbo Davy (GL)")
st.write("📌 AGUESSY Adékoun-Ibidou Gloria Ambroisine (SIRI)")
st.write("📌 ATTINDOGBE E. Emmanuel (SIRI)")
st.write("📌 AGBELETE Wilfried (SIRI)")
st.write("📌 DAN Yannick (GL)")
