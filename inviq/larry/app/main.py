from app.graph import create_graph

graph = create_graph()

if __name__ == "__main__":
    messages = graph.invoke({"messages": []})
    for m in messages["messages"]:
        m.pretty_print()
