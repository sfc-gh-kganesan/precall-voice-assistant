type Message = {
    role: "user" | "assistant";
    content: string;
  };
  
  export default function ChatWindow({ messages }: { messages: Message[] }) {
    return (
      <div className="flex-1 overflow-auto space-y-4 p-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`max-w-xl ${
              msg.role === "user" ? "ml-auto text-right" : ""
            }`}
          >
            <div
              className={`inline-block rounded px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-gray-600 text-white"
                  : "bg-pink-600 text-white"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
      </div>
    );
  }
  