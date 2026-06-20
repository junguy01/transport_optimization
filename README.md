# transport_optimization
Application Project Master Data Science HAW Kiel SoSe26

## Dashboard aufrufen
`pip install -r requirements.txt`

`streamlit run app.py`


# Notebook Übersicht:

Cleaning_EMR_CIS.ipynb:	-Cleaning EMR Daten, Cleaning CIS Daten, Zuordnung der Tournummern zu EMR Daten, Analyse reine EMR Daten, Analyse Sinnhaftigkeit reine CIS Daten (Miri, ab Pivotisierung Julia)

#### Miri
Analyse_Standzeiten.ipynb: -Standzeitenanalyse mit Geofence

analyse_fahrerverhalten.ipynb: -Standzeitenanalyse auf Basis der pivotisierten EMR Daten, misst Klickverhalten der Fahrer in App

Standzeiten_Soll_Ist.ipynb: -Visualisierungen der Standzeiten 

#### Julia
analyze_CIS.ipynb: -Erste Erschließung der CIS-Daten.xlsx (Soll-Daten)
analyse_routenabweichung_stopabdeckung.ipynb: -Routenabweichung, Stoppabdeckung, Cleaning PRC und Tournummernzuordnung PRC

tourenkarte_soll_emr_alle.ipynb: -Karte EMR vs. Soll, HTML Export war zu groß zum Hochladen 

tourenkarte_soll_prc.ipynb: -Karte PRC vs. Soll, HTML Export war zu groß zum Hochladen 