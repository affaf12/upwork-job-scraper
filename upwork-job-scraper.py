import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

st.title("Upwork Job Scraper (Cloud-friendly)")

job_urls_input = st.text_area("Enter Upwork job URLs (one per line):")
job_urls = [url.strip() for url in job_urls_input.split("\n") if url.strip()]

high_trust_hire_rate = st.number_input("High-trust hire rate threshold (%)", 0, 100, 50)

def scrape_job(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    try: title = soup.find("h1").get_text(strip=True)
    except: title = None
    try: description = soup.find("section", {"data-test": "job-description"}).get_text(" ", strip=True)
    except: description = None
    try: skills = [s.get_text(strip=True) for s in soup.find_all("a", {"data-test": "skill-tag"})]
    except: skills = []

    try: budget_elem = soup.find("strong", string=lambda x: x and "$" in x)
    budget = budget_elem.get_text(strip=True) if budget_elem else None
    except: budget = None

    try: client_name_elem = soup.find("div", {"data-test": "client-name"})
    client_name = client_name_elem.get_text(strip=True)
    client_profile_link = client_name_elem.find("a")["href"] if client_name_elem.find("a") else None
    except: client_name = client_profile_link = None

    try: client_location = soup.find("div", {"data-test": "client-location"}).get_text(strip=True)
    except: client_location = None

    try: payment_verified = bool(soup.find("span", string="Payment verified"))
    except: payment_verified = False

    try: hire_rate_text = soup.find("div", string=lambda x: x and "Hire rate" in x).get_text()
    hire_rate = int(hire_rate_text.split("%")[0])
    except: hire_rate = None

    high_trust = payment_verified and (hire_rate is not None and hire_rate >= high_trust_hire_rate) and (budget is not None)

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
        "High Trust Job": high_trust
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
        st.download_button("Download CSV", csv, "upwork_jobs.csv", "text/csv")
