import os
import requests
from apify_client import ApifyClient
from google import genai

# Load environment variables (We will put these in GitHub next)
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

apify_client = ApifyClient(APIFY_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def fetch_quora_questions(keyword):
    print(f"Scraping Quora for: {keyword}")
    run_input = {
        "startUrls": [{"url": f"https://www.quora.com/search?q={keyword}&type=question"}],
        "maxItems": 3
    }
    run = apify_client.actor("fatihtahta/quora-scraper").call(run_input=run_input)
    return list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())

def draft_answer(question_text):
    print(f"Drafting answer for: {question_text}")
    prompt = f"""
    You are the Senior Brand Strategist for Petnivo, a pet wellness and care brand.
    Quora Question: "{question_text}"
    
    Task: Write an authoritative, deeply helpful response. Provide 90% pure educational value. Subtly reference Petnivo's product standards, transparency, or packaging where contextually relevant. Use bullet points and clean formatting. Do not sound like a spam advertisement.
    """
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def push_to_notion(title, url, draft):
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
        print(f"Error: {response.text}")

if __name__ == "__main__":
    # Your target keywords to search Quora for daily
    keywords = ["dog health supplements", "sustainable pet care", "pet food packaging"]
    
    for keyword in keywords:
        scraped_data = fetch_quora_questions(keyword)
        for item in scraped_data:
            q_title = item.get("title", "Unknown Question")
            q_url = item.get("url", "")
            
            if q_title and q_title != "Unknown Question":
                ai_draft = draft_answer(q_title)
                push_to_notion(q_title, q_url, ai_draft)