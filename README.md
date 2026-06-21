# transport_optimization
Application Project Master Data Science HAW Kiel SoSe26

# Notebook Übersicht:
Hinweis: Falls die Notebooks nochmal ausgeführt werden müssen, sollten die Dateipfade der eingelesenen Dateien geändert werden, weil es jetzt einen `Daten` Ordner gibt. 

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

#### Jonas 
- Soll_Cis_final.ipynb - bereitet die CIS-Soll-Plandaten auf.
- Ist_EMR_final.ipynb - bereitet die EMR-Telematik (SPEDION-Fahrer-App) auf.
- Ist_PRC_final.ipynb - konsolidiert die PRC-Telematik (XML-Exporte der Fahrzeugbox).
- finale_analyse.ipynb - führt Soll, EMR und PRC im Soll-Ist-Verbund zusammen und leitet die vier Ist-Kennzahlen ab (Reihenfolge, Re-Disposition, Zeitabweichung, Standzeit).

Die drei Quell-Notebooks müssen vor finale_analyse durchgelaufen sein.