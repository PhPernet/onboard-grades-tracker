import requests
from bs4 import BeautifulSoup
import os
import pandas as pd
from io import StringIO
import unicodedata

# Base URL for the onboard platform
BASE = "https://onboard.ec-nantes.fr"
LOGIN_URL = f"{BASE}/login"  # Login endpoint
MENU_URL = f"{BASE}/faces/MainMenuPage.xhtml"  # Main menu page
NOTES_URL = f"{BASE}/faces/ChoixDonnee.xhtml"  # Notes page

# Path to the current script's directory and the CSV file for storing notes
DIR_FILE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(DIR_FILE, "notes.csv")

# Login credentials
LOGIN = ""
PASSWORD = ""


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
    """
    session.post(
        LOGIN_URL, data={"username": LOGIN, "password": PASSWORD, "j_idt27": ""}
    ).raise_for_status()
    return session.get(MENU_URL)


def get_common_params(soup):
    """
    Extract common parameters like ViewState and idInit from the HTML soup.
    """
    viewstate = get_input_value(soup, "javax.faces.ViewState")
    id_init = get_input_value(soup, "form:idInit")
    return {
        "form": "form",
        "form:largeurDivCenter": "457",
        "form:idInit": id_init,
        "form:sauvegarde": "",
        "form:j_idt827_input": "44323",
        "javax.faces.ViewState": viewstate,
    }


def ajax_sidebar(session, submenu_id, common_params, ajax_headers):
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
    session.post(MENU_URL, data=payload, headers=ajax_headers).raise_for_status()


def download_notes(session, common_params):
    """
    Download the notes CSV file from the onboard platform.
    """
    payload_final = {
        **common_params,
        "form:sidebar": "form:sidebar",
        "form:sidebar_menuid": "3_3_1",
    }
    resp_notes = session.post(MENU_URL, data=payload_final)
    resp_notes.raise_for_status()
    soup_notes = BeautifulSoup(resp_notes.text, "html.parser")
    form = soup_notes.find("form", id="form")
    payload_download = {
        inp.get("name") or inp.get("id"): inp.get("value", "")
        for inp in form.find_all("input")
    }
    payload_download["form:j_idt159"] = "form:j_idt159"
    payload_download["form:largeurDivCenter"] = "457"
    payload_download["form:j_idt181_reflowDD"] = "0_0"
    response = session.post(NOTES_URL, data=payload_download)
    return remove_accents(response.content.decode(encoding="windows-1252"))


def parse_notes(csv_content):
    """
    Parse the notes CSV content into a pandas DataFrame.
    """
    csv_buffer = StringIO(csv_content)
    return pd.read_csv(csv_buffer, sep=";")


def compare_and_save_notes(new_notes, csv_path):
    """
    Compare the new notes with the existing ones and save the updated notes to a CSV file.
    """
    COMPARE_COLS = ["Annee academique", "UE", "Cours", "Epreuve"]
    has_created_file = False

    if os.path.exists(csv_path):
        old_notes = pd.read_csv(csv_path)
        old_compare = old_notes[COMPARE_COLS].copy()
        new_compare = new_notes[COMPARE_COLS].copy()

        # Detect new rows in the new notes
        merged = new_compare.merge(old_compare, how="outer", indicator=True)
        diff_compare = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

        mask = (
            new_notes[COMPARE_COLS]
            .apply(
                lambda row: (
                    row["Annee academique"],
                    row["UE"],
                    row["Cours"],
                    row["Epreuve"],
                ),
                axis=1,
            )
            .isin(
                diff_compare.apply(
                    lambda row: (
                        row["Annee academique"],
                        row["UE"],
                        row["Cours"],
                        row["Epreuve"],
                    ),
                    axis=1,
                )
            )
        )
        diff = new_notes[mask]
        if diff.empty:
            print("No new notes.")
        else:
            print(f"{len(diff)} new notes detected:")
            print(diff)
    else:
        has_created_file = True
        print("Initial file created.")
        diff = new_notes

    # Save the updated notes to the CSV file
    new_notes.to_csv(csv_path, index=False)

    if not diff.empty and not has_created_file:
        print("File updated with new notes.")


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

    # Step 2: Open "My Schooling" submenu
    ajax_sidebar(session, "submenu_692908", common_params, ajax_headers)

    # Step 3: Open "Notes" submenu
    ajax_sidebar(session, "submenu_3755060", common_params, ajax_headers)

    # Step 4: Download and parse the notes
    csv_content = download_notes(session, common_params)
    new_notes = parse_notes(csv_content)

    # Step 5: Compare and save the notes
    compare_and_save_notes(new_notes, CSV_PATH)


if __name__ == "__main__":
    main()
