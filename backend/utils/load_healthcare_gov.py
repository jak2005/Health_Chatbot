"""
Script to fetch Healthcare.gov API data and load it into the knowledge base
"""

import json
import urllib.request
from pathlib import Path

HEALTHCARE_GOV_API = "https://www.healthcare.gov/api/index.json"

def fetch_healthcare_data():
    """Fetch data from Healthcare.gov API"""
    print("Fetching data from Healthcare.gov API...")
    
    try:
        with urllib.request.urlopen(HEALTHCARE_GOV_API) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"Fetched {len(data)} items from Healthcare.gov")
            return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def convert_to_knowledge_base(healthcare_data):
    """Convert Healthcare.gov data to knowledge base format"""
    documents = []
    
    for item in healthcare_data:
        title = item.get('title', '')
        bite = item.get('bite', '')  # Short description
        url = item.get('url', '')
        categories = item.get('categories', [])
        tags = item.get('tags', [])
        
        if not title or not bite:
            continue
        
        # Create document content
        content = f"{title}: {bite}"
        
        # Determine category
        if 'glossary' in categories:
            category = 'glossary'
        elif tags:
            category = tags[0]
        else:
            category = 'healthcare'
        
        doc_id = f"hcgov_{url.replace('/', '_').strip('_')}" if url else f"hcgov_{len(documents)}"
        
        documents.append({
            "id": doc_id,
            "content": content,
            "category": category,
            "source": "healthcare.gov",
            "url": f"https://www.healthcare.gov{url}" if url else None
        })
    
    return documents

def save_to_json(documents, output_path):
    """Save documents to JSON file"""
    data = {"documents": documents}
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(documents)} documents to {output_path}")

def main():
    # Fetch data
    healthcare_data = fetch_healthcare_data()
    
    if not healthcare_data:
        print("No data fetched. Exiting.")
        return
    
    # Convert to knowledge base format
    documents = convert_to_knowledge_base(healthcare_data)
    print(f"Converted {len(documents)} documents for knowledge base")
    
    # Save to healthcare_data.json (used by RAG service)
    output_path = Path(__file__).parent / "healthcare_data.json"
    save_to_json(documents, output_path)
    
    print("\nDone! Restart the backend to load the new data.")

if __name__ == "__main__":
    main()
