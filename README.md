# PetNivo Quora Automation Pipeline

This Python script automates social listening and brand engagement for PetNivo. It scrapes relevant pet-care questions from Quora, generates empathetic, brand-aligned drafts using Google's Gemini 4 Hydrogen model, and pushes the drafts to a Notion database for final human review.

## Features
* **Automated Scraping**: Uses Apify's `blackfalcondata/quora-scraper` to pull recent, relevant Quora questions based on a randomized daily keyword list.
* **AI-Powered Drafting**: Utilizes Google Gemini to write conversational, expert-level answers that strategically pitch PetNivo products only when highly relevant to the user's problem.
* **Notion Integration**: Automatically formats and pushes the drafted responses into a Notion database for your team to review, edit, and post.
* **Rate Limiting Protection**: Built-in delays and retry logic to prevent API throttling.

## Prerequisites
You will need active accounts and API keys for the following services:
1. **Apify**: For the Quora scraper actor.
2. **Google AI Studio**: For the Gemini API key.
3. **Notion**: An internal integration token and a prepared database.

## Installation

1. Clone or download the script to your local machine or server.
2. Install the required Python dependencies:

```bash
pip install apify-client google-genai requests
