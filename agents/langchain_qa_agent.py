"""
LangChain Q&A agent using LCEL (LangChain Expression Language).

This is a real LangChain agent pattern — a prompt | llm | parser chain
with optional context injection. Suitable for wrapping with LangChainAdapter.

Usage with a real LLM (e.g. in production):
    from langchain_openai import ChatOpenAI
    agent = make_qa_chain(ChatOpenAI(model="gpt-4o"))
    result = agent.invoke({"input": "What is the capital of France?"})

Usage with CheckAgent testing:
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from checkagent.adapters.langchain import LangChainAdapter

    llm = GenericFakeChatModel(messages=iter([AIMessage(content="Paris.")]))
    agent = make_qa_chain(llm)
    adapter = LangChainAdapter(agent)
    run = await adapter.run("What is the capital of France?")
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


SYSTEM_PROMPT = """You are a knowledgeable Q&A assistant. Answer questions clearly and concisely.
If you don't know the answer, say "I don't know" rather than making something up."""


def make_qa_chain(llm):
    """
    Build a simple Q&A chain using LangChain LCEL.

    Parameters
    ----------
    llm : BaseChatModel
        Any LangChain chat model (real or fake for testing).

    Returns
    -------
    Runnable
        A LangChain Runnable that accepts {"input": str} and returns str.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
    ])
    return prompt | llm | StrOutputParser()


def make_contextual_qa_chain(llm):
    """
    Q&A chain that accepts optional context in the input.

    Returns a Runnable that accepts {"input": str, "context": str}.
    Context is injected into the system prompt if provided.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT + "\n\nContext: {context}"),
        ("human", "{input}"),
    ])
    return prompt | llm | StrOutputParser()
