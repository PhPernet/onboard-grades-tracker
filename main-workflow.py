import warnings
warnings.filterwarnings("ignore", module="urllib3")
import requests
from bs4 import BeautifulSoup
import os
import sys
import pandas as pd
from io import StringIO
import unicodedata
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Base URL for the onboard platform
BASE = "https://onboard.ec-nantes.fr"
LOGIN_URL = f"{BASE}/login"  # Login endpoint
MENU_URL = f"{BASE}/faces/MainMenuPage.xhtml"  # Main menu page
GRADES_URL = f"{BASE}/faces/ChoixDonnee.xhtml"  # Grades page

# Path to the current script's directory and the CSV file for storing grades
DIR_FILE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(DIR_FILE, "grades.csv")

# Login credentials
LOGIN = os.environ["LOGIN"]
PASSWORD = os.environ["PASSWORD"]

# SMTP configuration for sending email notifications
SMTP_SERVER = os.environ["SMTP_SERVER"]
SMTP_PORT = os.environ["SMTP_PORT"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
RECEIVER_EMAIL = os.environ["RECEIVER_EMAIL"]
SENDER_EMAIL = os.environ["SENDER_EMAIL"]

# Regex to find the ids linked to the menus for years
regex_menu_id_years = re.compile(r"form:sidebar_menuid':'(\d+_\d+_\d+)'.*?<span[^>]*>\s*\d+-\d+\s*</span>")

def get_input_value(soup, name):
    """
    Extract the value of an input field by its name from the HTML soup.
    """
    tag = soup.find("input", {"name": name})
    return tag["value"] if tag and "value" in tag.attrs else ""


def remove_accents(text):
    """
    Remove accents from a given text by normalizing it.
    """
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def login(session):
    """
    Perform login to the onboard platform using the provided session.
    Check if the login was successful by verifying the presence of specific elements on the page.
    Handle exceptions if there is no internet connection.
    """
    try:
        print("Logging in to the onboard platform...")
        response = session.post(
            LOGIN_URL, data={"username": LOGIN, "password": PASSWORD, "j_idt27": ""}
        )
        response.raise_for_status()

        # Check if login was successful by looking for a specific element on the menu page
        if "form:idInit" not in response.text:
            print("Login failed: Invalid credentials or unexpected response.")
            sys.exit(1)

        print("Login successful.")
        return session.get(MENU_URL)
    except requests.exceptions.ConnectionError:
        print("Error: No internet connection. Please check your network and try again.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during login: {e}")
        sys.exit(1)


def get_common_params(soup):
    """
    Extract common parameters like ViewState, idInit, and lang from the HTML soup.
    """
    viewstate = get_input_value(soup, "javax.faces.ViewState")
    id_init = get_input_value(soup, "form:idInit")
    lang = soup.find("html").get("lang", "fr")
    return {
        "form": "form",
        "form:largeurDivCenter": "457",
        "form:idInit": id_init,
        "form:sauvegarde": "",
        "form:j_idt827_input": "44323",
        "javax.faces.ViewState": viewstate,
        "lang": lang,
    }


def ajax_sidebar(session: requests.Session, submenu_id: str, common_params: dict, ajax_headers: dict):
    """
    Perform an AJAX request to open a specific submenu on the onboard platform.
    """
    payload = {
        **common_params,
        "javax.faces.partial.ajax": "true",
        "javax.faces.source": "form:j_idt52",
        "javax.faces.partial.execute": "form:j_idt52",
        "javax.faces.partial.render": "form:sidebar",
        "javax.faces.behavior.event": "action",
        "javax.faces.partial.event": "action",
        "form:j_idt52": "form:j_idt52",
        "webscolaapp.Sidebar.ID_SUBMENU": submenu_id,
    }
    resp_ajax = session.post(MENU_URL, data=payload, headers=ajax_headers)
    resp_ajax.raise_for_status()
    return resp_ajax


def find_menu_id_for_last_year(partial_text_response):
    """
    Extract the menu ID corresponding to the last year from the partial response.
    """
    list_matches = list(regex_menu_id_years.finditer(partial_text_response))
    if list_matches:
        return list_matches[-1].group(1)
    else:
        raise ValueError("No match found for year options")


def download_grades(session, common_params, menu_id):
    """
    Download the grades CSV file from the onboard platform.
    """
    payload_final = {
        **common_params,
        "form:sidebar": "form:sidebar",
        "form:sidebar_menuid": menu_id,
    }
    resp_grades = session.post(MENU_URL, data=payload_final)
    resp_grades.raise_for_status()
    soup_grades = BeautifulSoup(resp_grades.text, "html.parser")
    form = soup_grades.find("form", id="form")
    payload_download = {
        inp.get("name") or inp.get("id"): inp.get("value", "")
        for inp in form.find_all("input")
    }
    payload_download["form:j_idt159"] = "form:j_idt159"
    payload_download["form:largeurDivCenter"] = "457"
    payload_download["form:j_idt181_reflowDD"] = "0_0"
    response = session.post(GRADES_URL, data=payload_download)
    return remove_accents(response.content.decode(encoding="windows-1252"))


def parse_grades(csv_content):
    """
    Parse the grades CSV content into a pandas DataFrame.
    """
    csv_buffer = StringIO(csv_content)
    return pd.read_csv(csv_buffer, sep=";")


def compare_and_save_grades(new_grades, csv_path, lang):
    """
    Compare the new grades with the existing ones and save the updated grades to a CSV file.
    """
    print("Comparing grades...")
    diff = None
    if lang == "fr":
        COMPARE_COLS = ["Annee academique", "UE", "Cours", "Epreuve"]
    else:
        COMPARE_COLS = ["Academic year", "UE", "Course", "Test"]
    has_created_file = False

    if os.path.exists(csv_path):
        old_grades = pd.read_csv(csv_path)
        if lang == "fr":
            old_grades = old_grades.rename(
                columns={
                    "Academic year": "Annee academique",
                    "Course": "Cours",
                    "Test": "Epreuve",
                    "Coefficient": "Coefficient",
                    "Grade": "Note",
                }
            )
        else:
            old_grades = old_grades.rename(
                columns={
                    "Annee academique": "Academic year",
                    "Cours": "Course",
                    "Epreuve": "Test",
                    "Coefficient": "Coefficient",
                    "Note": "Grade",
                }
            )
        old_compare = old_grades[COMPARE_COLS].copy()
        new_compare = new_grades[COMPARE_COLS].copy()

        # Detect new rows in the new grades
        merged = new_compare.merge(old_compare, how="outer", indicator=True)
        diff_compare = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

        mask = (
            new_grades[COMPARE_COLS]
            .apply(
                lambda row: (
                    row[COMPARE_COLS[0]],
                    row[COMPARE_COLS[1]],
                    row[COMPARE_COLS[2]],
                    row[COMPARE_COLS[3]],
                ),
                axis=1,
            )
            .isin(
                diff_compare.apply(
                    lambda row: (
                        row[COMPARE_COLS[0]],
                        row[COMPARE_COLS[1]],
                        row[COMPARE_COLS[2]],
                        row[COMPARE_COLS[3]],
                    ),
                    axis=1,
                )
            )
        )
        diff = new_grades[mask]
        if diff.empty:
            print("No new grades.")
        else:
            print(f"{len(diff)} new grades detected:")
            print(diff.to_string(index=False))
        
    else:
        has_created_file = True
        print("Initial file created.")
        diff = new_grades

    # Save the updated grades to the CSV file
    new_grades.to_csv(csv_path, index=False)

    if not diff.empty and not has_created_file:
        print("File updated with new grades.")
    
    return diff


def send_email(new_grades):
    """
    Envoie un email avec les nouvelles notes détectées.
    """
    subject = "Nouvelles notes détectées"
    
    # Construct the email body
    body = "Bonjour,\n\nLes nouvelles notes suivantes ont été détectées :\n\n"
    for _, row in new_grades.iterrows():
        body += f"- Matière : {row['Cours']}, Note : {row['Note']}\n"
    body += "\nCordialement,\nVotre script de suivi des notes."

    # Email configuration
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    

    # Send the email
    try:
        if SMTP_PORT == "465":  # SSL
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SENDER_EMAIL, SMTP_PASSWORD)
                server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        elif SMTP_PORT == "587":  # STARTTLS
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SMTP_PASSWORD)
                server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        else:
            raise ValueError(f"Invalid SMTP port: {SMTP_PORT}. Use 465 for SSL or 587 for STARTTLS.")
        
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")


def main():
    """
    Main function to execute the script workflow.
    """
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": BASE,
            "Referer": BASE + "/",
        }
    )

    # Step 1: Login and retrieve the main menu page
    resp_get = login(session)
    soup = BeautifulSoup(resp_get.text, "html.parser")
    common_params = get_common_params(soup)
    ajax_headers = {**session.headers, "Faces-Request": "partial/ajax"}
    print("Downloading grades...")

    # Step 2: Open "My Schooling" submenu
    ajax_sidebar(session, "submenu_692908", common_params, ajax_headers)

    # Step 3: Open "grades" submenu
    partial_text_response = ajax_sidebar(session, "submenu_3755060", common_params, ajax_headers).text

    # Step 4: Download and parse the grades
    menu_id = find_menu_id_for_last_year(partial_text_response)
    csv_content = download_grades(session, common_params, menu_id)
    new_grades = parse_grades(csv_content)

    # Step 5: Compare and save the grades
    diff = compare_and_save_grades(new_grades, CSV_PATH, common_params["lang"])

    # Step 6: Send email if new grades are detecteds
    if not diff.empty:
        send_email(diff)




if __name__ == "__main__":
    main()
