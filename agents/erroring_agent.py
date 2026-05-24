import sys
import random

def run(prompt: str) -> str:
    # Error on 50% of calls to trigger the warning
    if random.random() < 0.5:
        raise RuntimeError("Agent temporarily unavailable")
    return f"I cannot help with that request."
