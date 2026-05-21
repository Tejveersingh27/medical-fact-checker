from openai import OpenAI # same as import java.util.Scanner;

from dotenv import load_dotenv  # importing the dotenv library

from tavily import TavilyClient # importing the tavily library This is used to search the web first before consulting chatGPT

import os  # built in Python library, like java.io

load_dotenv() # reads your .env file, loads the key into memory

# This is like creating an instance of a class in Java
# OpenAI() automatically finds your key from .env


client = OpenAI() # same as Scanner sc = new Scanner(System.in);


# same as OpenAI client — creating an object to talk to Tavily
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY")) # go find TAVILY_API_KEY from my .env file.


claim = input("Enter your claim: ")

# search the web for real information
search_results = tavily.search(
    query=claim,
    search_depth="advanced",
    include_domains=["cdc.gov", "who.int"] # only trust these sources
)

# Step 2 — extract just the text from search results
# like getting .content from a JSON response
context = "\n".join([r["content"] for r in search_results["results"]])

# We're sending a message to ChatGPT and getting a response back
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": "You are a medical fact checker specializing in hantavirus.. When given a claim respond with: 1) VERDICT: TRUE/FALSE/MISLEADING 2) EXPLANATION: why 3) SOURCES: cite CDC, WHO or PubMed sources that support your answer"
        },
        {
            "role": "user", # this means you are actually asking
            "content": f"Claim: {claim}\n\nReal search results from CDC/WHO:\n{context}" #f claim is pythons version
            # Claim + {claim} + "\n" + Real search results from CDC/WHO + {context} 
        }
    ]
)
# Extract the text response
answer = response.choices[0].message.content # chatGPT gives a big response like JSON
print("ChatGPT's response:")
print(answer)
 