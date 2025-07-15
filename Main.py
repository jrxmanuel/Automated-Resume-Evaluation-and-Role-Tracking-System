import os
import re
from dotenv import load_dotenv
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from docx import Document
import google.generativeai as genai
from WebScraper import main as scrape_main

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# ==== Extract resume text ====
def extract_text_from_file(file_path):
    try:
        if file_path.lower().endswith((".jpg", ".jpeg", ".png")):
            image = Image.open(file_path)
            return pytesseract.image_to_string(image).strip()

        elif file_path.lower().endswith(".pdf"):
            text = ""
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            return text.strip()

        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs]).strip()

        else:
            print("Unsupported file format. Please use JPG, PNG, PDF, or DOCX.")
            return ""

    except Exception as e:
        print(f"[File Read ERROR] {e}")
        return ""

# ==== Ask Gemini for job role suggestions ====
def suggest_roles_from_resume(resume_text):
    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    prompt = (
        "You are a career advisor. Based on the following resume text, suggest 5 job roles "
        "that match the candidate's skills and background:\n\n"
        f"{resume_text}\n\n"
        "Return the suggestions as a numbered list and only the job role:\n1. Job Role A\n2. Job Role B\n..."
    )
    response = model.generate_content(prompt)
    return response.text.strip()

# ==== Parse job ranking response ====
def parse_job_rankings(response_text):
    """Parse the Gemini response and extract job rankings"""
    jobs = []
    lines = response_text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Check if this is a numbered job entry
        match = re.match(r'^(\d+)\.\s*(.*?)\s*-\s*(\d+)/10\s*$', line)
        if match:
            job_title_company = match.group(2).strip()
            score = int(match.group(3))
            
            # Look for explanation in the next few lines
            explanation_lines = []
            i += 1
            
            # Collect explanation lines until we hit another numbered entry or end
            while i < len(lines):
                next_line = lines[i].strip()
                
                # If we hit another numbered entry, stop collecting explanation
                if re.match(r'^(\d+)\.\s*(.*?)\s*-\s*(\d+)/10\s*$', next_line):
                    break
                
                # If it's not empty, add to explanation
                if next_line:
                    explanation_lines.append(next_line)
                
                i += 1
            
            # Create job entry
            jobs.append({
                'title_company': job_title_company,
                'score': score,
                'explanation': ' '.join(explanation_lines)
            })
            
            # Don't increment i here since we've already processed up to the next entry
            continue
        else:
            # Skip lines that don't match the expected format
            i += 1
    
    return jobs

# ==== Better duplicate removal ====
def remove_duplicates(all_jobs):
    """Remove duplicate jobs based on company name and job title"""
    seen = set()
    unique_jobs = []
    
    for job in all_jobs:
        # Extract company name and job title for comparison
        title_company = job['title_company'].lower()
        
        # Create a normalized key for duplicate detection
        normalized_key = re.sub(r'\s+', ' ', title_company.strip())
        normalized_key = re.sub(r'\s*(?:at|@|-)\s*', ' at ', normalized_key)
        
        if normalized_key not in seen:
            seen.add(normalized_key)
            unique_jobs.append(job)
    
    return unique_jobs

# ==== Debug the job file ====
def debug_job_file(filename):
    """Debug function to check how many jobs are actually in the file"""
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    
    return content

