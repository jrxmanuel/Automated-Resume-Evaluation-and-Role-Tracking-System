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


