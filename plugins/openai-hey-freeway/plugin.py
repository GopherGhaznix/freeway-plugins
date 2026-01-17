import json
import urllib.error
import urllib.request

import freeway


SYSTEM_PROMPT = "Your name is Freeway. You are a helpful assistant."


def _call_openai(api_key: str, model: str, user_input: str, timeout: int = 30) -> str:
    """Call OpenAI Responses API."""
    url = "https://api.openai.com/v1/responses"
    payload = {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": user_input,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code}: {error_detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e

    # Extract text from response
    output = response_data.get("output")
    if output and isinstance(output, list):
        for item in output:
            if item.get("type") == "message":
                content = item.get("content", [])
                for c in content:
                    if c.get("type") == "output_text":
                        return c.get("text", "").strip()

    raise RuntimeError("No response returned from OpenAI.")


def before_paste():
    api_key = freeway.get_setting("api_key")
    if not api_key:
        freeway.log("OpenAI API key is missing; skipping.")
        return

    model = freeway.get_setting("model") or "gpt-5-nano"
    user_input = freeway.get_text()

    if not user_input or not user_input.strip():
        freeway.log("No text to process.")
        return

    freeway.set_status_text("Thinking…")
    freeway.set_indicator_color("#10A37F")

    try:
        response_text = _call_openai(api_key, model, user_input)
        freeway.set_text(response_text)
        freeway.log(f"Got response from {model}.")
        freeway.set_status_text("✓ Done")
    except Exception as exc:
        freeway.log(f"OpenAI error: {exc}")
        freeway.set_status_text(f"Error: {str(exc)[:60]}")
