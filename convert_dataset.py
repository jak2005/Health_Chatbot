import pandas as pd
import json

# Read the Excel file
df = pd.read_excel('dataset.csv.xlsx')

# Create a dictionary to group symptoms by disease
disease_data = {}

for _, row in df.iterrows():
    disease = row['Disease']
    if disease not in disease_data:
        disease_data[disease] = set()
    
    # Collect all symptoms (columns Symptom_1 to Symptom_17)
    for col in df.columns:
        if 'Symptom' in col:
            symptom = row[col]
            if pd.notna(symptom) and symptom:
                disease_data[disease].add(str(symptom).strip())

# Convert to JSON format for RAG
knowledge_items = []
for disease, symptoms in disease_data.items():
    symptoms_list = sorted(list(symptoms))
    symptoms_text = ', '.join(symptoms_list)
    
    content = f"{disease}: Common symptoms include {symptoms_text}. If you experience these symptoms, consult a healthcare professional for proper diagnosis and treatment."
    
    knowledge_items.append({
        'id': f"disease_{disease.lower().replace(' ', '_')}",
        'content': content,
        'category': 'diseases',
        'source': 'Disease Symptoms Database'
    })

print(f"Created {len(knowledge_items)} disease entries")
print("Sample entry:", json.dumps(knowledge_items[0], indent=2))

# Save to JSON file
with open('data/disease_symptoms.json', 'w', encoding='utf-8') as f:
    json.dump(knowledge_items, f, indent=2, ensure_ascii=False)

print("Saved to data/disease_symptoms.json")
