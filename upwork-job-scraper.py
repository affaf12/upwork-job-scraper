import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import os

# --------------------------
# Configuration
# --------------------------
job_urls = [
    "https://www.upwork.com/jobs/~021975670761803497049",
    # Add more URLs here
]

high_trust_hire_rate = 50  # % threshold
save_screenshots = True  # Set to False if you don't want screenshots
screenshot_folder = "screenshots"

if save_screenshots and not os.path.exists(screenshot_folder):
    os.makedirs(screenshot_folder)

# Selenium setup for screenshots
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
service = Service()  # You can specify ChromeDriver path here if needed
driver = webdriver.Chrome(service=service, options=chrome_options)

data = []

# --------------------------
# Scraper function
# --------------------------
def scrape_job(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Job info
    try:
        title = soup.find("h1").get_text(strip=True)
    except:
        title = None

    try:
        description = soup.find("section", {"data-test": "job-description"}).get_text(separator=" ", strip=True)
    except:
        description = None

    try:
        skills = [s.get_text(strip=True) for s in soup.find_all("a", {"data-test": "skill-tag"})]
    except:
        skills = []

    try:
        budget_elem = soup.find("strong", string=lambda x: x and "$" in x)
        budget = budget_elem.get_text(strip=True) if budget_elem else None
    except:
        budget = None

    # Client info
    try:
        client_name_elem = soup.find("div", {"data-test": "client-name"})
        client_name = client_name_elem.get_text(strip=True)
        client_profile_link = client_name_elem.find("a")["href"] if client_name_elem.find("a") else None
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

    # High-trust job: payment verified + hire rate ≥ threshold + fixed budget
    high_trust = payment_verified and (hire_rate is not None and hire_rate >= high_trust_hire_rate) and (budget is not None)

    # Save screenshot using Selenium
    screenshot_path = None
    if save_screenshots:
        driver.get(url)
        time.sleep(3)  # wait for page to load
        filename = url.split("/")[-1] + ".png"
        screenshot_path = os.path.join(screenshot_folder, filename)
        driver.save_screenshot(screenshot_path)

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
        "Screenshot": screenshot_path
    }

# --------------------------
# Run scraper
# --------------------------
for url in job_urls:
    print(f"Scraping {url} ...")
    job_data = scrape_job(url)
    data.append(job_data)

# --------------------------
# Export to CSV
# --------------------------
df = pd.DataFrame(data)
df.to_csv("upwork_jobs_enhanced.csv", index=False)
print("Data saved to upwork_jobs_enhanced.csv")

# Close Selenium driver
driver.quit()
