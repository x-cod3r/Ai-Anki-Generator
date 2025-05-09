import requests
import json

num_cards = input("Enter the number of flashcards you want to generate: ")

API_KEY = "API_HERE" # Replace with your ChatPDF API key
FILE_PATH = "D:\development\Python\output_chunks\s00266-021-02350-z_01.pdf"  # Replace with the path to your PDF file
PROMPT = "Please summarize the key concepts and findings from the document and Create " + num_cards + " flashcards that cover the main topics and core concepts of the document and rational reasoning between facts and concepts. Each flashcard should contain a question on one side with the word Front before it and the corresponding answer on the other side with the word Back before it." # example prompt, you can change it


def upload_pdf(api_key, file_path):
    """Uploads a PDF to the ChatPDF API using the specified method."""
    url = "https://api.chatpdf.com/v1/sources/add-file"
    headers = {
        'x-api-key': api_key
    }
    try:
        with open(file_path, 'rb') as file:
          files = [('file', (file.name, file, 'application/octet-stream'))]
          response = requests.post(url, headers=headers, files=files)
          response.raise_for_status()  # Raise HTTPError for bad responses
          data = response.json()
          if 'sourceId' in data:
            return data['sourceId']
          else:
             print(f"Error: Response did not contain a valid sourceId: {data}")
             return None

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error during file upload: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None

def send_prompt(api_key, source_id, prompt):
    """Sends a prompt to the ChatPDF API using the source_id."""
    url = "https://api.chatpdf.com/v1/chats/message" # Corrected URL
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }
    data = {
        "sourceId": source_id,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise HTTPError for bad responses
        data = response.json()
        if data and 'content' in data:
            return data['content']
        else:
            print(f"Error: Response did not contain a valid response: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error during prompt request: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None

if __name__ == "__main__":
    source_id = upload_pdf(API_KEY, FILE_PATH)

    if source_id:
        print(f"File uploaded successfully. Source ID: {source_id}")
        response = send_prompt(API_KEY, source_id, PROMPT)
        if response:
            print("ChatPDF Response:")
            print(response)
    else:
        print("Failed to process the PDF")
