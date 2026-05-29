"""
Router Agent — Takes the validation output and decides what to do next
using OpenRouter's free Gemini 2.0 Flash endpoint.
"""

import json
import os
from openai import OpenAI

ROUTING_PROMPT = """
You are an expert logistics routing agent. Your job is to look at the validation results of a trade document and decide the next step.

Here is the validation result:
{validation_json}

Your task:
1. "decision": Must be exactly one of: "auto_approve", "flag_for_review", "amendment_required".
   - If there are ANY mismatches -> "amendment_required".
   - If there are NO mismatches but some fields are "uncertain" -> "flag_for_review".
   - If ALL fields are "match" -> "auto_approve".
2. "reasoning": A 1-2 sentence explanation of your decision.
3. "draft_email": If the decision is "amendment_required", draft a polite, professional email to the supplier (SU) listing the exact fields that mismatched, showing what was found vs what was expected. If no amendment is needed, return null.

CRITICAL RULES:
- Return ONLY valid JSON.
- Output format:
{{
  "decision": "...",
  "reasoning": "...",
  "draft_email": "..."
}}
"""

def route(validation_result: dict) -> dict:
    """
    Make a routing decision based on validation results using OpenRouter.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"decision": "flag_for_review", "reasoning": "GROQ_API_KEY not set.", "draft_email": None}

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )
    prompt = ROUTING_PROMPT.format(validation_json=json.dumps(validation_result, indent=2))

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        return json.loads(content.strip())
        
    except json.JSONDecodeError:
        return {"decision": "flag_for_review", "reasoning": "Failed to parse JSON.", "draft_email": None}
    except Exception as e:
        return {"decision": "flag_for_review", "reasoning": f"Error: {str(e)}", "draft_email": None}
