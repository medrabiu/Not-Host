from groq import Groq
from bot.ai.config import GROQ_API_KEY, DEFAULT_MODEL

client = Groq(api_key=GROQ_API_KEY)

def query_groq(prompt, model=DEFAULT_MODEL):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )
    return response.choices[0].message.content