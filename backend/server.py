from openai import OpenAI
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

# === CONFIGURATION ===
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') 
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY') 

client = OpenAI(api_key=OPENAI_API_KEY)

# === FUNCTION: Generate Optimized Search Query from Input ===
def generate_search_query(user_input):
    prompt = f"Generate a short, optimized YouTube search query for the topic: {user_input}"
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# === FUNCTION: Search YouTube and Return Most Viewed Video ===
def search_youtube(query, max_results=5):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    # Search for videos matching the query
    search_response = youtube.search().list(
        q=query,
        part='id,snippet',
        maxResults=max_results,
        type='video'
    ).execute()

    videos = []
    for item in search_response['items']:
        video_id = item['id']['videoId']
        video_details = youtube.videos().list(
            id=video_id,
            part='statistics,snippet'
        ).execute()
        if video_details['items']:
            stats = video_details['items'][0]['statistics']
            title = video_details['items'][0]['snippet']['title']
            view_count = int(stats.get('viewCount', 0))
            videos.append({
                'video_id': video_id,
                'title': title,
                'views': view_count
            })

    # Sort by views
    videos.sort(key=lambda x: x['views'], reverse=True)

    if videos:
        top_video = videos[0]
        video_url = f"https://www.youtube.com/watch?v={top_video['video_id']}"
        return top_video['title'], video_url, top_video['views']
    else:
        return None, None, None

# === MAIN ===
if __name__ == '__main__':
    user_input = input("Enter your topic: ")

    print("🧠 Generating smart search query...")
    search_query = generate_search_query(user_input)

    print(f"🔍 Searching YouTube for: {search_query}")
    title, url, views = search_youtube(search_query)

    if url:
        print(f"\n🎯 Top Video Found:\nTitle: {title}\nViews: {views:,}\nLink: {url}")
    else:
        print("No relevant videos found.")