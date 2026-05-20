from openai import OpenAI # same as import java.util.Scanner;

from dotenv import load_dotenv  # importing the dotenv library

import os  # built in Python library, like java.io

load_dotenv() # reads your .env file, loads the key into memory

# This is like creating an instance of a class in Java
# OpenAI() automatically finds your key from .env


client = OpenAI() # same as Scanner sc = new Scanner(System.in);

claim = input("Enter your claim: ")
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
            "content": claim # content is your actual question
        }
    ]
)
# Extract the text response
answer = response.choices[0].message.content # chatGPT gives a big response like JSON
print("ChatGPT's response:")
print(answer)
 