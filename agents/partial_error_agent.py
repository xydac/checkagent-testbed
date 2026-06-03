def partial_agent(prompt: str) -> str:
    # Fail on longer prompts (most injection probes are longer)
    if len(prompt) > 100:
        raise RuntimeError("Prompt too long")
    return "I cannot help with that request"
