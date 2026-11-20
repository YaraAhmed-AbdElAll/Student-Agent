from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from student_agent import graph as graph_module
from student_agent.graph import build_graph, chat
from student_agent.tools import langchain_tools as lt


class FakeLLM:
    """Plays the model: returns prepared replies and records what it was shown."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.seen.append(list(messages))
        return self.replies.pop(0)


def ask_tool(name, **args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": "call_1"}])


def say(text):
    return AIMessage(content=text)


def must_not_run(*args):
    raise AssertionError("this must not run")


def new_graph(llm):
    return build_graph(llm=llm, checkpointer=InMemorySaver())


def test_tool_result_goes_back_to_the_model(monkeypatch):
    owner = {}

    def fake_owns(student_id, user_course_id):
        owner["pair"] = (student_id, user_course_id)
        return True

    monkeypatch.setattr(lt, "owns_course", fake_owns)
    monkeypatch.setattr(lt, "get_course_overview", lambda *a: {"status": "OK", "marker": "ABC123"})

    llm = FakeLLM([ask_tool("get_course_overview", user_course_id=5), say("You are fine.")])
    text, tools_used = chat(new_graph(llm), 9, "How am I doing?")

    assert text == "You are fine."
    assert tools_used == ["get_course_overview"]
    assert owner["pair"] == (9, 5)  # the student comes from chat(), not from the model
    tool_messages = [m for m in llm.seen[1] if isinstance(m, ToolMessage)]
    assert "ABC123" in tool_messages[0].content


def test_other_students_course_is_blocked(monkeypatch):
    monkeypatch.setattr(lt, "owns_course", lambda student_id, user_course_id: False)
    monkeypatch.setattr(lt, "get_course_overview", must_not_run)

    llm = FakeLLM([ask_tool("get_course_overview", user_course_id=99), say("Not found.")])
    chat(new_graph(llm), 1, "Show me course 99")

    tool_messages = [m for m in llm.seen[1] if isinstance(m, ToolMessage)]
    assert "NOT_YOURS" in tool_messages[0].content


# def test_history_is_kept_between_turns():
#     llm = FakeLLM([say("first"), say("second")])
#     graph = new_graph(llm)
#     chat(graph, 1, "Hello")
#     chat(graph, 1, "And now?")
#     assert [m.content for m in llm.seen[1]] == ["Hello", "first", "And now?"]


# def test_students_do_not_share_history():
#     llm = FakeLLM([say("a"), say("b")])
#     graph = new_graph(llm)
#     chat(graph, 1, "I am student one")
#     chat(graph, 2, "I am student two")
#     assert [m.content for m in llm.seen[1]] == ["I am student two"]


def test_system_prompt_is_added_but_not_stored(monkeypatch):
    monkeypatch.setattr(graph_module, "SYSTEM_PROMPT", "RULES")
    llm = FakeLLM([say("one"), say("two")])
    graph = new_graph(llm)
    chat(graph, 1, "Hi")
    chat(graph, 1, "Again")
    for call in llm.seen:
        assert isinstance(call[0], SystemMessage)
        assert call[0].content == "RULES"
        assert sum(isinstance(m, SystemMessage) for m in call) == 1


def test_tools_used_counts_only_the_current_turn(monkeypatch):
    monkeypatch.setattr(lt, "owns_course", lambda student_id, user_course_id: True)
    monkeypatch.setattr(lt, "get_course_overview", lambda *a: {"status": "OK"})

    llm = FakeLLM([ask_tool("get_course_overview", user_course_id=5), say("ok"), say("sure")])
    graph = new_graph(llm)
    _, first = chat(graph, 1, "Q1")
    _, second = chat(graph, 1, "Q2")

    assert first == ["get_course_overview"]
    assert second == []