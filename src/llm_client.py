"""
Thin wrapper so the pipeline can run on whichever LLM provider is set in
.env (LLM_PROVIDER). Defaults to Gemini since it's free - no card needed,
~1,500 requests/day on the free tier, plenty for this project's volume.

Switch to Anthropic later (e.g. once you have credits) just by changing
LLM_PROVIDER=anthropic in .env - nothing else in the pipeline changes.
"""
from src.config import (
    LLM_PROVIDER,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_FAST_MODEL,
    ANTHROPIC_STRONG_MODEL,
)


def _call_gemini(prompt):
    from google import genai

    if not GEMINI_API_KEY:
        raise EnvironmentError(
            "GEMINI_API_KEY not set. Get a free key at aistudio.google.com "
            "(no credit card needed) and add it to .env."
        )
    client = genai.Client(api_key=GEMINI_API_KEY)

    if hasattr(client, "responses") and hasattr(client.responses, "create"):
        response = client.responses.create(model=GEMINI_MODEL, input=prompt)
        text = getattr(response, "output_text", None)
        if text:
            return text

        output = getattr(response, "output", None)
        if output:
            if isinstance(output, list):
                for item in output:
                    if hasattr(item, "content"):
                        for chunk in item.content:
                            chunk_text = getattr(chunk, "text", None)
                            if chunk_text:
                                return chunk_text
                    if isinstance(item, dict) and "content" in item:
                        for chunk in item["content"]:
                            if isinstance(chunk, dict) and "text" in chunk:
                                return chunk["text"]
        raise RuntimeError("Could not parse Gemini response output.")

    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text


def _call_anthropic(prompt, tier, max_tokens):
    import anthropic

    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY not set. Add it to .env or your GitHub/Streamlit secrets.")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    model = ANTHROPIC_FAST_MODEL if tier == "fast" else ANTHROPIC_STRONG_MODEL
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def call_llm(prompt, tier="fast", max_tokens=2000):
    """tier: 'fast' for bulk tagging, 'strong' for opportunity reasoning.
    Only affects which Anthropic model is used - Gemini's free tier only
    exposes Flash, so it uses the same model for both.
    """
    if LLM_PROVIDER == "gemini":
        return _call_gemini(prompt)
    elif LLM_PROVIDER == "anthropic":
        return _call_anthropic(prompt, tier, max_tokens)
    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}. Use 'gemini' or 'anthropic'.")
