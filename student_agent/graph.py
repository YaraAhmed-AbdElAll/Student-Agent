from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from student_agent.llm import get_llm, message_text
from student_agent.prompts import SYSTEM_PROMPT
from student_agent.tools.langchain_tools import ALL_TOOLS



# Stops a runaway loop. Each model call plus its tools is about 2 steps,
# so 12 steps is at most about 6 model calls (and 6 requests from the daily limit).
RECURSION_LIMIT = 12


def build_graph(llm=None, checkpointer=None):
    """Build the Student Agent: a model that can call tools, in a loop."""
    if llm is None:
        llm = get_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def call_model(state: MessagesState):
        messages = state["messages"]
        if SYSTEM_PROMPT:
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        return {"messages": [llm_with_tools.invoke(messages)]}

    builder = StateGraph(MessagesState)
    builder.add_node("model", call_model)
    builder.add_node("tools", ToolNode(ALL_TOOLS))

    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", tools_condition)
    builder.add_edge("tools", "model")

    return builder.compile(checkpointer=checkpointer)


def last_turn(messages):
    """The messages added since the student's latest question."""
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].type == "human":
            return messages[i + 1:]
    return messages


def chat(graph, student_id, text):
    """Send one message from a student. Returns (reply text, tools the agent used)."""
    config = {
        "recursion_limit": RECURSION_LIMIT,
        "configurable": {
            "thread_id": f"student-{student_id}",
            "student_id": student_id,
        },
    }
    result = graph.invoke({"messages": [HumanMessage(content=text)]}, config=config)

    turn = last_turn(result["messages"])
    tools_used = [
        call["name"] for m in turn if m.type == "ai" for call in m.tool_calls
    ]
    return message_text(result["messages"][-1]), tools_used