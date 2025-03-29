from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set API keys
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

class CyberThreatTools:
    """A custom tool to fetch and analyze cyber threat data using DuckDuckGo web search."""
    
    def __init__(self, duckduckgo_tool):
        self.duckduckgo_tool = duckduckgo_tool

    def search(self, query, max_results=5):
        """Perform a web search and format results."""
        try:
            results = self.duckduckgo_tool.search(query, max_results=max_results)
            return [{
                'title': r.get('title', 'No Title'),
                'snippet': r.get('snippet', 'No Description'),
                'link': r.get('link', '#')
            } for r in results]
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def get_cyber_threats(self, location="Ahmedabad"):
        """Fetch and format cyber threats for a specific location."""
        query = f"current cyber attacks in {location}"
        search_results = self.search(query)

        if not search_results:
            return f"No recent cyber threats reported in {location}."

        result = f"### Current Cyber Attacks in {location}:\n"
        for idx, item in enumerate(search_results, start=1):
            result += f"{idx}. *{item['title']}*\n"
            result += f"   - Description: {item['snippet']}\n"
            result += f"   - Source: [{item['link']}]({item['link']})\n"
        
        return result

# Initialize FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for request
class LocationRequest(BaseModel):
    location: str = "Ahmedabad"

# Initialize tools
duckduckgo_tool = DuckDuckGoTools()
cyber_threat_tool = CyberThreatTools(duckduckgo_tool)

# Create agent
agent = Agent(
    model=Groq(id="qwen-2.5-32b"),
    description="Cyber threat detection agent with real-time web search capabilities",
    tools=[duckduckgo_tool, cyber_threat_tool],
    markdown=True
)

@app.get("/")
def read_root():
    return {"message": "Cyber Threat API - Use POST /cyber-threats with location parameter"}

@app.post("/cyber-threats")
async def get_cyber_threats(request: LocationRequest):
    """Endpoint to get cyber threats for a location."""
    try:
        response = agent.print_response(
            f"What are the current cyber attacks in {request.location}?"
        )
        
        # Parse markdown response
        threats = []
        current_threat = {}
        
        for line in response.split('\n'):
            if line.startswith('###'):
                continue
            elif line and line[0].isdigit():
                if current_threat:
                    threats.append(current_threat)
                parts = line.split('*')
                current_threat = {
                    "title": parts[1] if len(parts) > 1 else line.strip('. '),
                    "description": "",
                    "source": ""
                }
            elif line.strip().startswith('- Description:'):
                current_threat["description"] = line.split(':', 1)[1].strip()
            elif line.strip().startswith('- Source:'):
                current_threat["source"] = line.split(':', 1)[1].strip()
        
        if current_threat:
            threats.append(current_threat)
            
        return {
            "location": request.location,
            "threats": threats,
            "raw_response": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)