

type Message = {
    role: "user" | "assistant";
    content: string;
}

export async function sendBrainMessage(messages: Message[]) {

    console.log("process.env.NEXT_PUBLIC_BRAIN_API_URL =", process.env.NEXT_PUBLIC_BRAIN_API_URL);

    const res = await fetch(`${process.env.NEXT_PUBLIC_BRAIN_API_URL}/v1/brain/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: messages }),
    });
  
    if (!res.ok) {
      throw new Error("Brain request failed");
    }
  
    return res.json();
  }
  