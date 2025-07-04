from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
from typing import List, Dict

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")
if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY environment variable is required")

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_best_search_query(user_input):
    prompt = (
        f"You are generating YouTube search queries specifically for math problems.\n\n"
        f"The user input is a trigonometry expression or math question: \"{user_input}\"\n\n"
        f"Generate a YouTube search query that includes the **exact same expression** (no rewriting), "
        f"formatted in a way that someone would realistically search for it on YouTube.\n"
        f"Do NOT explain the expression. Do NOT rephrase. Just wrap it in a helpful search phrase.\n\n"
        f"Example format: 'How to solve <expression>' or 'Solve <expression> step by step'\n\n"
        f"Output only the search query."
    )
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    print(f"OpenAI response: {response.choices[0].message.content}")
    
    content = response.choices[0].message.content
    # Extract just the best query using simple parsing
    for line in content.splitlines():
        if line.lower().startswith("best query:"):
            return line.split(":", 1)[1].strip()
    
    # Fallback: return first valid query line
    for line in content.splitlines():
        if line.strip().startswith("-"):
            return line.strip("- ").strip()
    
    return user_input  # fallback to original message


# Request/Response models
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
    video_id: str
    video_url: str
    video_title: str
    video_views: int

# === FUNCTION: Generate Optimized Search Query from Input ===
def generate_search_query(user_input):
    prompt = f"Generate a short, optimized YouTube search query for the topic: {user_input}"
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# === FUNCTION: Search YouTube and Return Most Viewed Video ===
def search_youtube(query, max_results=15):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    try:
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=max_results,
            type='video',
            order='relevance'  # prioritize relevant results
        ).execute()

        videos = []
        for item in search_response['items']:
            video_id = item['id']['videoId']
            snippet = item['snippet']
            title = snippet['title']
            description = snippet.get('description', '')

            video_details = youtube.videos().list(
                id=video_id,
                part='statistics'
            ).execute()

            if video_details['items']:
                stats = video_details['items'][0]['statistics']
                view_count = int(stats.get('viewCount', 0))

                videos.append({
                    'video_id': video_id,
                    'title': title,
                    'description': description,
                    'views': view_count
                })

        # ✅ ADD THIS BLOCK RIGHT HERE
        # Prioritize exact matches (or close string matches) in title or description
        expression = query.strip().lower()
        exact_matches = [
            v for v in videos
            if expression in v['title'].lower() or expression in v['description'].lower()
        ]
        if exact_matches:
            top_video = exact_matches[0]
        else:
            # Sort by views as fallback
            videos.sort(key=lambda x: x['views'], reverse=True)
            top_video = videos[0] if videos else None

        if top_video:
            video_url = f"https://www.youtube.com/watch?v={top_video['video_id']}"
            return top_video['title'], video_url, top_video['views'], top_video['video_id']
        else:
            return None, None, None, None

    except Exception as e:
        print(f"YouTube API error: {e}")
        return None, None, None, None


# === FUNCTION: Generate AI Response ===
def generate_ai_response(user_input):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a friendly and knowledgeable math teacher. When a student sends a math expression or problem, you respond as if you're explaining it step by step in a clear and patient way. Use simple, encouraging language, and aim to teach the concept behind the question. If the question is unclear, try to interpret it based on what a student might mean. End with a helpful tip or encouragement if appropriate."},
                {"role": "user", "content": user_input}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return f"Thanks for your message about: {user_input}. I've found a relevant video for you!"

@app.get("/")
async def root():
    return {"message": "YouTube Chat Video API with AI Search is running!"}

@app.post("/chat", response_model=ChatResponse)
async def chat_with_video(chat_message: ChatMessage):
    try:
        print(f"🧠 Processing message: {chat_message.message}")
        
        # Generate AI response
        ai_response = generate_ai_response(chat_message.message)
        
        # Generate optimized search query
        print("🧠 Generating smart search query...")
        search_query = generate_best_search_query(chat_message.message)
        print(f"🔍 Searching YouTube for: {search_query}")
        
        # Search YouTube for the most viewed video
        title, video_url, views, video_id = search_youtube(search_query)
        
        if video_url:
            print(f"🎯 Top Video Found: {title} ({views:,} views)")
            return ChatResponse(
                reply=ai_response,
                video_id=video_id,
                video_url=video_url,
                video_title=title,
                video_views=views
            )
        else:
            # Fallback to a default video if no results found
            print("⚠️ No relevant videos found, using fallback")
            fallback_video_id = "dQw4w9WgXcQ"  # Rick Roll as fallback
            return ChatResponse(
                reply=f"{ai_response} (Note: I couldn't find a specific video for your query, so here's a classic!)",
                video_id=fallback_video_id,
                video_url=f"https://www.youtube.com/watch?v={fallback_video_id}",
                video_title="Rick Astley - Never Gonna Give You Up",
                video_views=1000000000
            )
    
    except Exception as e:
        print(f"Error in chat_with_video: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.get("/random-video")
async def get_random_video():
    """Endpoint to get a random video by searching for trending topics"""
    try:
        # Search for trending content
        trending_queries = ["trending", "popular", "viral", "music", "entertainment"]
        import random
        query = random.choice(trending_queries)
        
        title, video_url, views, video_id = search_youtube(query, max_results=10)
        
        if video_url:
            return {
                "video_id": video_id,
                "video_url": video_url,
                "title": title,
                "views": views
            }
        else:
            # Fallback
            return {
                "video_id": "dQw4w9WgXcQ",
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Rick Astley - Never Gonna Give You Up",
                "views": 1000000000
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting random video: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)