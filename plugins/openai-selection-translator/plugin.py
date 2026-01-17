import json
import subprocess
import time
import urllib.error
import urllib.request

import freeway


def _get_clipboard_text() -> str:
    """Get text from clipboard using pbpaste (macOS)."""
    try:
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout
    except Exception:
        return ""


def _call_openai(api_key: str, model: str, prompt: str, timeout: int = 30) -> str:
    """Call OpenAI Responses API."""
    url = "https://api.openai.com/v1/responses"
    payload = {
        "model": model,
        "input": prompt,
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

    output = response_data.get("output") or []
    for item in output:
        if item.get("type") == "message":
            content = item.get("content") or []
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

    text = freeway.get_text()
    if not text:
        freeway.log("No text to process.")
        return

    freeway.set_status_text("Copying selection…")

    # Press Cmd+C to copy selected text
    freeway.press_keys(["Command", "C"])
    time.sleep(0.15)
    freeway.release_keys(["Command", "C"])
    time.sleep(0.1)

    # Get clipboard content
    clipboard_text = _get_clipboard_text()

    if not clipboard_text or not clipboard_text.strip():
        freeway.log("Clipboard is empty; skipping.")
        freeway.set_status_text("No selection to translate")
        return

    clipboard_text = clipboard_text.strip()

    # Build prompt: text already contains the instruction
    # prompt = f"{text}. Output only the translation, nothing else.\n\nText:\n{selected_text}"
    prompt = freeway.get_setting("prompt")
    prompt = prompt.replace("{text}", text)
    prompt = prompt.replace("{selected_text}", clipboard_text)

    freeway.set_status_text("Translating…")
    freeway.set_indicator_color("#10A37F")  # OpenAI green

    try:
        response_text = _call_openai(api_key, model, prompt)
        freeway.set_text(response_text)
        freeway.log(f"Translated selection with model {model}.")
        freeway.set_status_text("✓ Translated")
    except Exception as exc:
        freeway.log(f"OpenAI error: {exc}")
        freeway.set_status_text(f"Error: {str(exc)[:60]}")