# ==== Ask Gemini to rank jobs ====
def rank_jobs_with_gemini(resume_text, jobs_text):
    model = genai.GenerativeModel("gemini-2.0-flash-lite")

    def split_text(text, max_chars=100000):
        # If text is small enough, don't split it
        if len(text) <= max_chars:
            return [text]
            
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            
            # If we're at the end, take the rest
            if end >= len(text):
                chunks.append(text[start:].strip())
                break
                
            # Find a good place to split (look for job separators)
            split_at = text.rfind("\nJob ", start, end)  # Look for "Job X:" pattern
            if split_at == -1 or split_at <= start:
                split_at = text.rfind("\n---", start, end)  # Look for job separators
            if split_at == -1 or split_at <= start:
                split_at = text.rfind("\n\n", start, end)  # Look for double newlines
            if split_at == -1 or split_at <= start:
                split_at = end
                
            chunk = text[start:split_at].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            start = split_at
            
        return [chunk for chunk in chunks if chunk.strip()]  # Remove empty chunks

    job_batches = split_text(jobs_text)
    all_jobs = []

    for i, batch in enumerate(job_batches, start=1):
        # Skip empty or tiny batches (this is where the hallucination happens!)
        if len(batch.strip()) < 100:
            continue
        
        prompt = (
            "You are a career advisor.\n\n"
            f"Candidate Resume:\n{resume_text}\n\n"
            f"Job Listings:\n{batch}\n\n"
            "Evaluate how well each job matches the resume, be realistic and stricly no sugarcoating. Score each job from 1 to 10 based on relevance.\n\n"
            "Respond in this EXACT format:\n"
            "1. <Job Title> at <Company> - <Score>/10\n"
            "<Explanation in 2 sentences>\n"
            "2. <Job Title> at <Company> - <Score>/10\n"
            "<Explanation in 2 sentences>\n\n"
            "Only use the provided information. Do not create additional jobs. If no jobs are provided, respond with 'No jobs to evaluate.'"
        )
        
        try:
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Skip if Gemini says no jobs to evaluate
            if "No jobs to evaluate" in response_text:
                continue
                
            batch_jobs = parse_job_rankings(response_text)
            all_jobs.extend(batch_jobs)
                
        except Exception as e:
            print(f"Error processing batch {i}: {e}")
            continue

    print(f"Analyzing {len(all_jobs)} job listings...")

    # Remove duplicates
    unique_jobs = remove_duplicates(all_jobs)
    
    # Only show duplicate removal message if duplicates were actually found
    if len(all_jobs) > len(unique_jobs):
        print(f"Removed {len(all_jobs) - len(unique_jobs)} duplicate(s)")
    
    # Sort by score (descending)
    unique_jobs.sort(key=lambda x: x['score'], reverse=True)
    
    # Format final output
    final_output = f"Job Matches Based on Your Resume:\n\n"
    for i, job in enumerate(unique_jobs, 1):
        final_output += f"{i}. {job['title_company']} - {job['score']}/10\n"
        final_output += f"{job['explanation']}\n\n"
    
    return final_output.strip()

# ==== Main ====
def main():
    resume_path = input("Enter the full path to your resume file (PDF, DOCX, JPG, PNG): ").strip()
    if not os.path.exists(resume_path):
        print("File not found. Please check the path and try again.")
        return

    print("Extracting resume text...")
    resume_text = extract_text_from_file(resume_path)
    if not resume_text:
        print("Failed to extract resume text.")
        return

    print("Analyzing resume to suggest job roles...")
    suggestions_raw = suggest_roles_from_resume(resume_text)
    print("\nSuggested Job Roles:\n")
    print(suggestions_raw)

    # Parse job roles
    suggested_roles = []
    for line in suggestions_raw.splitlines():
        match = re.match(r"\d+\.\s*(.*)", line.strip())
        if match:
            suggested_roles.append(match.group(1).strip())

    if not suggested_roles:
        print("Could not parse any job role suggestions.")
        return

    try:
        selected_index = int(input("\nSelect a job role number from the list above (e.g., 1): ").strip())
        selected_role = suggested_roles[selected_index - 1]
    except (ValueError, IndexError):
        print("Invalid selection. Please enter a valid number.")
        return

    try:
        max_jobs = int(input("Enter the number of job listings to scrape: ").strip())
    except ValueError:
        print("Invalid input. Please enter a number.")
        return

    print(f"\nStarting job scraping for '{selected_role}' ({max_jobs} listings)...")
    job_role_clean = selected_role.strip().lower().replace(" ", "-")
    filename = f"data/jobstreet_{job_role_clean}_jobs.txt"

    import asyncio
    asyncio.run(scrape_main(selected_role, max_jobs))

    if not os.path.exists(filename):
        print("Scraped job data file not found.")
        return

    print(f"\nReading job listings from: {filename}")
    
    # Debug the job file first
    jobs_text = debug_job_file(filename)

    print("Ranking jobs based on your resume...")
    rankings = rank_jobs_with_gemini(resume_text, jobs_text)

    print("\nJob Matches Based on Your Resume:\n")
    print(rankings)

    # Save results
    output_filename = f"ranked_jobs_{job_role_clean}_output.txt"
    with open(output_filename, "w", encoding="utf-8") as out_file:
        out_file.write(rankings)
    print(f"\nRanking results saved to: {output_filename}")

if __name__ == "__main__":
    main()