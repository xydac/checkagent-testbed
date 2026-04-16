"""Class-based LangChain LCEL chain agent for checkagent wrap testing."""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel


class LCELAgent:
    """A class-based LangChain LCEL chain."""
    
    def __init__(self):
        model = GenericFakeChatModel(messages=iter(["Response from LCEL class agent"]))
        prompt = ChatPromptTemplate.from_template("Answer: {input}")
        self.chain = prompt | model | StrOutputParser()
    
    def invoke(self, input_text: str) -> str:
        return self.chain.invoke({"input": input_text})
