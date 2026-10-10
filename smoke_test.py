import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["API_KEY"],
)
resp = client.chat.completions.create(
    model=os.environ["NVIDIA_MODEL"],
    messages=[{"role": "user", "content": "Say hi in 5 words"}],
)
print(resp.choices[0].message.content)