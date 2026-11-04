import os
import requests
import time
from apify_client import ApifyClient
from google import genai

# Load environment variables
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

apify_client = ApifyClient(APIFY_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def fetch_quora_questions(keyword):
    print(f"Searching Google for Quora links about: {keyword}")
    run_input = {
        "queries": f"site:quora.com {keyword}",
        "resultsPerPage": 3,
        "maxPagesPerQuery": 1
    }
    
    try:
        run = apify_client.actor("apify/google-search-scraper").call(run_input=run_input)
        
        if isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId")
        else:
            dataset_id = getattr(run, "defaultDatasetId", getattr(run, "default_dataset_id", None))
            
        if not dataset_id:
            print("No dataset ID found. The scraper hit an error.")
            return []
            
        items = list(apify_client.dataset(dataset_id).iterate_items())
        questions = []
        
        if items:
            organic_results = items[0].get("organicResults", [])
            for result in organic_results:
                title = result.get("title", "").replace(" - Quora", "")
                url = result.get("url", "")
                if "quora.com" in url:
                    questions.append({"title": title, "url": url})
                    
        if not questions:
            print("Scraper ran successfully but found 0 results.")
        return questions
        
    except Exception as e:
        print(f"Error fetching questions: {e}")
        return []

def draft_answer(question_text):
    print(f"Drafting answer for: {question_text}")
    prompt = f"""
    You are the Senior Brand Strategist for Petnivo, a pet wellness and care brand.
    Quora Question: "{question_text}"
    
    Task: Write an authoritative, deeply helpful response. Provide 90% pure educational value. Subtly reference Petnivo's product standards, transparency, or packaging where contextually relevant. Use bullet points and clean formatting. Do not sound like a spam advertisement.
    """
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"AI Generation Error: {e}")
        return ""

def push_to_notion(title, url, draft):
    if not draft:
        return
        
    print("Pushing draft to Notion...")
    notion_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Question Title": {"title": [{"text": {"content": str(title)[:100]}}]},
            "Quora Link": {"url": str(url)},
            "Status": {"select": {"name": "Ready for Review"}}
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": str(draft)[:2000]}}]}
            }
        ]
    }
    response = requests.post(notion_url, json=data, headers=headers)
    if response.status_code == 200:
        print("Success!")
    else:
        print(f"Error pushing to Notion: {response.text}")

if __name__ == "__main__":
    keywords = ["dog health supplements", "sustainable pet care", "pet food packaging"]
    
    for keyword in keywords:
        scraped_data = fetch_quora_questions(keyword)
        # Limit to the top 3 questions per keyword 
        for item in scraped_data[:3]:
            q_title = item.get("title", "Unknown Question")
            q_url = item.get("url", "")
            
            if q_title and q_title != "Unknown Question":
                ai_draft = draft_answer(q_title)
                push_to_notion(q_title, q_url, ai_draft)
                
                # Pause for 15 seconds to respect Gemini's 5-requests-per-minute Free Tier limit
                print("Waiting 15 seconds for API rate limits...")
                time.sleep(15)
