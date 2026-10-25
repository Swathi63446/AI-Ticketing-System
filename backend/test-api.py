import os
import sys
import json
import traceback
from pathlib import Path

# Add backend directory to module search path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from config import GEMINI_API_KEY, MODELS
from llm_service import analyze_ticket_with_provider

def run_gemini_test():
    print("\n" + "="*60)
    print("           GEMINI API DIAGNOSTIC TEST RUN")
    print("="*60)

    api_key = os.getenv("AIzaSyBieZQr3SXVHjyT831XNRlN1alnCWHVGDE", GEMINI_API_KEY)
    model_name = MODELS.get("gemini", "gemini-3.5-flash")

    # 1. Inspect Credentials
    if api_key:
        masked_key = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "INVALID_LENGTH"
        print(f"[+] API Key Found: {masked_key}")
    else:
        print("[!] ERROR: GEMINI_API_KEY is completely missing from environment or config.py!")
        return

    print(f"[+] Targeted Model: {model_name}")

    # 2. Test Payload
    subject = "Critical: Checkout crash on iOS app"
    description = "Whenever I try to complete my purchase on the iOS app during the final payment step, the app crashes completely and returns me to the home screen. iPhone 15 running iOS 18.1."

    print("\n[*] Sending request to Gemini via LangChain...")
    
    try:
        response = analyze_ticket_with_provider(
            subject=subject,
            description=description,
            context=[],
            provider="gemini"
        )

        print("\n" + "-"*40)
        print("          RESULTS")
        print("-"*40)
        print(f"Status     : {response.get('status')}")
        print(f"Provider   : {response.get('provider')}")
        print(f"Latency    : {response.get('latency_ms')} ms")

        if response.get("status") == "success":
            print("\n[SUCCESS] Parsed JSON Output from Gemini:")
            print(json.dumps(response.get("data", {}), indent=2))
        else:
            print(f"\n[FAILURE] Raw Error Details:\n{response.get('error')}")

    except Exception as err:
        print("\n[CRITICAL EXCEPTION CAUGHT]:")
        traceback.print_exc()

    print("="*60 + "\n")

if __name__ == "__main__":
    run_gemini_test()