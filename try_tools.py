from langchain_core.tools import tool

from student_agent.llm import get_llm, message_text


@tool
def add_numbers(a: int, b: int) -> int:
    """Add two whole numbers and return the sum."""
    return a + b


llm = get_llm().bind_tools([add_numbers])
reply = llm.invoke("What is 17 plus 25? Use the tool.")

print("text:", message_text(reply))
print("tool calls:", reply.tool_calls)