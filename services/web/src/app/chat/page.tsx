"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/store/session";
import ChatView from "@/components/chat-view";
import ChatActions from "@/components/chat-actions";
import StepDots from "@/components/step-dots";

export default function ChatPage() {
  const router = useRouter();
  const sessionId = useSessionStore((s) => s.sessionId);

  useEffect(() => {
    if (!sessionId) router.replace("/");
  }, [sessionId, router]);

  if (!sessionId) return null;

  return (
    <div>
      <StepDots total={3} current={1} />
      <ChatActions />
      <ChatView />
    </div>
  );
}
