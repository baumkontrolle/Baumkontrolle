import streamlit as st
from fpdf import FPDF
from datetime import date
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import tempfile
import requests
from io import BytesIO
from PIL import Image
import os
from fpdf.enums import XPos, YPos


# --- 1. PDF-ERSTELLUNG FUNKTION ---
def create_pdf(data, image_file=None, sat_url=None, logo_file=None):
    # Tambah parameter logo_file
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # --- LOGO PERUSAHAAN ---
    y_posisi = 10
    logo_breite = 0 # Standard, falls kein Logo da ist
    gap = 3 # Gewünschter Abstand zwischen Text und Logo

    if logo_file is not None:
        try:
            # Gunakan PIL untuk memproses gambar langsung dari memori
            img = Image.open(logo_file)
            logo_breite = 40

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_logo:
                img.save(tmp_logo.name, format="JPEG")
                pdf.image(tmp_logo.name, x=160, y=10, w=35)
                # Tutup file sebelum dihapus (penting untuk Windows)
                x_logo = 200 - logo_breite 
                pdf.image(tmp_logo.name, x=x_logo, y=y_posisi, w=logo_breite)
        except Exception as e:
            logo_breite = 0
            pdf.set_font("Helvetica", "I", 8)
            pdf.text(160, 8, "Logo-Format Fehler")

    # ---DATA PERUSAHAAN (Sisi Kiri, Samping Logo) ---
    # Kita ambil data dari input user (misalnya 'Nama Perusahaan', 'Alamat', dll)
    # Seitenbreite (210) - Ränder (20) - Logo_Breite - Gap (3)
    text_box_breite = 210 - 20 - logo_breite - gap
    pdf.set_xy(10, y_posisi + 2) 
            
    # Nama Perusahaan (Ambil dari data yang dikirim user)
    pdf.set_font("Helvetica", "B", 11,) 
    nama_pt = data.get("Firmennamen", "Nama Perusahaan Anda")
    pdf.cell(text_box_breite, 6, nama_pt, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R") 
    
    # Detail Tambahan (Alamat/Telp)
    pdf.set_font("Helvetica", "", 10,)
    alamat_pt = data.get("Firmenadresse", "Alamat Belum Diisi")
    pdf.cell(text_box_breite, 5, alamat_pt, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
    
    email_pt = data.get("Email Perusahaan", "email@perusahaan.com")
    pdf.cell(text_box_breite, 5, email_pt, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")

    telp_pt = data.get("Telefonnummer", "Telp: -")
    pdf.cell(text_box_breite, 5, telp_pt, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")


#tanpa gris pembartas, langsung ke judul utama dan konten lainnya

    # --- 1. JUDUL UTAMA (Di bawah Header) ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 15, "Baumkontrolle VTA I", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    
    # --- 2. KUNDENDATEN ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Kundendaten", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    label_w_head = 20  # Lebar label untuk Kundendaten
    kundendaten_felder = [("Datum", "Kontroldatum"), ("Kunde", "Kunde"),  ("Adresse", "Adresse")]
    for label, key in kundendaten_felder:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(label_w_head, 8, f"{label}:") 
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, str(data.get(key, "-")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # --- 3. BAUMDATEN (Zwei Spalten) ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Baumdaten", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    y_start_baum = pdf.get_y()
    label_w_col = 20 

    # Linke Spalte
    pdf.set_y(y_start_baum)
    kiri = [("Baum-ID", "Baum-ID"), ("Baumart", "Baumart"), ("Standort", "Standort")]
    for label, key in kiri:
        pdf.set_x(10)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_w_col, 8, f"{label}:") 
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(50, 8, str(data.get(key, "-")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Rechte Spalte
    pdf.set_y(y_start_baum)
    kanan = [("Höhe", "Baumhöhe"), ("Umfang", "Stammumfang"), ("Ø Stamm", "Stammdurchmesser"), ("Ø Krone", "Kronendurchmesser")]
    for label, key in kanan:
        pdf.set_x(105)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_w_col, 8, f"{label}:")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(50, 8, str(data.get(key, "-")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(y_start_baum + 40)  # Pindah ke bawah untuk bagian selanjutnya

    # --- 4. SEKTIONEN (Nur einmal ausführen!) ---
    sektionen = [
        ("Visuelle Kontrolle (Symptomerkennung)", ["Vitalität", "Visuallesymptome Wurzel", "Visuellesymptome Stamm", "Visuallesymptome Krone"]),
        ("Maßnahmen & Empfehlungen", ["Maßnahmen", "Kontrollintervall", "Bemerkung", "Koordinaten", "logo_file"])
    ]

    for titel, keys in sektionen:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, titel, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)

        for key in keys:
            if key in data:
                wert = data[key]
                
                # 1. Komma-String in Liste umwandeln (falls nötig)
                if isinstance(wert, str) and "," in wert:
                    wert = [i.strip() for i in wert.split(",")]

                # 2. Label drucken (Helvetica statt Arial wegen der Warnung)
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 8, f"{key}:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                pdf.set_font("Helvetica", "", 11)
                
                # 3. Inhalt prüfen und drucken
                if isinstance(wert, list) and wert:
                    # SCHLEIFE: Hier existiert 'item'
                    for item in wert:
                        if str(item).strip():
                            pdf.set_x(15)
                            # WICHTIG: Bindestrich statt Punkt nutzen!
                            pdf.multi_cell(0, 7, text=f"- {item}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                else:
                    # KEINE SCHLEIFE: Hier gibt es kein 'item'!
                    pdf.set_x(15)
                    # Wir nutzen 'inhalt', um den Wert sicher zu formatieren
                    inhalt = str(wert) if wert and str(wert).strip() not in ["", "-", "None"] else "Keine Angabe"
                    pdf.multi_cell(0, 7, text=inhalt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                pdf.ln(2)


    # --- SEITE 2: BILDER NEBENEINANDER ---

    if image_file or sat_url:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Dokumentation (Bilder)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(10)
        
        # Koordinaten für diese neue Seite setzen
        text_y = pdf.get_y()
        bild_y = text_y + 10
        bild_breite = 90

        # 2.1 Foto vom Baum
        if image_file is not None:
            try:
                image_file.seek(0)
                pdf.set_font("Helvetica", "B", 12)
                pdf.text(x=10, y=bild_y - 3, text="Baum-Foto")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(image_file.read())
                    pdf.image(tmp.name, x=10, y=bild_y, w=bild_breite)
                os.remove(tmp.name)
            except Exception as e:
                print(f"Error Tree Image: {e}")

        # 2.2 Satellitenbild (Korrigierte Version)
        if sat_url:
            try:
                response = requests.get(sat_url, timeout=10)
                response.raise_for_status()

                # Bild aus dem Internet laden
                sat_img = Image.open(BytesIO(response.content))
                
                # Konvertieren falls nötig (RGBA zu RGB für PDF)
                if sat_img.mode in ("RGBA", "P"):
                    sat_img = sat_img.convert("RGB")

                # Als temporäre Datei für FPDF zwischenspeichern
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_sat:
                    sat_img.save(tmp_sat.name, format="JPEG")
                    tmp_sat_path = tmp_sat.name
                    
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.text(x=105, y=bild_y - 3, text="Satelliten-Standort")
                    # Bild auf der rechten Seite (x=105) platzieren
                    pdf.image(tmp_sat.name, x=105, y=bild_y, w=bild_breite)
                
                # Datei danach löschen
                if os.path.exists(tmp_sat.name):
                    os.remove(tmp_sat.name)

            except Exception as e:
                pdf.set_font("Helvetica", "I", 10)
                pdf.text(x=105, y=bild_y + 10, text=f"Sat-Bild Fehler: {e}")

    return pdf.output()
    
    # --- UNTERSCHRIFTENFELD (Ganz am Ende) ---
    pdf.ln(20) # Großer Abstand nach oben
    
    # Wir erstellen eine Spalte auf der rechten Seite
    # 130 ist der X-Wert (Abstand von links), um nach rechts zu rücken
    pdf.set_x(130) 
    
    # Eine Linie für die Unterschrift zeichnen
    current_y = pdf.get_y()
    pdf.line(130, current_y, 200, current_y)
    
    # Text unter die Linie schreiben
    pdf.ln(2)
    pdf.set_x(130)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(70, 8, "Unterschrift Prüfer", ln=True, align="C")

    pdf_output = pdf.output()

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
    "*Sonstige / Unbekannt"
]

## b. Visuelle Kontrolle (Symptomerkennung)
Wurzelbereich_optionen = [
    "Pilzfruchtkörper", "Risse", "Wurzelanläufe",
    "Pestizid-Aufwölbungen", "Bodenveränderungen", "Stammaustriebe",
    "Abgestorbene Rinden oder Rindenschäden", "Anfahrschäden",
    "Kappungen von Wurzeln", "Würgewurzeln", "Adventivwurzeln",
    "Auffallende Ausformungen", "Bodenrisse (Bodenaufwölbungen)",
    "Insekten", "Baustellen", "Bodenauftrag", "Bodenabtrag",
    "Bodenverdichtung oder Bodenversiegelung", "Keine gefährliche Visuelle Symptome erkannt"
    ]

Stammbereich_optionen = [
    "Pilzfruchtkörper", "offene Höhlungen", "Spechtlöcher", "Fremdkörper", 
    "Rindenverlust", "Beulen", "Schrägstand", "Stammsicherungen", 
    "Anfahrschaden", "Astungswunden", "Zwiesel", "Höhlungen", "Risse", "Borkenabhebung", 
    "Rindenverletzungen", "Rindenveränderungen", "Rindenveränderungen mit Pilzbefall", 
    "Rindenveränderungen mit Pilzbefall, eingerissen", "Rindenveränderungen mit Pilzbefall, eingerissen und eingefault",
    "Baumfremder Bewuchs", "Stammaustriebe", "bgestorbene Rinde", 
    "Leckstellen", "Ausfluss", "nässende Flecken", "Wülste", "Rippen", "Beulen",
    "Keine gefährliche Visuelle Symptome erkannt"
]

Kronen_optionen = [
    "Abgestorbene Rinde", "Pilzfruchtkörper", "Kronendeformationen", 
    "Schädlingsbefall", "Zwieselbildung", "Totäste (> 5 cm Durchmesser ab Astbasis)", 
    "Astabbrüche", "Astungswunden", "Astausbrüche", "Wunden (Teil-)überwallt", 
    "Wunden Eingefault", "Eingefaulte Äste", "Kronensicherungen", "Vergabelungen (U-Zwiesel) ohne eingewachsene Rinde", 
    "Vergabelungen (V-Zwiesel) mit eingewachsener Rinde", "Vergabelungen (V-Zwiesel) mit eingewachsener Rinde, eingerissen", 
    "Fehlentwicklungen in der Krone", "Kappungsstellen überwallt",
    "Kappungsstellen eingefault", "Kappungsstellen mit Pilzbefall", 
    "Kappungsstellen mit Pilzbefall, eingerissen", "Kappungsstellen mit Pilzbefall, eingerissen und eingefault", 
    "kappungstellen nicht überwallt", "kappungsstellen nicht überwallt, eingefault", 
    "kappungsstellen nicht überwallt, mit Pilzbefall", "kappungsstellen nicht überwallt, mit Pilzbefall, eingerissen", 
    "kappungsstellen nicht überwallt, mit Pilzbefall, eingerissen und eingefault",
    "Unglücksbalken", "Unglücksbalken mit Pilzbefall", "Unglücksbalken mit Pilzbefall, eingerissen", 
    "Unglücksbalken mit Pilzbefall, eingerissen und eingefault", "Unglücksbalken nicht überwallt", 
    "Unglücksbalken nicht überwallt, eingefault", "Unglücksbalken nicht überwallt, mit Pilzbefall", 
    "Unglücksbalken nicht überwallt, mit Pilzbefall, eingerissen", "Unglücksbalken nicht überwallt, mit Pilzbefall, eingerissen und eingefault",
    "Specht-/Nisthöhlen", "Specht-/Nisthöhlen mit Pilzbefall", 
    "Specht-/Nisthöhlen mit Pilzbefall, eingerissen", "Specht-/Nisthöhlen mit Pilzbefall, eingerissen und eingefault", 
    "Specht-/Nisthöhlen nicht überwallt", "Specht-/Nisthöhlen nicht überwallt, eingefault", "Specht-/Nisthöhlen nicht überwallt, mit Pilzbefall", 
    "Specht-/Nisthöhlen nicht überwallt, mit Pilzbefall, eingerissen", 
    "Specht-/Nisthöhlen nicht überwallt, mit Pilzbefall, eingerissen und eingefault",
    "Keine gefährliche Visuelle Symptome erkannt", 
    "Baumfremder Bewuchs", "Lichtraumprofil",
    "ungewöhnliche Blattverfärbungen", "ungewöhnliche Blattabwurf", "ungewöhnliche Blattaustrieb",
    "überlange asten", "überlange Äste mit Pilzbefall", "überlange Äste mit Pilzbefall, eingerissen",
    ]

##c. empfohlene Maßnahmen
maßnahmen_optionen = [
    "Trimmen", "Düngen", "Bewässerung", "Pestizid-Anwendung", "Entfernung",
    "Totholzenfestigung", "Stammsicherung", "Kronensicherung", "Baumstütze",
    "Baumfällung", "Keine Maßnahmen erforderlich", "Andere Maßnahme"
]

## d. Standort
Standort = [ "Parkplatz", "Straße", "Garten", "Wald", "Feld", "Andere" ]

## e. Entwicklungsphase
Entwicklungsphase = ["Jungephase", "Altephase", "Reifphase", "Absterbephase"]
                     
##f. Vitalität / Zustand
Vitalität = ["Vital", "Mittel", "Gering vital", "Absterbend"]

## g. Verkehrssicherheit
Verkehrssicherheit = ["Keine Gefahr", "Geringe Gefahr", "Mittlere Gefahr", "Hohe Gefahr", "Unmittelbare Gefahr"]

## h. ...
Stammumpfang = float
Stammdurchmesser = float
Baumhöhe = float
kronendurchmesser = float   

## i. kontrolintervall
Kontrollintervall = ["sofort", " 6 Monate", "1 Jahr",
                     "2 Jahre", "3 Jahre", "5 Jahre",
                     "10 Jahre", "Individuell festlegen"]

## j. Judul tiap kateegori
Kundendaten = " Kundendaten"
Baumdaten = "Baumdaten"
Kontroledaten= "Visuelle Kontrolle (Symptomerkennung)"
schluß = "Maßnahmen & Empfehlungen"
Unterschrift = "Unterschrift"



# --- 3. STREAMLIT UI ---
st.set_page_config(page_title="Baumprotokoll Generator", layout="wide")
st.title("🌳 Baumkontroll-Protokoll Generator")

st.info("Dieses Tool speichert keine Daten. Füllen Sie das Formular aus und laden Sie das PDF direkt herunter.")

logo_file = st.file_uploader("Unternehmenslogo hochladen (PNG/JPG)", type=["png", "jpg", "jpeg"])

with st.expander("Firmenprofil-Einstellungen"):
    nama_perusahaan = st.text_input("Firmennamen")
    alamat_perusahaan = st.text_input("Firmenadresse")
    email_perusahaan = st.text_input("Email")
    Telefonnummer = st.text_input("Telefonnummer")


# A. STANDORT ERFASSEN
st.subheader("📍 1. Standort & Foto")

# Karte mit "LocateControl" für den aktuellen Standort
m = folium.Map(location=[52.52, 13.40], zoom_start=15)
LocateControl(auto_start=False).add_to(m) # Fügt den "Wo bin ich"-Button hinzu
m.add_child(folium.LatLngPopup())

map_output = st_folium(m, height=300, width=500, key="map")

selected_lat, selected_lng = None, None
sat_image_url = None

if map_output and map_output.get("last_clicked"):
    selected_lat = map_output["last_clicked"]["lat"]
    selected_lng = map_output["last_clicked"]["lng"]
    st.success(f"Position gewählt: {selected_lat:.5f}, {selected_lng:.5f}")
    mapbox_token = "DEIN_MAPBOX_TOKEN"
    sat_image_url = f"https://mapbox.com{selected_lng},{selected_lat},18,0/600x600?access_token={mapbox_token}"

        
# B. FOTO AUFNEHMEN
st.subheader("📸 2. Baum-Foto")
img_file = st.camera_input("Foto aufnehmen")

# C. FORMULAR
st.subheader("📝 3. Protokoll-Details")
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
    Standort = st.selectbox("Standort", options=sorted(Standort), key="Standort")
    Baumhöhe = st.number_input("Baumhöhe (m)", min_value=0.0, step=0.1, key="baumhöhe")
    Stammumpfang = st.number_input("Stammumfang (cm)", min_value=0.0, step=0.1, key="stammumfang")
    Stammdurchmesser = (Stammumpfang / 3.14159) / 100  # Umrechnung von cm zu m und Berechnung des Durchmessers
    kronendurchmesser = st.number_input("Kronendurchmesser (m)", min_value=0.0, step=0.1, key="kronendurchmesser")

    

    st.divider()



    st.write("👁️ **Visuelle Kontrolle (Symptomerkennung)**")
    Vitalität = st.selectbox("Vitalität", options=sorted(Vitalität), key="vitalität")
    vWurzelbereich = st.multiselect("Wurzelbereich", options=sorted(Wurzelbereich_optionen), default=[])
    vStammbereich = st.multiselect("Stammbereich", options=sorted(Stammbereich_optionen), default=[])
    vKronen = st.multiselect("Kronen", options=sorted(Kronen_optionen), default=[])



    st.divider()



    st.write("🛠️ **Maßnahmen & Empfehlungen**")
    maßnahmen = st.multiselect("Empfohlene Maßnahmen", options=sorted(maßnahmen_optionen), default=[])
    kontrolrolintervall = st.selectbox("Kontrollintervall", options=sorted(Kontrollintervall), key="kontrollintervall")
    bemerkung = st.text_area("Bemerkungen")
    


    # Formular abschicken
    submitted = st.form_submit_button("📋 Protokoll generieren")


    

# --- 4. LOGIK NACH ÜBERMITTLUNG ---
if submitted:
        # 1. Daten sammeln
    data_for_pdf = {
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
        "Visuallesymptome Wurzel": ", ".join(vWurzelbereich) if vWurzelbereich else "Keine gefährliche Visuelle Symptome erkannt",
        "Visuellesymptome Stamm": ", ".join(vStammbereich) if vStammbereich  else "Keine gefährliche Visuelle Symptome erkannt",
        "Visuallesymptome Krone": ", ".join(vKronen) if vKronen else "Keine gefährliche Visuelle Symptome erkannt",
        "Maßnahmen": ", ".join(maßnahmen),
        "Kontrollintervall": kontrolrolintervall,
        "Bemerkung": bemerkung,
        "Koordinaten": f"{selected_lat}, {selected_lng}" if selected_lat else "Nicht gesetzt"
    }


# Gambar satelit
if selected_lat and selected_lng:
    # Bounding Box um die Koordinaten
    delta = 0.001 
    bbox = f"{selected_lng-delta},{selected_lat-delta},{selected_lng+delta},{selected_lat+delta}"
    
    # Korrekte Basis-URL für den Export-Service
    base_url = "https://arcgisonline.com"
    
    # Parameter sauber zusammenfügen
    sat_url = (
        f"{base_url}?bbox={bbox}"
        f"&bboxSR=4326"        # Korrekter Code für WGS84
        f"&size=600,600"
        f"&format=png"
        f"&f=image"
    )
else:
    sat_url = None


    # --- 5. PDF erstellen (HIER rufen wir die Funktion auf!)
if st.button("Protokoll generieren"):
    try:
        # Hier rufst du deine Funktion auf
        pdf_bytes = create_pdf(
            data_for_pdf=data_for_pdf, 
            image_file=img_file, 
            sat_url=sat_url, 
            logo_file=logo_file
        )
        
        # Wenn alles geklappt hat, speichern wir es im "Gedächtnis" (Session State)
        st.session_state.pdf_ready = pdf_bytes
        st.success("✅ Protokoll bereit zum Download!")

        st.download_button(
            label="📄 PDF Herunterladen",
            data=data_for_pdf,
            file_name=f"Baumprotokoll_{kontroldatum}_{kunde_name.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Fehler bei der PDF-Erstellung: {e}")
