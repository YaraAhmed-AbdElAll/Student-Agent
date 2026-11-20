from langgraph.checkpoint.memory import InMemorySaver

from student_agent.graph import build_graph, chat

graph = build_graph(checkpointer=InMemorySaver())
STUDENT_ID = 2

questions = [
    "How am I doing in Data Structures"
]

for question in questions:
    text, tools_used = chat(graph, STUDENT_ID, question)
    print("Q:", question)
    print("tools:", tools_used)
    print("A:", text)
    print()