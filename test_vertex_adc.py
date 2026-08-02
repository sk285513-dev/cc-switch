from google import genai

client = genai.Client(
    vertexai=True,
    project="project-bbb51788-254b-4ec3-ad7",
    location="us-central1",
)

resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="請用一句話回答：如果你收到這段訊息，代表目前 Vertex ADC 已可用。",
)

print(resp.text)
