# Automated Resume Evaluation and Role Tracking System

This system automatically analyzes a resume, recommends job roles that match the candidate's background, scrapes real-time job listings from JobStreet, and ranks them based on relevance using AI.

##  Features
- Resume parsing from PDF, DOCX, JPG, or PNG
- Role suggestion based on extracted resume content
- Live job scraping from JobStreet
- Job listing deduplication and relevance scoring
- Ranks job listings using Gemini Pro API
- Saves ranked results to a text file

##  Technologies Used
- Python
- Playwright (for web scraping)
- Gemini API (via Google Generative AI)
- Tesseract OCR (image text extraction)
- BeautifulSoup (HTML parsing)
- PyMuPDF, python-docx (document parsing)
- dotenv (for API key management)

##  How to Run
1. Clone the repository:
2. Install the requirements:
3. Add your Gemini API key to a `.env` file:   
4. Run the program

## Example Usage
$ py main.py

Enter the full path to your resume file (PDF, DOCX, JPG, PNG): C:\Users\...\resume1.jpg
Extracting resume text...
Analyzing resume to suggest job roles...

Suggested Job Roles:

Here are 5 job roles that match the candidate's skills and background:

1. Data Scientist
2. Data Analyst
3. Machine Learning Engineer
4. Software Engineer (with a focus on data)
5. Business Intelligence Analyst

Select a job role number from the list above (e.g., 1): 2
Enter the number of job listings to scrape: 10

Starting job scraping for 'Data Analyst' (10 listings)...

Step 1: Collecting job links from search results...
Page 1: 10 jobs collected

Step 2: Scraping 10 job descriptions...
Scraped 10 descriptions in 17.73s
Saved 10 jobs to data\jobstreet_data-analyst_jobs.txt
Saved CSV to data\jobstreet_data-analyst_10_data.csv

Reading job listings from: data/jobstreet_data-analyst_jobs.txt
Ranking jobs based on your resume...
Analyzing 10 job listings...

Job Matches Based on Your Resume:

1. Power BI-focused Reporting & Analytics Analyst | WFH - 9/10
   This role is a strong fit, as the job description explicitly seeks expertise in Power BI and data analysis and aligns directly with the candidate's skills and experience. The required experience of 5+ years is a potential barrier.

2. Data Analyst at RiteMed Phils., Inc. - 7/10
   The job description aligns well with the candidate's skills in data analysis and visualization using tools like Power BI. However, the requirement for "at least 1 year experience" might be a barrier given recent graduation.

...

10. Billing Analyst - Mckinley Hill - Data Analysis at HCL Technologies Philippines Inc - 2/10
    This position is focused on billing and client relations, which is quite different from the candidate's data science background. The role requires customer service skills and an understanding of billing processes.

Ranking results saved to: ranked_jobs_data-analyst_output.txt
