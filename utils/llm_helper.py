import time
import random


def invoke_with_retry(llm, prompt, max_retries=3):
    """
    Safely invoke the Gemini LLM.

    Retries temporarily failed requests such as:
    - 429 Too Many Requests
    - Quota / Resource Exhausted
    - 503 Service Unavailable
    """

    for attempt in range(max_retries):

        try:

            print(
                f"LLM request attempt {attempt + 1}/{max_retries}"
            )

            response = llm.invoke(prompt)

            print("LLM request successful.")

            return response

        except Exception as e:

            error_text = str(e).lower()

            is_rate_limit = (
                "429" in error_text
                or "quota" in error_text
                or "too many requests" in error_text
                or "resource exhausted" in error_text
            )

            is_server_error = (
                "503" in error_text
                or "service unavailable" in error_text
                or "500" in error_text
            )

            # If this is not a temporary API problem,
            # immediately stop and show the actual error.
            if not (is_rate_limit or is_server_error):

                print("Non-retryable LLM error:")
                print(e)

                raise

            # Last attempt failed.
            if attempt == max_retries - 1:

                print("Maximum LLM retries reached.")

                raise

            # Exponential backoff:
            # 1st retry → ~1-2 sec
            # 2nd retry → ~2-3 sec
            wait_time = (
                (2 ** attempt)
                + random.uniform(0, 1)
            )

            print(
                f"Temporary LLM error detected."
            )

            print(
                f"Retrying in {wait_time:.2f} seconds..."
            )

            time.sleep(wait_time)