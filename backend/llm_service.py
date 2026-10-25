import os
import re
import json
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from config import GEMINI_API_KEY, GROQ_API_KEY, HF_API_TOKEN, MODELS


def clean_and_parse_json(text_content):
    """
    Resilient JSON parser that unwraps LangChain content blocks 
    and parses string outputs into valid Python dicts/lists.
    """
    # 1. Unwrap dict content block e.g., {"type": "text", "text": "..."}
    if isinstance(text_content, dict):
        if "text" in text_content and "subject" not in text_content and "tickets" not in text_content:
            text_content = text_content["text"]

    # 2. Unwrap list content block e.g., [{"type": "text", "text": "..."}]
    if isinstance(text_content, list) and len(text_content) > 0:
        first = text_content[0]
        if isinstance(first, dict) and "text" in first and "subject" not in first and "tickets" not in first:
            text_content = first["text"]

    # 3. If already a valid dict or list, return directly
    if isinstance(text_content, (dict, list)):
        return text_content

    if not isinstance(text_content, str):
        text_content = str(text_content)

    # 4. Clean markdown fences and common LLM boundary glitches
    cleaned = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', text_content, flags=re.DOTALL).strip()
    cleaned = re.sub(r'\}\s*,\s*"\s*\{', '},{', cleaned)

    # 5. Direct JSON load
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 6. Extract outermost JSON structure fallback
    match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON from LLM output: {str(text_content)[:200]}...")


def get_langchain_model(provider: str):
    """Factory function returning a configured LangChain Chat model instance."""
    if provider == "groq":
        groq_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        if not groq_key:
            raise ValueError("GROQ_API_KEY is missing in environment.")
        return ChatGroq(
            groq_api_key=groq_key,
            model_name=MODELS.get("groq", "llama-3.1-8b-instant"),
            temperature=0.1,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    elif provider in ["featherless-ai", "featherless", "huggingface"]:
        hf_token = os.getenv("HF_API_TOKEN", HF_API_TOKEN)
        if not hf_token:
            raise ValueError("HF_API_TOKEN is missing in environment.")
        
        base_model = MODELS.get(provider, "Qwen/Qwen2.5-7B-Instruct")
        model_name = f"{base_model}:featherless-ai" if not base_model.endswith(":featherless-ai") else base_model

        return ChatOpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=hf_token,
            model_name=model_name,
            temperature=0.1
        )

    else:  # Gemini Default
        gemini_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is missing in environment.")
        
        model_name = MODELS.get("gemini", "gemini-3.5-flash")
        return ChatGoogleGenerativeAI(
            google_api_key=gemini_key,
            model=model_name,
            temperature=0.1
        )


def analyze_ticket_with_provider(subject, description, context=[], provider="gemini"):
    start_time = time.perf_counter()

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert customer support ticket classifier. Output ONLY a valid JSON object without markdown fences.\n"
            "STRICT RULES:\n"
            '1. "sentiment" MUST strictly be one of: "Positive", "Negative", or "Neutral".\n'
            '2. "priority" MUST strictly be one of: "Critical", "High", "Medium", or "Low".'
        )),
        ("user", (
            "Analyze this customer support ticket.\n"
            "Subject: {subject}\n"
            "Description: {description}\n"
            "Context: {context}\n\n"
            "Return a raw JSON object with exact keys: "
            '"subject", "description", "category", "sentiment", "priority", "summary", "requires_human_review", "response".'
        ))
    ])

    try:
        llm = get_langchain_model(provider)
        chain = prompt_template | llm
        
        raw_response = chain.invoke({
            "subject": subject,
            "description": description,
            "context": str(context)
        })

        content = raw_response.content if hasattr(raw_response, 'content') else raw_response
        parsed_data = clean_and_parse_json(content)

        if isinstance(parsed_data, list) and len(parsed_data) > 0:
            parsed_data = parsed_data[0]

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {"status": "success", "provider": provider, "latency_ms": latency_ms, "data": parsed_data}

    except Exception as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        print(f"\n[!!! {provider.upper()} API ERROR !!!]: {e}\n")
        return {"status": "error", "provider": provider, "latency_ms": latency_ms, "error": str(e), "data": {}}


def analyze_document_tickets_with_provider(description, context=[], provider="gemini"):
    start_time = time.perf_counter()

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert customer support ticket extractor. Output ONLY a valid JSON object containing all extracted tickets.\n"
            "STRICT RULES:\n"
            '1. "sentiment" MUST strictly be one of: "Positive", "Negative", or "Neutral".\n'
            '2. "priority" MUST strictly be one of: "Critical", "High", "Medium", or "Low".'
        )),
        ("user", (
            "Extract ALL individual support tickets from this document content:\n"
            "{description}\n\n"
            "Context: {context}\n\n"
            "Return JSON format:\n"
            '{{"tickets": [{{"subject": "...", "description": "...", "category": "...", "sentiment": "...", "priority": "...", "summary": "...", "requires_human_review": false, "response": "..."}}]}}'
        ))
    ])

    try:
        llm = get_langchain_model(provider)
        chain = prompt_template | llm

        raw_response = chain.invoke({
            "description": description,
            "context": str(context)
        })

        content = raw_response.content if hasattr(raw_response, 'content') else raw_response
        parsed_data = clean_and_parse_json(content)

        tickets_list = []
        if isinstance(parsed_data, list):
            tickets_list = parsed_data
        elif isinstance(parsed_data, dict):
            for key in ["tickets", "data", "items", "results"]:
                if key in parsed_data and isinstance(parsed_data[key], list):
                    tickets_list = parsed_data[key]
                    break
            if not tickets_list:
                tickets_list = [parsed_data]

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {"status": "success", "provider": provider, "latency_ms": latency_ms, "data": tickets_list}

    except Exception as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        print(f"\n[!!! {provider.upper()} DOC PARSE ERROR !!!]: {e}\n")
        return {"status": "error", "provider": provider, "latency_ms": latency_ms, "error": str(e), "data": []}


def analyze_ticket_with_gemini(subject, description, context=[]):
    result = analyze_ticket_with_provider(subject, description, context=context, provider="gemini")
    return result.get("data", {})