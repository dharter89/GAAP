import os
from google import genai

# Point the SDK to your downloaded service-account JSON key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\DavidHarter\OneDrive - Valiant Partners LLC\VP Drive\7. Drive Templates\Python\Gemini\gemini-demo-467504-ca7268cb4985.json"


def main():
    # Initialize the Vertex AI client with explicit project and location
    client = genai.Client(
        vertexai=True,
        project="gemini-demo-467504",   # replace with your actual project ID
        location="us-central1",          # replace with your region
    )

    # Send a simple test prompt to Gemini 2.5 Pro
    # Note: use the short model name for Vertex AI
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents="Hello Gemini! Can you say hi?"
    )

    # Print the AI's response
    print("Gemini says:", response.text)


if __name__ == "__main__":
    main()
