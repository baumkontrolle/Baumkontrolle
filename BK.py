from pandas.io.formats import style
import streamlit as st
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import date
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from folium.plugins import LocateControl
import tempfile
import requests
import json
import base64
import io
from io import BytesIO  
from PIL import Image
import os
import uuid



# --- 1. SETZE DEINEN MAPBOX TOKEN HIER EIN ---
MAPBOX_TOKEN = st.secrets["MAPBOX_TOKEN"]


def get_satellite_image(lat, lon, zoom=18):
    # Den Style explizit als String definieren
    style_id = "mapbox/satellite-v9"
    marker = f"pin-s+ff0000({lon},{lat})"
    
    # URL ohne das Token am Ende zusammenbauen (wird via params sauber angehängt)
    url = f"https://api.mapbox.com/styles/v1/{style_id}/static/{marker}/{lon},{lat},{zoom},0/600x400"

    params = {
        "access_token": MAPBOX_TOKEN
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            st.error(f"Mapbox API Fehler {response.status_code}: {response.text}")
            return None
    except Exception as e:
        st.error(f"Netzwerkfehler: {e}")
        return None
    
# --- 2. PDF-ERSTELLUNG FUNKTION ---
def create_pdf(data, image_file=None, logo_file=None, map_image_stream=None):
    pdf = FPDF()
    temp_files = []
    # ==============
    # Page & Margin
    # ==============
    LEFT_MARGIN = 17.8
    RIGHT_MARGIN = 17.8
    TOP_MARGIN = 19.1
    BOTTOM_MARGIN = 19.1

    PAGE_WIDTH = 210
    PAGE_HEIGHT = 297

    CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

    pdf.set_margins(
    left=LEFT_MARGIN,
    top=TOP_MARGIN,
    right=RIGHT_MARGIN
    )

    pdf.set_auto_page_break(
        auto=True,
        margin=BOTTOM_MARGIN
        )
    
    pdf.add_page()
    
    y_posisi = TOP_MARGIN
    logo_breite = 40
    
    # --- HEADER: LOGO & FIRMENINFO ---
    if logo_file is not None:
        try:
            img = Image.open(logo_file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                img.save(tmp.name, format="JPEG")
                tmp_path = tmp.name

            temp_files.append(tmp_path)

            pdf.image(tmp_path,
                x=PAGE_WIDTH - RIGHT_MARGIN - logo_breite,
                y=y_posisi,
                w=logo_breite
                )
                
            os.unlink(tmp_path)

        except Exception as e:
            print(f"Logo-Fehler: {e}")
    
    # Firmeninfos links vom Logo
    pdf.set_xy(LEFT_MARGIN, TOP_MARGIN)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_font("Helvetica", "", 10)
    text_box_breite = (
        PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - logo_breite - 3
    )
    
    pdf.cell(text_box_breite, 5, data.get("Firmennamen", "Mein Unternehmen"), new_x=XPos.LEFT, new_y=YPos.NEXT, align="R")
    pdf.cell(text_box_breite, 5, data.get("Firmenadresse", ""), new_x=XPos.LEFT, new_y=YPos.NEXT, align="R")
    pdf.cell(text_box_breite, 5, data.get("Email Perusahaan", ""), new_x=XPos.LEFT, new_y=YPos.NEXT, align="R")
    pdf.cell(text_box_breite, 5, data.get("Telefonnummer", ""), new_x=XPos.LEFT, new_y=YPos.NEXT, align="R")

    # --- TITEL ---
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Baumkontrolle (VTA I) nach FLL-Richtlinien", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    
    # --- KUNDENDATEN ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Kundendaten", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.line(LEFT_MARGIN,
             pdf.get_y(),
             PAGE_WIDTH - RIGHT_MARGIN,
             pdf.get_y()
             )
    
    pdf.ln(3)

    kundendaten_felder = [("Datum", "Kontroldatum"), ("Kunde", "Kunde"), ("Adresse", "Adresse")]
    for label, key in kundendaten_felder:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(30, 8, f"{label}:") 
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, str(data.get(key, "-")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # --- BAUMDATEN ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Baumdaten", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.line(LEFT_MARGIN,
             pdf.get_y(),
             PAGE_WIDTH - RIGHT_MARGIN,
             pdf.get_y()
             )
    
    pdf.ln(3)

    y_start_baum = pdf.get_y()
    # Linke Spalte
    kiri = [("Baum-ID", "Baum-ID"), ("Baumart", "Baumart"), ("Standort", "Standort")]
    for label, key in kiri:
        pdf.set_x(LEFT_MARGIN)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(25, 7, f"{label}:")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(60, 7, text=str(data.get(key, "-")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Rechte Spalte
    pdf.set_y(y_start_baum)
    kanan = [("Höhe", "Baumhöhe"), ("Umfang", "Stammumfang"), ("Ø Stamm", "Stammdurchmesser"), ("Ø Krone", "Kronendurchmesser")]
    for label, key in kanan:
        pdf.set_x(125)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(25, 7, f"{label}:")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(60, 7, text=str(data.get(key, "-")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # --- Visuelle Kontrolle ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Visuelle Kontrolle", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.line(LEFT_MARGIN,
             pdf.get_y(),
             PAGE_WIDTH - RIGHT_MARGIN,
             pdf.get_y()
             )
    
    pdf.ln(3)

    def format_list_text(wert):
        if not wert or str(wert).strip() == "-":
            return "Keine gefährliche Visuelle Symptome erkannt"

        if isinstance(wert, str):
            liste = [item.strip() for item in wert.split(",") if item.strip()]
        elif isinstance(wert, list):
            liste = [str(item).strip() for item in wert if str(item).strip()]
        else:
            return f"{str(wert)}"

        return "\n".join(f"- {item}" for item in liste)
    

    Visuelle = [ ("Entwicklungsphase", "Entwicklungsphase"),
        ("Vitalität", "Vitalität"),
        ("Verkehrssicherheit", "Verkehrssicherheit"),
        ]
    
    for label, key in Visuelle:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(55, 7, f"{label}:") 
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, str(data.get(key, "-")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    Kontrolle = [
        ("Visuellesymptome Wurzel", "Visuellesymptome Wurzel"), 
        ("Visuellesymptome Stamm", "Visuellesymptome Stamm"), 
        ("Visuellesymptome Krone", "Visuellesymptome Krone")
        ]
       
    pdf.set_x(LEFT_MARGIN)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 7, "Visuellesymptome Wurzel:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_x(LEFT_MARGIN + 5)
    wert_wurzel = data.get("Visuellesymptome Wurzel", []) or []
    inhalt_wurzel = format_list_text(wert_wurzel)
    pdf.multi_cell(85, 6, inhalt_wurzel, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(2)
    pdf.set_x(LEFT_MARGIN)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 7, "Visuellesymptome Stamm:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_x(LEFT_MARGIN + 5)
    wert_stamm = data.get("Visuellesymptome Stamm", []) or []
    inhalt_stamm = format_list_text(wert_stamm)
    pdf.multi_cell(85, 6, inhalt_stamm, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(2)
    pdf.set_x(LEFT_MARGIN)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 7, "Visuellesymptome Krone:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_x(LEFT_MARGIN + 5)
    wert_krone = data.get("Visuellesymptome Krone", []) or []
    inhalt_krone = format_list_text(wert_krone)
    pdf.multi_cell(85, 7, inhalt_krone, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


        # --- Massnahmen & Empfehlungen ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Massnahmen & Empfehlungen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.line(LEFT_MARGIN,
             pdf.get_y(),
             PAGE_WIDTH - RIGHT_MARGIN,
             pdf.get_y()
             )
    
    pdf.ln(3)

    Massnahmen = [("Kontrollinterval", "Kontrollinterval")]
    for label, key in Massnahmen:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(50, 8, f"{label}:") 
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, text=str(data.get(key, "-")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    Empfehlung = [("Empfohlene Maßnahmen", "Empfohlene Maßnahmen")]

    pdf.set_x(LEFT_MARGIN)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 7, "Empfohlene Maßnahmen:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_x(LEFT_MARGIN + 5)
    wert_Empfehlung = data.get("Empfohlene Maßnahmen", []) or []
    inhalt_Empfehlung = format_list_text(wert_Empfehlung)
    if data.get("Empfohlene Maßnahmen"):
        pdf.multi_cell(85, 7, inhalt_Empfehlung, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else :
        pdf.cell(90, 7, "Keine Maßnahmen erforderlich", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        

     # --- Bemerkungen --- 
    pdf.ln (5) 
    pdf.set_x(LEFT_MARGIN)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Bemerkungen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.line(LEFT_MARGIN,
             pdf.get_y(),
             PAGE_WIDTH - RIGHT_MARGIN,
             pdf.get_y()
             )
    
    pdf.ln(3) 
    pdf.set_font("Helvetica", "", 11)

    if data.get("Bemerkung"):
        pdf.multi_cell(CONTENT_WIDTH, 6, str(data.get("Bemerkung", "-")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else :
        pdf.cell(0, 8, "Keine Angaben", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


  

    # --- Unterschreiben ---
    # unterschreiben sebelah kanan diakhir input bemerkungen
    ttd_path = None

    if ttd_file:
        file_id = str(uuid.uuid4())
        ttd_path = f"ttd_{file_id}.png"

        with open(ttd_path, "wb") as f:
            f.write(ttd_file.getbuffer())

    pdf.ln(15)

    lebar_kolom_ttd = 60
    posisi_x_ttd = PAGE_WIDTH - RIGHT_MARGIN - lebar_kolom_ttd

    pdf.set_x(posisi_x_ttd)
    pdf.set_font("helvetica", "", 10)

    # tanggal
    datum_text = f"Bielefeld, {data.get('Kontroldatum', '-')}"
    pdf.cell(lebar_kolom_ttd, 10, datum_text, new_x=XPos.LEFT, new_y=YPos.NEXT, align="L")

    pdf.ln(20)

    # gambar tanda tangan jika ada
    if ttd_path:
        try:
            pdf.image(ttd_path, x=posisi_x_ttd, y=pdf.get_y() - 20, w=40)
        except Exception as e:
            print("Unterschrift fehlt:", e)

    # garis bawah
    pdf.set_x(posisi_x_ttd)
    pdf.line(posisi_x_ttd, pdf.get_y(), PAGE_WIDTH - RIGHT_MARGIN, pdf.get_y())

    pdf.cell(lebar_kolom_ttd, 5, "Unterschrift Prüfer", new_x=XPos.LEFT, new_y=YPos.NEXT, align="L")


    
    # --- dOKUMENTASION fOTO & STANDORT ---
    if image_file is not None or map_image_stream is not None:
        pdf.add_page()
        
        #Judul halaman Foto
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Dokumentation & Standort", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)

        # menentukan posisi y awal setelah judul
        y_start_foto = pdf.get_y()
        lebar_foto = 90  # Maximalbreite für das Foto

        # Foto-Camera oder Upload
        pdf.set_xy(LEFT_MARGIN, y_start_foto)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(lebar_foto, 8, "Foto des Baumes", align="L")

        try:
                img= Image.open(image_file)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")


                tmp_path = ""
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    img.save(tmp.name, format="JPEG")
                    tmp_path = tmp.name

                temp_files.append(tmp_path)

                pdf.image(tmp_path,
                    x=LEFT_MARGIN,
                    y=y_start_foto + 10,
                    w=lebar_foto
                    )
                    
                os.unlink(tmp_path)

        except Exception as e:
                st.warning(f"Foto konnte nicht in PDF eingebettet werden: {e}")

        # SATELLITENBILD
    if map_image_stream is not None:
        try:
            #pindahkan kursor ke kanan pada y yg sama
            pdf.set_xy(PAGE_WIDTH / 2 + 5,  y_start_foto)  # Etwas rechts neben dem Foto-Titel
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(lebar_foto, 8, "Baumstandort (Satellit)", align="L")

            map_image_stream.seek(0)
            
            # Prüfen, ob es wirklich ein Bild ist
            test_img = Image.open(map_image_stream)
            test_img.verify() # Validiert das Bild
            map_image_stream.seek(0) # Zurücksetzen nach verify()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(map_image_stream.getvalue())
                tmp_path = tmp.name
            
            temp_files.append(tmp_path)

            pdf.image(tmp_path,
                x=PAGE_WIDTH / 2 + 5,
                y=pdf.get_y()+10,
                w=lebar_foto
                )
            
            os.unlink(tmp_path)

        except Exception as e:
            st.warning(f"Kartenbild konnte nicht in PDF eingebettet werden: {e}")
            
        # atur ulang posisi y ke bawah foto agar teks selanjutnya tidak menimpa foto
        pdf.set_y(y_start_foto + 85)  # 15mm Puffer nach dem Foto    
        
    pdf_bytes = pdf.output()

    for file in temp_files:
        try:
            os.unlink(file)
        except:
            pass

    return pdf_bytes

## a. Liste der Bäume
baum_optionen = [
    "Stieleiche (Quercus robur)", "Winterlinde (Tilia cordata)", 
    "Rotbuche (Fagus sylvatica)", "Spitzahorn (Acer platanoides)",
    "Hänge-Birke (Betula pendula)", "Rosskastanie (Aesculus hippocastanum)",
    "Esche (Fraxinus excelsior)", "Kiefer (Waldkiefer) (Pinus sylvestris)", 
    "Traubeneiche (Quercus petraea)", "Hainbuche (Carpinus betulus)",
    "Gemeine Esche (Fraxinus excelsior)", "Schwarz-Erle (Alnus glutinosa)",
    "Europäische Lärche (Larix decidua)","weißtanne (Abies alba)", "Feldahorn (Acer campestre)",
    "Bergahorn (Acer pseudoplatanus)", "Roteiche (Quercus rubra)",
    "Douglasie (Pseudotsuga menziesii)", "Sommerlinde (Tilia platyphyllos)",
    "Silber-weide (Salix alba)", "Eberesche (Sorbus aucuparia)", "Platane (Platanus x hispanica)",
    "Schwarze Pappel (Populus nigra)",  "Zitterpappel (Populus tremula)",
    "Vogelkirsche (Prunus avium)", "Nordmanntanne (Abies nordmanniana)",
    "schwarzkiefer (Pinus nigra)","Thunja (Thuja occidentalis)",
    "Ginkgo (Ginkgo biloba)",
    "Sonstige / Unbekannt"
]

## b. Visuelle Kontrolle (Symptomerkennung)
Wurzelbereich_optionen = [
    "Pilzfruchtkörper", "Risse", "Wurzelanläufe",
    "Pestizid-Aufwölbungen", "Bodenveränderungen", "Stammaustriebe",
    "Abgestorbene Rinden oder Rindenschäden", "Anfahrschäden",
    "Kappungen von Wurzeln", "Würgewurzeln", "Adventivwurzeln",
    "Auffallende Ausformungen", "Bodenrisse (Bodenaufwölbungen)",
    "Insekten", "Baustellen", "Bodenauftrag", "Bodenabtrag",
    "Bodenverdichtung oder Bodenversiegelung", "Keine gefährliche Visuelle Symptome erkannt",
    "Faulstelle", "Beulen / Wulste", "Ausfluss",
    "Stockaustriebe", "Höhlungen", "Wuchsanomalien",
    "Freiliegende Wurzel", "Freiliegende beschädigte Wurzel",
    "Einwalungen",
    ]

Stammbereich_optionen = [
    "Pilzfruchtkörper", 
    "offene Höhlungen",
    "Spechtlöcher", 
    "Fremdkörper", 
    "Rindenverlust", 
    "Blitzrinne",
    "Schrägstand", 
    "Stammsicherungen", 
    "Anfahrschaden", 
    "Astungswunden", 
    "Einwalungen"
    "Zwiesel", 
    "Höhlungen", 
    "Spechlocher / Nisthohlen",
    "Borkenabhebung", 
    "Rindenverletzungen", 
    "Rindenveränderungen", 
    "Rindenveränderungen mit Pilzbefall", 
    "Rindenveränderungen mit Pilzbefall, eingerissen", 
    "Rindenveränderungen mit Pilzbefall, eingerissen und eingefault",
    "Baumfremder Bewuchs", 
    "Stammaustriebe", 
    "Abgestorbene Rinde", 
    "Faulstelle",
    "Leckstellen", 
    "Ausfluss", 
    "Nässende Flecken", 
    "Wülste", 
    "Risse / Rippen", 
    "Beulen",
    "Vergabelung / Zwiesel",
    "Vergabelung / Zwiesel eingefault",
    "Vergabelung / Zwiesel eingewachsene Rinde",
    "Vergabelung / Zwiesel eingerissen",
    "Keine gefährliche Visuelle Symptome erkannt"
]

Kronen_optionen = [
    "Abgestorbene Rinde",
    "Pilzfruchtkörper",
    "Kronendeformationen", 
    "Schädlingsbefall",
    "Zwieselbildung",
    "Totholz",
    "Ausfluss",
    "Astungswunden",
    "Astausbrüche",
    "Wunden (Teil-)überwallt", 
    "Wunden Eingefault", "Eingefaulte Äste", "Kronensicherungen",
    "Vergabelungen (U-Zwiesel) ohne eingewachsene Rinde", 
    "Vergabelungen (V-Zwiesel) mit eingewachsener Rinde",
    "Vergabelungen (V-Zwiesel) mit eingewachsener Rinde, eingerissen", 
    "Fehlentwicklungen in der Krone",
    "Kappungsstellen überwallt",
    "Kappungsstellen eingefault",
    "Kappungsstellen mit Pilzbefall", 
    "Kappungsstellen mit Pilzbefall, eingerissen",
    "Kappungsstellen mit Pilzbefall, eingerissen und eingefault", 
    "Kappungstellen nicht überwallt", "kappungsstellen nicht überwallt, eingefault", 
    "Kappungsstellen nicht überwallt, mit Pilzbefall",
    "Kappungsstellen nicht überwallt, mit Pilzbefall, eingerissen", 
    "Kappungsstellen nicht überwallt, mit Pilzbefall, eingerissen und eingefault",
    "Unglücksbalken", "Unglücksbalken mit Pilzbefall",
    "Unglücksbalken mit Pilzbefall, eingerissen", 
    "Unglücksbalken mit Pilzbefall, eingerissen und eingefault",
    "Unglücksbalken nicht überwallt", 
    "Unglücksbalken nicht überwallt, eingefault",
    "Unglücksbalken nicht überwallt, mit Pilzbefall", 
    "Unglücksbalken nicht überwallt, mit Pilzbefall, eingerissen",
    "Unglücksbalken nicht überwallt, mit Pilzbefall, eingerissen und eingefault",
    "Specht-/Nisthöhlen",
    "Specht-/Nisthöhlen mit Pilzbefall", 
    "Specht-/Nisthöhlen mit Pilzbefall, eingerissen",
    "Specht-/Nisthöhlen mit Pilzbefall, eingerissen und eingefault", 
    "Specht-/Nisthöhlen nicht überwallt",
    "Specht-/Nisthöhlen nicht überwallt, eingefault",
    "Specht-/Nisthöhlen nicht überwallt, mit Pilzbefall", 
    "Specht-/Nisthöhlen nicht überwallt, mit Pilzbefall, eingerissen", 
    "Specht-/Nisthöhlen nicht überwallt, mit Pilzbefall, eingerissen und eingefault",
    "Keine gefährliche Visuelle Symptome erkannt", 
    "Baumfremder Bewuchs",
    "Lichtraumprofil",
    "Ugewöhnliche Blattverfärbungen",
    "Ungewöhnliche Blattabwurf",
    "Ungewöhnliche Blattaustrieb",
    "Überlange Aste",
    "Überlange Äste mit Pilzbefall",
    "Überlange Äste mit Pilzbefall, eingerissen",
    "Wipfeldürre",
    "Kronensicherung",
    "Absenkfalten",
    "Risse / Rippen",
    "Hohlungen",
    "Blitzrinne",
    "Einwalungen",
    "Faulstelle / Astausbruche"]

##c. empfohlene Maßnahmen
maßnahmen_optionen = [
    "Trimmen", "Düngen", "Bewässerung", "Pestizid-Anwendung", "Entfernung",
    "Stammsicherung", "Baumstütze",
    "Baumfällung", "Keine Maßnahmen erforderlich", 
    "Totholzbeseitigung", "Kronensicherung einbauen",
    "Astbruch entfernen", "Sicherung kontrolieren",
    "Frembewuchs entfernen", "Oberlange Aste einkürzen",
    "Kopfbaum schneiden", "Hubsteigerkontrolle"
    "Andere Maßnahme"
]

## d. Standort
Standort_optionen = [ "Parkplatz", "Straße", "Garten", "Wald", "Feld", "Andere" ]

## e. Entwicklungsphase
Entwicklungsphase_optionen = ["Jungephase", "Altephase", "Reifphase", "Absterbephase"]
                     
##f. Vitalität / Zustand
Vitalität_optionen = ["Vital", "Mittel", "Gering vital", "Absterbend"]

## g. Verkehrssicherheit
Verkehrssicherheit_optionen = ["Verkehrssicher", "Verkehrssicher Wiederherstelbar", 
                               "Geringe Gefahr", "Mittlere Gefahr", "Hohe Gefahr", "Unmittelbare Gefahr"]

## h. ...
Stammumpfang = float
Stammdurchmesser = float
Baumhöhe = float
kronendurchmesser = float   

## i. Kontrollinterval
Kontrollinterval_optionen = ["Halbjährlich", "Jährlich", "Einundeinhalbjährlich",
                     "Zweijährlich", "Individuell festlegen"]

## j. Judul tiap kateegori
Kundendaten = " Kundendaten"
Baumdaten = "Baumdaten"
Kontroledaten= "Visuelle Kontrolle (Symptomerkennung)"
schluß = "Maßnahmen & Empfehlungen"
Unterschrift = "Unterschrift"



# --- 3. STREAMLIT UI ---
st.set_page_config(page_title="Baumprotokoll Generator", layout="wide")
st.title("🌳 VTA Baumkontrolle-Protokoll Generator")

st.info("Dieses Tool speichert keine Daten. Füllen Sie das Formular aus und laden Sie das PDF direkt herunter.")

logo_file = st.file_uploader("Unternehmenslogo hochladen (PNG/JPG)", type=["png", "jpg", "jpeg"])

with st.expander("Firmenprofil-Einstellungen"):
    nama_perusahaan = st.text_input("Firmennamen")
    alamat_perusahaan = st.text_input("Firmenadresse")
    email_perusahaan = st.text_input("Email")
    Telefonnummer = st.text_input("Telefonnummer")


# A. STANDORT ERFASSEN
if "sat_img" not in st.session_state:
    st.session_state.sat_img = None

st.subheader("📸 Dokumentation & Standort")

# Karte zum Anklicken
st.subheader("📍 Standort auf Karte markieren")
m = folium.Map(location=[51.16, 10.45], zoom_start=6)
map_data = st_folium(m, width=800, height=400)

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    
    # Bild von Mapbox holen und im SessionState speichern
    st.session_state.sat_img = get_satellite_image(lat, lon)
    
    if st.session_state.sat_img:
        st.success("Standort erfasst und Satellitenbild bereit!")

with st.expander("📸 Fotoaufnahme"):
    # Nutze camera_input für den direkten Zugriff auf die Handykamera
    camera_photo = st.camera_input("Baum fotografieren")
    
    # Optionaler Upload, falls man ein altes Foto wählen will
    uploaded_photo = st.file_uploader("Oder Foto aus Galerie wählen", type=["jpg", "png", "jpeg"])

    # Bestimme, welches Foto genutzt werden soll
    final_photo = camera_photo or uploaded_photo

# B. FORMULAR
st.subheader("📝 2. Protokoll-Details")
with st.form("kataster_form"):

    st.write("👤 **Kundendaten**")
    kontroldatum = st.date_input("Kontrolldatum", value=date.today())   
    kunde_name = st.text_input("Name des Kunden", key="kunde_name", value="")
    kunde_adresse = st.text_input("Adresse des Kunden", key="kunde_adresse", value="")
    

    
    st.divider()



    st.write("🌲 **Baumdaten**")
    search_id = st.text_input("Kataster-Nummer", key="b_id", value="")
    baum_id = st.text_input("Baum-Nummer", key="baum_id", placeholder="z.B. B-001")
    baumart = st.selectbox("Baumart", options=sorted(baum_optionen), key="baumart")
    Standort = st.selectbox("Standort", options=sorted(Standort_optionen), key="Standort")
    Baumhöhe = st.number_input("Baumhöhe (m)", min_value=0.0, step=0.1, key="baumhöhe")
    Stammumpfang = st.number_input("Stammumfang (cm)", min_value=0.0, step=0.1, key="stammumfang")
    Stammdurchmesser = (Stammumpfang / 3.14159) / 100  # Umrechnung von cm zu m und Berechnung des Durchmessers
    kronendurchmesser = st.number_input("Kronendurchmesser (m)", min_value=0.0, step=0.1, key="kronendurchmesser")

    

    st.divider()



    st.write("👁️ **Visuelle Kontrolle (Symptomerkennung)**")
    vWurzelbereich = st.multiselect("Wurzelbereich", options=sorted(Wurzelbereich_optionen), default=[])
    vStammbereich = st.multiselect("Stammbereich", options=sorted(Stammbereich_optionen), default=[])
    vKronen = st.multiselect("Kronen", options=sorted(Kronen_optionen), default=[])
    Vitalität = st.selectbox("Vitalität", options=sorted(Vitalität_optionen), key="vitalität")
    Verkehrssicherheit = st.selectbox("Verkehrssicherheit", options=sorted(Verkehrssicherheit_optionen), key="verkehrssicherheit")
    Entwicklungsphase = st.selectbox("Entwicklungsphase", options=sorted(Entwicklungsphase_optionen), key="entwicklungsphase")
    



    st.divider()



    st.write("🛠️ **Maßnahmen & Empfehlungen**")
    maßnahmen = st.multiselect("Empfohlene Maßnahmen", options=sorted(maßnahmen_optionen), default=[])
    Kontrollinterval = st.selectbox("Kontrollinterval", options=sorted(Kontrollinterval_optionen), key="Kontrollinterval")
    bemerkung = st.text_area("Bemerkungen")

    st.subheader("Digitales Unterschrift einfügen")
    ttd_file = st.file_uploader("Unterschrift hochladen", type=["png","jpg","jpeg"])
    if ttd_file:
        with open("ttd.png", "wb") as f:
            f.write(ttd_file.getbuffer())

    # Formular abschicken
    submitted = st.form_submit_button("📋 Protokoll generieren") 

# --- 4. LOGIK NACH ÜBERMITTLUNG ---
if submitted:
    # 1. Daten sammeln
    data_for_pdf= {
        "Firmennamen": nama_perusahaan,
        "Firmenadresse": alamat_perusahaan,
        "Email Perusahaan": email_perusahaan,
        "Telefonnummer": Telefonnummer,
        "Kontroldatum": kontroldatum.strftime("%d.%m.%Y"),
        "Kunde": kunde_name,
        "Adresse": kunde_adresse,
        "Baum-ID": baum_id,
        "Baumart": baumart,
        "Standort": Standort,
        "Baumhöhe": f"{Baumhöhe} m",
        "Stammumfang": f"{Stammumpfang} cm",
        "Stammdurchmesser": f"{Stammdurchmesser:.2f} m",
        "Kronendurchmesser": f"{kronendurchmesser} m",
        "Vitalität": Vitalität,
        "Visuellesymptome Wurzel": ", ".join(vWurzelbereich) if vWurzelbereich else "Keine gefährliche Visuelle Symptome erkannt",
        "Visuellesymptome Stamm": ", ".join(vStammbereich) if vStammbereich  else "Keine gefährliche Visuelle Symptome erkannt",
        "Visuellesymptome Krone": ", ".join(vKronen) if vKronen else "Keine gefährliche Visuelle Symptome erkannt",
        "Entwicklungsphase": Entwicklungsphase,
        "Verkehrssicherheit": Verkehrssicherheit,
        "Empfohlene Maßnahmen": ", ".join(maßnahmen),
        "Kontrollinterval": Kontrollinterval,
        "Bemerkung": bemerkung,
        "TTD_Pfad": "ttd.png" if ttd_file else None,
    }
  

    # Hier werden das Foto und der Karten-Stream übergeben
    pdf_content = create_pdf(
        data=data_for_pdf,
        logo_file=logo_file,     # Das Firmenlogo (sofern hochgeladen)
        image_file=final_photo,     # Das finale Foto (Kamera oder Upload)
        map_image_stream=st.session_state.sat_img, # Das Mapbox-Satellitenbild (sofern Standort gewählt)
    )
    
    # DOWNLOAD-BUTTON ANZEIGEN
    st.success("✅ Protokoll erfolgreich erstellt!")
    st.download_button(
            label="📄 PDF HERUNTERLADEN",
            data=bytes(pdf_content) if isinstance(pdf_content, (bytearray, bytes)) else pdf_content.encode('latin-1'),
            file_name=f"Baumprotokoll_{date.today()}.pdf",
            mime="application/pdf"
    )