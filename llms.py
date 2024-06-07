import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()

if os.environ.get('CHEAP_MODE') == 'True':
    cto_llm_name = os.environ.get('CHEAP_MODE_LLM')
    coder_llm_name = os.environ.get('CHEAP_MODE_LLM')
else:
    cto_llm_name = os.environ.get('CTO_AGENT_LLM')
    coder_llm_name = os.environ.get('CODER_AGENT_LLM')


def get_llm_client(model_name, temperature):
    # Its assumed that if you have an OPENROUTER_API_KEY you want to use OpenRouter.
    # Otherwise, you want to use OpenAI and OPENAI_API_KEY is required.
    if 'OPENROUTER_API_KEY' in os.environ:
        return ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ['OPENROUTER_API_KEY'],
            temperature=temperature
        )
    else:
        return ChatOpenAI(
            api_key=os.environ['OPENAI_API_KEY'],
            temperature=temperature
        )

cto_llm = get_llm_client(
    model_name=os.environ.get('CTO_AGENT_LLM'),
    temperature=0.2
)
coder_llm = get_llm_client(
    model_name=os.environ.get('CODER_AGENT_LLM'),
    temperature=0.1
)