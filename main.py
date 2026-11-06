import os
import requests
import time
import random  # Imported to allow randomization
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
        "resultsPerPage": 10,  # Pull more results so we have a pool to randomly pick from
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

def draft_answer(question_text, retries=3):
    print(f"Drafting answer for: {question_text}")
    
    # MASTER PROMPT: Fed with your exact PetNivo product catalog and strict humanizing rules
    prompt = f"""
    You are the Senior Brand Strategist for PetNivo, a premium Indian pet hygiene and grooming brand.
    Write a highly conversational, empathetic, and human-sounding response to this Quora question: "{question_text}"

    Our Product Catalog (DO NOT list these out, just know them):
    1. Tick & Flea Shampoo: Plant-powered (Neem, Peppermint, Eucalyptus), sulphate/paraben-free. Repels ticks, soothes bites.
    2. Anti-Dandruff & Itch Shampoo: Neem & Tea Tree. Soothes itchy skin and flakiness.
    3. Silky Coat Conditioner: Aloe, Coconut Oil, Oat extract. Detangles, softens, reduces static.
    4. Dry Bath Foam: Waterless cleanser with Neem & Aloe. Great for quick cleanups.
    5. Earth Lap Pet Wipes: Fragrance-free, pH balanced with Chamomile. Perfect for muddy paws or face wipe-downs.
    6. Paw Balm: 100% lick-safe, Shea butter, Beeswax, Hemp seed oil. Soothes dry/cracked paws and noses.

    RULES FOR WRITING:
    1. Write like a passionate, knowledgeable pet owner talking to a friend. Do not use robotic AI jargon like "In conclusion" or "Here are a few things to consider."
    2. Give the direct answer immediately in the first paragraph.
    3. THE GOLDEN RULE: ONLY pitch a product if it directly solves the user's problem. 
       - If they ask about ticks, explain how to pull them out with tweezers, then casually mention our Tick & Flea shampoo for aftercare to soothe the skin.
       - If they ask about dry paws, give winter care tips and mention our 100% lick-safe Paw Balm.
    4. IF THE QUESTION IS UNRELATED TO HYGIENE (e.g., "why does my dog eat grass", "best diet for senior dogs", "trouble chewing"): DO NOT pitch any products. Just give amazing, caring advice to build brand authority, and sign off warmly as the PetNivo Team.
    """
    
    for attempt in range(retries):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_msg = str(e)
            print(f"AI Generation Error (Attempt {attempt + 1}): {error_msg}")
            
            if "429" in error_msg:
                print("Daily quota exceeded. Skipping AI generation.")
                return ""
            elif "503" in error_msg and attempt < retries - 1:
                print("Server busy. Retrying in 20 seconds...")
                time.sleep(20)
            else:
                return ""
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
    # A massive master list mixing specific hygiene products and general pet advice
    master_keywords = [
        # Petnivo Specific Products
        "dog itchy skin relief", "how to remove dog ticks", "are pet wipes safe for dogs",
        "best paw balm for cracked dog paws", "dog conditioner for dry coat",
        "how often should i bathe my dog", "natural flea and tick prevention for dogs",
        
        # General Pet Health & Care
        "how to train a puppy to stop biting", "best diet for senior dogs",
        "why does my dog eat grass", "how to calm an anxious dog during storms",
        "how much exercise does a dog need daily", "tips for adopting a rescue dog"
    ]
    
    # 1. Randomly select 3 topics to cover today (keeps your daily content fresh)
    todays_keywords = random.sample(master_keywords, 3)
    print(f"Today's randomly selected topics: {todays_keywords}")
    
    for keyword in todays_keywords:
        scraped_data = fetch_quora_questions(keyword)
        
        # 2. Randomly select 3 questions from the scraped pool (prevents answering the same top Google result every day)
        sample_size = min(3, len(scraped_data)) 
        if sample_size > 0:
            random_questions = random.sample(scraped_data, sample_size)
            
            for item in random_questions:
                q_title = item.get("title", "Unknown Question")
                q_url = item.get("url", "")
                
                if q_title and q_title != "Unknown Question":
                    ai_draft = draft_answer(q_title)
                    
                    if ai_draft:
                        push_to_notion(q_title, q_url, ai_draft)
                        print("Waiting 20 seconds for API rate limits...")
                        time.sleep(20)
