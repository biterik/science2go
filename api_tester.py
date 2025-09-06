import os
import time
import sys
import google.generativeai as genai
from typing import Optional, Dict, Any

def run_api_test() -> Dict[str, Any]:
    """
    A standalone script to test the Gemini API configuration and a basic call.
    Provides detailed output to help debug connection issues.
    """
    print("--- Starting Gemini API Test ---")
    
    # 1. Check for API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in environment variables.")
        print("Please set your API key and try again.")
        return {'success': False, 'error': 'API key not found'}
    print("✅ API key found.")

    # 2. Configure the Gemini model
    model = None
    try:
        genai.configure(api_key=api_key)
        
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-latest",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        print("✅ Gemini model configured successfully.")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize Gemini model. Details: {e}")
        return {'success': False, 'error': f"Model initialization failed: {e}"}

    # 3. Prepare a test prompt
    test_text = "Hydrogen embrittlement is a complex phenomenon."
    test_prompt = f"""
    You are a text cleaning specialist. Clean the following text for text-to-speech.
    - Remove figure/table references.
    - Remove citation brackets.
    - Convert symbols.

    TEXT TO CLEAN: {test_text}
    """
    test_prompt = "x"*25000
    print("\n--- Running Test API Call ---")
    print(f"Test prompt: '{test_text}'")
    print("length:", len(test_prompt))

    # 4. Make the API call with a timeout
    try:
        start_time = time.time()
        print("⚙️ Attempting API call with a 30-second timeout...")
        
        # Use a chat session as in your main code
        chat = model.start_chat(history=[])
        response = chat.send_message(
            test_prompt,
            request_options={'timeout': 30}
        )
        
        end_time = time.time()
        
        if response and response.text:
            print("✅ API call successful!")
            print(f"Time taken: {end_time - start_time:.2f} seconds.")
            print(f"Response (first 100 chars): '{response.text.strip()[:100]}...'")
            return {'success': True, 'response': response.text}
        else:
            print("❌ API call failed: No text in response.")
            return {'success': False, 'error': 'Empty response'}

    except genai.APIError as e:
        print(f"❌ ERROR: genai.APIError occurred during API call. This is a problem with the API service.")
        print(f"Error details: {e}")
        return {'success': False, 'error': f'APIError: {e}'}
    except Exception as e:
        print(f"❌ ERROR: An unexpected error occurred during the API call.")
        print(f"Error details: {e}")
        return {'success': False, 'error': f'Unexpected Error: {e}'}

if __name__ == "__main__":
    test_result = run_api_test()
    if test_result['success']:
        print("\n--- Test passed successfully. The issue is likely in the main program's logic. ---")
    else:
        print("\n--- Test failed. The issue is likely with the API configuration or connectivity. ---")
