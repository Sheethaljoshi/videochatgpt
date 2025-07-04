from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
import re
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
    reply_steps: List[str]  # Changed from single reply to list of steps
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

# === FUNCTION: Break Down AI Response into Steps ===
# === FUNCTION: Break Down AI Response into Steps ===
def break_down_response_into_steps(response_text):
    """
    Uses AI to intelligently break down a response into logical steps
    """
    try:
        breakdown_prompt = f"""
        You are an expert at breaking down educational content into clear, digestible steps.
        
        Take the following math explanation and break it down into logical steps that are easy to follow.
        Each step should be a complete thought that builds on the previous one.
        
        Rules:
        1. Each step should be 1-3 sentences maximum
        2. Start with the most basic concept or identification
        3. Progress logically through the solution
        4. End with the final answer or conclusion
        5. Use clear, simple language
        6. Format each step as: "Step X: [complete explanation]"
        7. Do not use markdown formatting like **bold** or *italic*
        8. Make sure each step contains the full explanation, not just a partial sentence
        
        Original explanation:
        {response_text}
        
        Break this down into clear, complete steps:
        """
        
        breakdown_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": breakdown_prompt}]
        )
        
        breakdown_text = breakdown_response.choices[0].message.content.strip()
        print(f"🔍 AI Breakdown Response: {breakdown_text}")  # Debug print
        
        # Parse the steps from the response
        steps = []
        lines = breakdown_text.split('\n')
        
        current_step = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a new step
            if (line.startswith('Step ') or 
                re.match(r'^\d+[\.\):]', line) or 
                line.startswith('**Step ') or
                re.match(r'^\*\*\d+\*\*', line)):
                
                # Save the previous step if it exists
                if current_step.strip():
                    steps.append(current_step.strip())
                
                # Start new step, remove step markers
                step_text = re.sub(r'^(Step \d+:|\*\*Step \d+:\*\*|\d+[\.\):]|\*\*\d+\*\*)', '', line).strip()
                current_step = step_text
            else:
                # Continue the current step
                if current_step:
                    current_step += " " + line
                else:
                    current_step = line
        
        # Don't forget the last step
        if current_step.strip():
            steps.append(current_step.strip())
        
        print(f"📝 Parsed {len(steps)} steps:")  # Debug print
        for i, step in enumerate(steps, 1):
            print(f"  Step {i}: {step[:100]}...")  # Debug print
        
        # If no steps were parsed or steps are too short, try a different approach
        if not steps or len(steps) < 3 or any(len(step) < 20 for step in steps):
            print("⚠️ Using fallback parsing method")
            return fallback_step_parsing(response_text)
        
        return steps
        
    except Exception as e:
        print(f"Error breaking down response: {e}")
        return fallback_step_parsing(response_text)

def fallback_step_parsing(response_text):
    """
    Fallback method for parsing steps when AI breakdown fails
    """
    # Split by sentences and group logically
    sentences = re.split(r'[.!?]+', response_text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    
    if len(sentences) <= 3:
        return [s + "." for s in sentences]
    
    # Group sentences into logical steps (2-3 sentences per step)
    steps = []
    current_step = ""
    sentence_count = 0
    
    for sentence in sentences:
        if sentence_count < 2 and len(current_step) + len(sentence) < 200:
            current_step += sentence + ". "
            sentence_count += 1
        else:
            if current_step:
                steps.append(current_step.strip())
            current_step = sentence + ". "
            sentence_count = 1
    
    # Add the last step
    if current_step:
        steps.append(current_step.strip())
    
    return steps if steps else [response_text]
    """
    Uses AI to intelligently break down a response into logical steps
    """
    try:
        breakdown_prompt = f"""
        You are an expert at breaking down educational content into clear, digestible steps.
        
        Take the following math explanation and break it down into logical steps that are easy to follow.
        Each step should be a complete thought that builds on the previous one.
        
        Rules:
        1. Each step should be 1-3 sentences maximum
        2. Start with the most basic concept or identification
        3. Progress logically through the solution
        4. End with the final answer or conclusion
        5. Use clear, simple language
        6. Number each step (Step 1:, Step 2:, etc.)
        
        Original explanation:
        {response_text}
        
        Break this down into clear steps:
        """
        
        breakdown_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": breakdown_prompt}]
        )
        
        breakdown_text = breakdown_response.choices[0].message.content.strip()
        
        # Parse the steps from the response
        steps = []
        lines = breakdown_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('Step ') or line.startswith('**Step ') or 
                        re.match(r'^\d+[\.\):]', line) or line.startswith('- ')):
                # Clean up the step text
                step_text = re.sub(r'^(Step \d+:|\*\*Step \d+:\*\*|\d+[\.\):]|\- )', '', line).strip()
                if step_text:
                    steps.append(step_text)
        
        # If no steps were parsed, try a simpler approach
        if not steps:
            # Split by sentences and group logically
            sentences = re.split(r'[.!?]+', response_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) <= 3:
                return sentences
            else:
                # Group sentences into logical steps
                steps = []
                current_step = ""
                for sentence in sentences:
                    if len(current_step) + len(sentence) < 150:  # Keep steps concise
                        current_step += sentence + ". "
                    else:
                        if current_step:
                            steps.append(current_step.strip())
                        current_step = sentence + ". "
                if current_step:
                    steps.append(current_step.strip())
        
        return steps if steps else [response_text]
        
    except Exception as e:
        print(f"Error breaking down response: {e}")
        # Fallback: simple sentence splitting
        sentences = re.split(r'[.!?]+', response_text)
        return [s.strip() + "." for s in sentences if s.strip()]

# === FUNCTION: Generate AI Response ===
def generate_ai_response(user_input):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a friendly and knowledgeable math teacher. When a student sends a math expression or problem, you respond as if you're explaining it step by step in a clear and patient way. Use simple, encouraging language, and aim to teach the concept behind the question. Structure your response in a logical flow that can be easily broken down into steps. If the question is unclear, try to interpret it based on what a student might mean. Be thorough but concise in your explanations."},
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
        
        # Break down the response into steps
        print("🔄 Breaking down response into steps...")
        response_steps = break_down_response_into_steps(ai_response)
        print(f"📝 Generated {len(response_steps)} steps")
        
        # Generate optimized search query
        print("🧠 Generating smart search query...")
        search_query = generate_best_search_query(chat_message.message)
        print(f"🔍 Searching YouTube for: {search_query}")
        
        # Search YouTube for the most viewed video
        title, video_url, views, video_id = search_youtube(search_query)
        
        if video_url:
            print(f"🎯 Top Video Found: {title} ({views:,} views)")
            return ChatResponse(
                reply_steps=response_steps,
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
                reply_steps=response_steps,
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