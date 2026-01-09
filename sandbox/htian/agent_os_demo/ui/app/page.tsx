"use client";

import { useState } from "react";
import ChatWindow from "./components/chatWindow";
import ChatInput from "./components/chatInput";
import { sendBrainMessage } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function BrainPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleSend(text: string) {
    const nextMessages = [...messages, { role: "user", content: text }];
    
    setMessages(nextMessages);
    setLoading(true);

    try {
      const res = await sendBrainMessage(nextMessages);
      setMessages((msgs) => [
        ...msgs,
        { role: "assistant", content: res.reply },
      ]);
    } catch {
      setMessages((msgs) => [
        ...msgs,
        {
          role: "assistant",
          content: "Error talking to Brain.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="p-4 border-b">
        <h1 className="font-semibold">Brain</h1>
        <p className="text-xs text-gray-600">
          Chat-based interface to the MetaOrchestrator (sandbox)
        </p>
      </div>

      <ChatWindow messages={messages} />
      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}
