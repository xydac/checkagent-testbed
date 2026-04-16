"""LangChain LCEL chain agent for checkagent wrap testing."""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

_model = GenericFakeChatModel(messages=iter(["I'm a helpful assistant. Your query was: {input}"]))
_prompt = ChatPromptTemplate.from_template("Answer this: {input}")
chain = _prompt | _model | StrOutputParser()


def run(input_text: str) -> str:
    """Run the LCEL chain with the given input."""
    return chain.invoke({"input": input_text})
