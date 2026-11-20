from student_agent.llm import get_llm, message_text

llm = get_llm()
reply = llm.invoke("Say hello to a student in one short sentence.")
print(message_text(reply))