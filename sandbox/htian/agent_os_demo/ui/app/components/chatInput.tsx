"use client";

import { useState } from "react";

export default function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const [text, setText] = useState("");

  function handleSend() {
    if (!text.trim()) return;
    onSend(text);
    setText("");
  }

  return (
    <div className="border-t p-4 flex gap-2">
      <input
        className="flex-1 border rounded px-3 py-2 text-sm"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
        placeholder="Talk to the Brain…"
        disabled={disabled}
      />
      <button
        className="px-4 py-2 bg-pink-600 text-white rounded text-sm"
        onClick={handleSend}
        disabled={disabled}
      >
        Send
      </button>
    </div>
  );
}
