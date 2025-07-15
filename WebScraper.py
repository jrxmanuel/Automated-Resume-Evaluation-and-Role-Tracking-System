import csv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os
import re
import asyncio
from playwright.async_api import async_playwright
import time

async def scrape_job_description(url, browser):
    try:
        page = await browser.new_page()
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        await page.goto(url, wait_until="load", timeout=15000)
        await page.wait_for_timeout(2000)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        description_section = soup.select_one("div[data-automation='jobAdDetails']")
        if description_section:
            description_elements = description_section.find_all(['h2', 'p', 'ul', 'hr', 'li'])
            job_description_parts = []
            seen_texts = set()

            for elem in description_elements:
                text = elem.get_text(separator='\n', strip=True)
                if text and text not in seen_texts:
                    job_description_parts.append(text)
                    seen_texts.add(text)

            await page.close()
            return "\n".join(job_description_parts)

        await page.close()
        return "Description not found"
    except Exception as e:
        if 'page' in locals():
            await page.close()
        return f"Error: {str(e)}"

async def scrape_descriptions_batch(job_links, browser, batch_size=10):
    results = {}

    for i in range(0, len(job_links), batch_size):
        batch = job_links[i:i + batch_size]
        tasks = [scrape_job_description(link, browser) for link in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for job_link, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                results[job_link] = f"Error: {str(result)}"
            else:
                results[job_link] = result

        await asyncio.sleep(1)

    return results

def extract_job_cards_data(soup):
    job_cards = soup.select("article[data-automation='normalJob']")
    if not job_cards:
        job_cards = soup.select("div[data-automation='normalJob']")

    jobs_data = []

    for card in job_cards:
        try:
            job_title_el = card.select_one("a[data-automation='jobTitle']")
            if not job_title_el:
                continue

            job_title = job_title_el.text.strip()
            relative_job_link = job_title_el.get("href", "")
            base_url = "https://ph.jobstreet.com"
            job_link = f"{base_url}{relative_job_link}" if relative_job_link.startswith("/") else f"{base_url}/{relative_job_link}"

            company_el = card.select_one("a[data-automation='jobCompany']")
            company = company_el.text.strip() if company_el else "N/A"

            location_el = card.select_one("a[data-automation='jobLocation']")
            location = location_el.text.strip() if location_el else "N/A"

            work_arrangement_el = card.select_one("span[data-testid='work-arrangement']")
            work_arrangement = work_arrangement_el.text.strip() if work_arrangement_el else "N/A"

            job_date_el = card.select_one("span[data-automation='jobListingDate']")
            job_date = job_date_el.text.strip() if job_date_el else "N/A"

            salary_el = card.select_one("span[data-automation='jobSalary']")
            min_salary = max_salary = "N/A"
            if salary_el and salary_el.text.strip() != "Salary not specified":
                salary_text = salary_el.text.strip()
                numbers = re.findall(r'[\d,]+', salary_text)
                if len(numbers) >= 2:
                    salary_nums = sorted([int(n.replace(',', '')) for n in numbers])
                    min_salary, max_salary = str(salary_nums[0]), str(salary_nums[-1])
                elif len(numbers) == 1:
                    min_salary = max_salary = str(int(numbers[0].replace(',', '')))

            jobs_data.append({
                "job_title": job_title,
                "company": company,
                "link": job_link,
                "location": location,
                "work_arrangement": work_arrangement,
                "job_date": job_date,
                "min_salary": min_salary,
                "max_salary": max_salary,
            })
        except Exception as e:
            print(f"Error processing job card: {e}")
            continue

    return jobs_data

async def main(job_role, max_jobs):
    job_role_clean = job_role.strip().lower().replace(" ", "-")
    url = f"https://ph.jobstreet.com/{job_role_clean}-jobs/in-Metro-Manila"

    print("Step 1: Collecting job links from search results...")
    all_jobs_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-web-security'
        ])
        page = await browser.new_page()
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        current_page = 1
        while len(all_jobs_data) < max_jobs:
            try:
                await page.goto(url, wait_until="load", timeout=15000)
                await page.wait_for_timeout(3000)
                soup = BeautifulSoup(await page.content(), "html.parser")

                page_jobs = extract_job_cards_data(soup)
                if not page_jobs:
                    break

                all_jobs_data.extend(page_jobs[:max_jobs - len(all_jobs_data)])
                print(f"Page {current_page}: {len(all_jobs_data)} jobs collected")

                if len(all_jobs_data) >= max_jobs:
                    break

                next_btn = await page.query_selector('a[aria-label="Next"]')
                if not next_btn:
                    break
                await next_btn.click()
                await page.wait_for_timeout(3000)
                current_page += 1
            except Exception as e:
                print(f"Error on page {current_page}: {e}")
                break

        await browser.close()

    print(f"\nStep 2: Scraping {len(all_jobs_data)} job descriptions...")
    job_links = [job['link'] for job in all_jobs_data]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-web-security'
        ])
        start_time = time.time()
        descriptions = await scrape_descriptions_batch(job_links, browser, batch_size=5)
        print(f"Scraped {len(descriptions)} descriptions in {time.time() - start_time:.2f}s")
        await browser.close()

    for job in all_jobs_data:
        job['job_description'] = descriptions.get(job['link'], 'N/A')

    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)

    # Save TXT
    txt_filename = os.path.join(output_dir, f"jobstreet_{job_role_clean}_jobs.txt")
    with open(txt_filename, "w", encoding="utf-8") as f:
        for i, job in enumerate(all_jobs_data, 1):
            f.write(f"Job {i}:\n")
            f.write(f"Company: {job['company']}\n")
            f.write(f"Title: {job['job_title']}\n")
            f.write(f"Description: {job['job_description']}\n\n")
    print(f"✅ Saved {len(all_jobs_data)} jobs to {txt_filename}")

    # Save CSV
    csv_filename = os.path.join(output_dir, f"jobstreet_{job_role_clean}_{len(all_jobs_data)}_data.csv")
    with open(csv_filename, "w", encoding="utf-8", newline="") as csvfile:
        fieldnames = [
            "Job Title", "Company", "Location", "Work Arrangement", "Job Date",
            "Min Salary", "Max Salary", "Average Salary"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for job in all_jobs_data:
            try:
                min_salary = int(job["min_salary"]) if job["min_salary"].isdigit() else 0
                max_salary = int(job["max_salary"]) if job["max_salary"].isdigit() else 0
                avg_salary = (min_salary + max_salary) // 2 if min_salary and max_salary else "N/A"
            except:
                avg_salary = "N/A"

            writer.writerow({
                "Job Title": job["job_title"],
                "Company": job["company"],
                "Location": job["location"],
                "Work Arrangement": job["work_arrangement"],
                "Job Date": job["job_date"],
                "Min Salary": job["min_salary"],
                "Max Salary": job["max_salary"],
                "Average Salary": avg_salary
            })
    print(f"📄 Saved CSV to {csv_filename} 🎉")

# Usage from another script:
# asyncio.run(main("Data Analyst", 50))
