import requests
from bs4 import BeautifulSoup
import re
import json
import nltk

nltk.download("punkt")

EMAIL_RE = r"\S+@\S+"
PHONE_RE = r"(\+43|0043|0)\s?\d{2,4}[\d\s]+"

possible_category_words = [
    "Sport", "Tierschutz", "Bildung", "Kultur", "Gesundheit",
    "Kinder", "Jugendliche", "Familien", "Umwelt", "Natur"
]


def get_text_and_soup(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    return text, soup


def extract_regex(pattern, text):
    match = re.search(pattern, text)

    if match:
        return match.group(0).strip()

    return ""


def extract_after_label(text, label):
    pattern = label + r"\s*:\s*(.*)"
    match = re.search(pattern, text)

    if match:
        return match.group(1).strip()

    return ""


def extract_between(text, start, end):
    pattern = re.escape(start) + r"(.*?)" + re.escape(end)
    match = re.search(pattern, text, re.DOTALL)

    if match:
        return " ".join(match.group(1).split())

    return ""


def select_description(text):
    sentences = nltk.sent_tokenize(text, language="german")

    if sentences:
        return sentences[0]

    return ""


def extract_category(text):
    for word in possible_category_words:
        if word.lower() in text.lower():
            return word

    return ""


# First website: homogeneous, label-based
def extract_homogeneous(url):
    text, soup = get_text_and_soup(url)

    description = extract_between(
        text,
        "Ziel der Organisation:",
        "Tätigkeitsbereich"
    )

    category = extract_between(
        text,
        "Themenbereich(e) der Organisation:",
        "Ort(e), wo ehrenamtliche Tätigkeit"
    )

    return {
        "organization_name": extract_after_label(text, "Name"),
        "address": extract_after_label(text, "Adresse"),
        "phone": extract_after_label(text, "Telefon"),
        "email": extract_after_label(text, "E-Mail"),
        "homepage": extract_after_label(text, "Homepage"),
        "description": select_description(description),
        "category": category,
        "source_url": url
    }

# Second website: more generic rule-based extraction
def extract_heterogeneous(url):
    text, soup = get_text_and_soup(url)

    # Name rule: use og:title first, because it is more reliable
    og_title = soup.find("meta", property="og:title")
    if og_title:
        name = og_title.get("content", "")
    else:
        title = soup.find("title")
        name = title.get_text(strip=True) if title else ""

    # Description rule: use meta description first
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        description = meta_desc.get("content", "")
    else:
        description = select_description(text)

    # Email rule
    email = extract_regex(EMAIL_RE, text)

    # Phone rule: prefer tel: links
    phone = ""
    tel_link = soup.find("a", href=re.compile("^tel:"))
    if tel_link:
        phone = tel_link.get_text(" ", strip=True)
    else:
        phone = extract_regex(PHONE_RE, text)

    # Contact section
    address = ""
    homepage = ""

    contact_heading = soup.find(string=re.compile("Kontaktdaten", re.IGNORECASE))

    if contact_heading:
        contact_box = contact_heading.find_parent().find_parent()

        contact_text = contact_box.get_text("\n", strip=True)
        lines = contact_text.split("\n")

        address_lines = []

        for line in lines:
            if "Kontaktdaten" in line:
                continue
            if "@" in line:
                break
            if line.startswith("+43") or line.startswith("0"):
                break
            if ".at" in line or ".com" in line:
                break

            address_lines.append(line)

        address = " ".join(address_lines).strip()

        for link in contact_box.find_all("a", href=True):
            href = link["href"]

            if href.startswith("http"):
                if "facebook" not in href and "instagram" not in href and "tiktok" not in href:
                    homepage = href
                    break

    # Category rule
    category = extract_category(text)

    return {
        "organization_name": name,
        "address": address,
        "phone": phone,
        "email": email,
        "homepage": homepage,
        "description": description,
        "category": category,
        "source_url": url
    }

homogeneous_urls = [
    "https://treffpunkt-ehrenamt.at/organisation/zukunft-rechberg-verein-fuer-dorfentwicklung/",
    "https://treffpunkt-ehrenamt.at/organisation/zivilschutzverband-oberoesterreich/",
    "https://treffpunkt-ehrenamt.at/organisation/zeitbank-fuer-alt-und-jung-miteinander-leben-in-schlatt/",
    "https://treffpunkt-ehrenamt.at/organisation/zeitbank-eggelsberg-fuer-alt-und-jung/",
    "https://treffpunkt-ehrenamt.at/organisation/zak-zwettler-aktionsteam/",
    "https://treffpunkt-ehrenamt.at/organisation/youth-for-understanding-austria/",
    "https://treffpunkt-ehrenamt.at/organisation/wsv-atsv-ranshofen-zweigverein-fussball/",
    "https://treffpunkt-ehrenamt.at/organisation/wir-gemeinsam-zeittausch-netzwerk/",
    "https://treffpunkt-ehrenamt.at/organisation/wieso-bekommt-nicht-jeder-beeintraechtigte-das-geeignete-hilfsmittel/",
    "https://treffpunkt-ehrenamt.at/organisation/wellcome-praktische-hilfe-nach-der-geburt-kath-familienverband-ooe/"
]

heterogeneous_urls = [
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/1-badminton-club-vorarlberg-fu%C3%9Fach",
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/abschnittsfeuerwehrkommando-zistersdorf",
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/abteilung-gesellschaftliches-engagement-zivilcourage",
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/acker-%C3%B6sterreich-gemeinn%C3%BCtzige-gmbh",
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/adventures-leibnitz",
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/afc-telfs-patriots",
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/afs-%C3%B6sterreich",
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/aha-plus",
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/aktion-mutante-kunst-und-kulturverein",
    "https://www.freiwillig-engagiert.at/fuer-organisationen/organisation/aktiver-tierschutz-austria"
]

results = []

for url in homogeneous_urls:
    results.append(extract_homogeneous(url))

for url in heterogeneous_urls:
    results.append(extract_heterogeneous(url))


with open("organizations.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)


print("Saved organizations.json")