from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from datetime import datetime
from urllib.parse import quote
import os
from duckduckgo_search import DDGS
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Cyber Threat Intelligence API",
             description="Real-time cyber threat detection with web search capabilities")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class ThreatRequest(BaseModel):
    location: str = "global"
    use_cache: bool = True

# Response model
class ThreatResponse(BaseModel):
    location: str
    generated_at: str
    threats: List[Dict]
    analysis: str
    raw_markdown: str

class CyberThreatDetector:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "qwen-2.5-32b"
        self.threat_cache = {}

    def search_threats(self, location: str) -> List[Dict]:
        queries = [
            f"recent financial fraud in {location}",
            
        ]
        
        all_results = []
        try:
            with DDGS() as ddgs:
                for query in queries:
                    results = list(ddgs.text(query, max_results=3))
                    all_results.extend(results)
                    if len(all_results) >= 4:
                        break

                processed = []
                seen_urls = set()
                for item in all_results:
                    url = item.get('href', '').strip()
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        processed.append({
                            'title': item.get('title', 'No Title'),
                            'description': self._clean_text(item.get('body', 'No Description')),
                            'url': url,
                            'safe_url': quote(url, safe='/:?=&')
                        })
                return processed[:4]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    def _clean_text(self, text: str) -> str:
        return text.replace('\n', ' ').replace('"', "'").strip()

    def analyze_threats(self, threats: List[Dict], location: str) -> str:
        context = "Financial Fraud  to analyze:\n"
        for t in threats:
            context += f"- {t['title']}: {t['description']}\n"
        
        prompt = f"""Provide detailed analysis of these threats for {location}:
        1. Threat severity assessment
        2. Potential targets
        3. Recommended mitigation
        4. Relevant security advisories"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a cybersecurity expert."},
                    {"role": "user", "content": context + prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Analysis failed: {str(e)}"

detector = CyberThreatDetector()

@app.post("/detect-threats", response_model=ThreatResponse)
async def detect_threats(request: ThreatRequest):
    """
    Detect and analyze Fina for a specific location
    
    Parameters:
    - location: Geographic location or industry sector
    - use_cache: Whether to use cached results if available (default: True)
    
    Returns:
    - Structured threat report with clickable links
    """
    try:
        # Check cache first
        if request.use_cache and request.location in detector.threat_cache:
            cached = detector.threat_cache[request.location]
            cache_age = (datetime.now() - datetime.fromisoformat(cached['timestamp'])).seconds
            if cache_age < 3600:  # 1 hour cache
                threats = cached['threats']
                from_cache = True
        
        # Get fresh results if not using cache
        if not request.use_cache or request.location not in detector.threat_cache or cache_age >= 3600:
            threats = detector.search_threats(request.location)
            from_cache = False
            if not threats:
                raise HTTPException(status_code=404, detail="No threats found")

        # Generate analysis
        analysis = detector.analyze_threats(threats, request.location)
        
        # Generate markdown with links
        markdown = f"# Cyber Threats in {request.location}\n\n"
        markdown += "## Detected Threats\n"
        for idx, threat in enumerate(threats, 1):
            markdown += (
                f"{idx}. **[{threat['title']}]({threat['safe_url']})**\n"
                f"   - *Description*: {threat['description']}\n"
                f"   - [View Full Report]({threat['safe_url']})\n\n"
            )
        markdown += f"## Analysis\n{analysis}"

        # Prepare response
        return {
            "location": request.location,
            "generated_at": datetime.now().isoformat(),
            "threats": threats,
            "analysis": analysis,
            "raw_markdown": markdown,
            "from_cache": from_cache
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "Cyber Threat Intelligence API",
        "endpoints": {
            "POST /detect-threats": "Detect threats for a location",
            "parameters": {
                "location": "string (e.g., 'New York', 'healthcare')",
                "use_cache": "boolean (default: true)"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)