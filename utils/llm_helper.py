from utils.gemini_client import gemini_client

def invoke_with_retry(llm, prompt, max_retries=3):
    """
    Delegates all requests to centralized gemini_client.
    """
    res = gemini_client.generate(str(prompt), max_retries=max_retries)
    content = res.get("content", "")
    
    class FakeResponse:
        def __init__(self, text):
            self.content = text
            
    return FakeResponse(content)