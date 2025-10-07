import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

st.title("Upwork Job Scraper (Cloud-friendly) — public emails / LinkedIn finder")

job_urls_input = st.text_area("Enter Upwork job URLs (one per line):", height=150)
job_urls = [url.strip() for url in job_urls_input.split("\n") if url.strip()]

high_trust_hire_rate = st.number_input("High-trust hire rate threshold (%)", 0, 100, 50)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9.\-+_]+@[a-zA-Z0-9.\-+_]+\.[a-zA-Z]+")

def find_emails_and_linkedin(soup, base_url=None):
    emails = set()
    linkedin_links = set()

    # 1) mailto: links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            addr = href.split("mailto:")[1].split("?")[0].strip()
            if EMAIL_REGEX.fullmatch(addr):
                emails.add(addr)

        # detect linkedin links
        if "linkedin.com/in" in href or "linkedin.com/pub" in href:
            linkedin_links.add(urljoin(base_url or "", href))

    # 2) search plain text for emails and linkedin urls
    text = soup.get_text(" ", strip=True)
    for m in EMAIL_REGEX.findall(text):
        emails.add(m)

    # linkedin pattern in text
    for m in re.findall(r"https?://[^\s'\"<>]*linkedin\.com[^\s'\"<>]*", text, flags=re.IGNORECASE):
        linkedin_links.add(m)

    return list(emails), list(linkedin_links)

def safe_get(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp
    except Exception:
        return None

def scrape_job(url):
    resp = safe_get(url)
    if not resp:
        return {"URL": url, "Error": "Unable to fetch page"}

    soup = BeautifulSoup(resp.text, "html.parser")

    # Basic fields (same as before)
    try:
        title = soup.find("h1").get_text(strip=True)
    except:
        title = None
    try:
        description = soup.find("section", {"data-test": "job-description"}).get_text(" ", strip=True)
    except:
        description = None
    try:
        skills = [s.get_text(strip=True) for s in soup.find_all("a", {"data-test": "skill-tag"})]
    except:
        skills = []

    # budget
    try:
        budget_elem = soup.find("strong", string=lambda x: x and "$" in x)
        budget = budget_elem.get_text(strip=True) if budget_elem else None
    except:
        budget = None

    # client info
    try:
        client_name_elem = soup.find("div", {"data-test": "client-name"})
        client_name = client_name_elem.get_text(strip=True)
        client_profile_link = client_name_elem.find("a")["href"] if client_name_elem and client_name_elem.find("a") else None
        if client_profile_link and client_profile_link.startswith("/"):
            # convert relative link to absolute if necessary
            client_profile_link = urljoin("https://www.upwork.com", client_profile_link)
    except:
        client_name = None
        client_profile_link = None

    try:
        client_location = soup.find("div", {"data-test": "client-location"}).get_text(strip=True)
    except:
        client_location = None

    try:
        payment_verified = bool(soup.find("span", string="Payment verified"))
    except:
        payment_verified = False

    try:
        hire_rate_text = soup.find("div", string=lambda x: x and "Hire rate" in x).get_text()
        hire_rate = int(hire_rate_text.split("%")[0])
    except:
        hire_rate = None

    high_trust = payment_verified and (hire_rate is not None and hire_rate >= high_trust_hire_rate) and (budget is not None)

    # Search this job page for emails / linkedin
    emails, linkedin_links = find_emails_and_linkedin(soup, base_url=url)

    # If there is a public client profile link, fetch and scan it too
    profile_emails = []
    profile_linkedin = []
    if client_profile_link:
        prof_resp = safe_get(client_profile_link)
        if prof_resp:
            prof_soup = BeautifulSoup(prof_resp.text, "html.parser")
            pe, pl = find_emails_and_linkedin(prof_soup, base_url=client_profile_link)
            profile_emails = pe
            profile_linkedin = pl

    # Combine and dedupe
    all_emails = sorted(set(emails + profile_emails))
    all_linkedin = sorted(set(linkedin_links + profile_linkedin))

    return {
        "URL": url,
        "Title": title,
        "Description": description,
        "Skills": ", ".join(skills),
        "Budget": budget,
        "Client Name": client_name,
        "Client Profile": client_profile_link,
        "Location": client_location,
        "Payment Verified": payment_verified,
        "Hire Rate": hire_rate,
        "High Trust Job": high_trust,
        "Public Emails Found": ", ".join(all_emails) if all_emails else None,
        "LinkedIn URLs Found": ", ".join(all_linkedin) if all_linkedin else None
    }

if st.button("Scrape Jobs"):
    if not job_urls:
        st.warning("Please enter at least one URL!")
    else:
        all_data = []
        for url in job_urls:
            st.write(f"Scraping {url}")
            all_data.append(scrape_job(url))
        df = pd.DataFrame(all_data)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "upwork_jobs_with_contacts.csv", "text/csv")
