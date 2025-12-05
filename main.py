import warnings
warnings.filterwarnings("ignore", module="urllib3")
import requests
from bs4 import BeautifulSoup
import os
import sys
import pandas as pd
from io import StringIO
import unicodedata
from dotenv import load_dotenv
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()
# Base URL for the onboard platform
BASE = "https://onboard.ec-nantes.fr"
LOGIN_URL = f"{BASE}/login"  # Login endpoint
MENU_URL = f"{BASE}/faces/MainMenuPage.xhtml"  # Main menu page
GRADES_URL = f"{BASE}/faces/ChoixDonnee.xhtml"  # Grades page

# Path to the current script's directory and the CSV file for storing grades
DIR_FILE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(DIR_FILE, "grades.csv")

# Login credentials
LOGIN = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")

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
    Handles both CSV format and HTML table format (site may have changed).
    """
    csv_str = (csv_content or "").strip()
    if not csv_str:
        print("parse_grades: empty response (no CSV content).")
        return pd.DataFrame()

    # If we received HTML, try to extract a table from it
    if csv_str.lstrip().startswith("<"):
        print("parse_grades: received HTML response. Attempting to extract table...")
        try:
            # Parse HTML and look for tables
            soup = BeautifulSoup(csv_str, "html.parser")
            tables = soup.find_all("table")
            
            if not tables:
                print("parse_grades: no HTML table found in response.")
                return pd.DataFrame()
            
            print(f"parse_grades: found {len(tables)} table(s) in HTML. Searching for valid grades table...")
            
            # Try to manually extract rows and columns from each table
            for table_idx, table in enumerate(tables):
                try:
                    # Extract headers from <th> or first <tr>
                    headers = []
                    header_row = table.find("thead")
                    if header_row:
                        header_cells = header_row.find_all("th")
                        headers = [cell.get_text(strip=True) for cell in header_cells]
                    else:
                        # Try first row as headers
                        first_row = table.find("tr")
                        if first_row:
                            header_cells = first_row.find_all(["th", "td"])
                            headers = [cell.get_text(strip=True) for cell in header_cells]
                    
                    if not headers:
                        print(f"parse_grades: table {table_idx}: no headers found, skipping.")
                        continue
                    
                    # Clean headers: remove "Filter by ...", extract only the main part
                    cleaned_headers = []
                    for h in headers:
                        # Remove "Filter by XYZ" suffix
                        if "Filter by" in h:
                            h = h.split("Filter by")[0].strip()
                        cleaned_headers.append(h)
                    
                    # Filter out empty header strings
                    cleaned_headers = [h for h in cleaned_headers if h]
                    if not cleaned_headers:
                        print(f"parse_grades: table {table_idx}: all headers are empty after cleaning, skipping.")
                        continue
                    
                    print(f"parse_grades: table {table_idx}: found headers (cleaned): {cleaned_headers}")
                    
                    # Extract data rows
                    rows = []
                    tbody = table.find("tbody") or table
                    tbody_rows = tbody.find_all("tr")
                    
                    # Determine starting index: skip the first row only if it's a header row (contains <th>)
                    start_idx = 0
                    if tbody_rows and tbody_rows[0].find("th"):
                        # First row has <th>, so it's a header row, skip it
                        start_idx = 1
                    
                    for tr in tbody_rows[start_idx:]:
                        cells = tr.find_all(["td", "th"])
                        row_data = [cell.get_text(strip=True) for cell in cells]
                        if row_data and len(row_data) > 0:
                            # Pad or trim row data to match header count
                            if len(row_data) < len(cleaned_headers):
                                row_data.extend([""] * (len(cleaned_headers) - len(row_data)))
                            elif len(row_data) > len(cleaned_headers):
                                row_data = row_data[:len(cleaned_headers)]
                            rows.append(row_data)
                    
                    print(f"parse_grades: table {table_idx}: extracted {len(rows)} data rows.")
                    
                    if rows:
                        # Create DataFrame
                        df = pd.DataFrame(rows, columns=cleaned_headers)
                        if not df.empty:
                            print(f"parse_grades: table {table_idx}: successfully extracted {len(df)} rows and {len(df.columns)} columns.")
                            print(f"parse_grades: table {table_idx}: columns = {list(df.columns)}")
                            print(f"parse_grades: table {table_idx}: first row = {df.iloc[0].to_dict() if len(df) > 0 else 'N/A'}")
                            
                            # Check if this looks like a grades table
                            # Simple heuristic: if it has 4+ columns and one of them contains "Note", "Cours", or similar, it's likely a grades table
                            if len(df.columns) >= 4:
                                print(f"parse_grades: table {table_idx}: has {len(df.columns)} columns (>= 4), looks like a valid grades table, using it.")
                                return df
                            else:
                                print(f"parse_grades: table {table_idx}: has only {len(df.columns)} columns, continuing search.")
                    else:
                        print(f"parse_grades: table {table_idx}: no data rows extracted.")
                except Exception as ex:
                    print(f"parse_grades: table {table_idx}: error extracting rows: {ex}")
                    continue
            
            print("parse_grades: could not find a valid grades table in any of the HTML tables.")
            return pd.DataFrame()
        except Exception as e:
            print(f"parse_grades: error parsing HTML: {e}")
            return pd.DataFrame()

    # Otherwise, try standard CSV parsing
    # If the expected separator is not present, it's probably not the CSV we expect
    first_line = csv_str.splitlines()[0]
    if ";" not in first_line:
        print("parse_grades: no ';' separator found in CSV header — treating as no grades.")
        return pd.DataFrame()

    try:
        csv_buffer = StringIO(csv_content)
        return pd.read_csv(csv_buffer, sep=";")
    except pd.errors.EmptyDataError:
        print("parse_grades: pandas reported EmptyDataError — no grades.")
        return pd.DataFrame()
    except pd.errors.ParserError as e:
        print(f"parse_grades: ParserError reading CSV: {e} — treating as no grades.")
        return pd.DataFrame()


def compare_and_save_grades(new_grades, csv_path, lang):
    """
    Compare the new grades with the existing ones and save the updated grades to a CSV file.
    """
    print("Comparing grades...")
    diff = None
    # If parsing produced an empty DataFrame, there are no grades to compare
    if new_grades is None or new_grades.empty:
        print("No grades found for the latest year (page exists but contains no notes). Nothing to save or compare.")
        # Return an empty DataFrame to signal 'no new grades'
        return pd.DataFrame()
    
    # Normalize column names: clean up encoding issues and remove spaces
    def clean_column_name(col):
        # Replace common encoding artifacts
        col = col.replace("A©", "e").replace("A‰", "e").replace("A ", "a")
        # Remove accents
        col = remove_accents(col)
        # Remove spaces
        col = col.replace(" ", "").lower()
        return col
    
    new_grades.columns = [clean_column_name(col) for col in new_grades.columns]
    
    if lang == "fr":
        COMPARE_COLS = ["anneeacademique", "ue", "cours", "epreuve"]
    else:
        COMPARE_COLS = ["academicyear", "ue", "course", "test"]
    has_created_file = False

    if os.path.exists(csv_path):
        old_grades = pd.read_csv(csv_path)
        # Normalize column names in old_grades too
        old_grades.columns = [clean_column_name(col) for col in old_grades.columns]
        
        if lang == "fr":
            old_grades = old_grades.rename(
                columns={
                    "academicyear": "anneeacademique",
                    "course": "cours",
                    "test": "epreuve",
                    "coefficient": "coefficient",
                    "grade": "note",
                }
            )
        else:
            old_grades = old_grades.rename(
                columns={
                    "anneeacademique": "academicyear",
                    "cours": "course",
                    "epreuve": "test",
                    "coefficient": "coefficient",
                    "note": "grade",
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
    receiver_email = os.getenv("RECEIVER_EMAIL")
    sender_email =  os.getenv("SENDER_EMAIL")
    subject = "Nouvelles notes détectées"
    
    # Construct the email body
    body = "Bonjour,\n\nLes nouvelles notes suivantes ont été détectées :\n\n"
    for _, row in new_grades.iterrows():
        # Use normalized column names (lowercase, no spaces, no accents)
        cours = row.get('cours', row.get('course', 'N/A'))
        note = row.get('note', row.get('grade', 'N/A'))
        body += f"- Matière : {cours}, Note : {note}\n"
    body += "\nCordialement,\nVotre script de suivi des notes."

    # Email configuration
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv('SMTP_PORT')
    smtp_password = os.getenv("SMTP_PASSWORD")

    # Send the email
    try:
        if smtp_port == "465":  # SSL
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, smtp_password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
        elif smtp_port == "587":  # STARTTLS
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, smtp_password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
        else:
            raise ValueError(f"Invalid SMTP port: {smtp_port}. Use 465 for SSL or 587 for STARTTLS.")
        
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
