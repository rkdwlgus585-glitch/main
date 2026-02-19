'use client';

import { useState, useEffect, useCallback } from 'react';
import { Conversation, Message, ModelId } from '@/types';

const STORAGE_KEY = 'chatbot_conversations';

function generateId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed: Conversation[] = JSON.parse(stored);
        setConversations(parsed);
        if (parsed.length > 0) setActiveId(parsed[0].id);
      }
    } catch {
      // ignore parse errors
    }
  }, []);

  const persist = useCallback((convs: Conversation[]) => {
    setConversations(convs);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(convs));
  }, []);

  const createConversation = useCallback(
    (model: ModelId): Conversation => {
      const conv: Conversation = {
        id: generateId(),
        title: '새 대화',
        model,
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      const updated = [conv, ...conversations];
      persist(updated);
      setActiveId(conv.id);
      return conv;
    },
    [conversations, persist],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      const updated = conversations.filter((c) => c.id !== id);
      persist(updated);
      if (activeId === id) {
        setActiveId(updated.length > 0 ? updated[0].id : null);
      }
    },
    [conversations, persist, activeId],
  );

  const appendMessage = useCallback(
    (convId: string, message: Message) => {
      setConversations((prev) => {
        const updated = prev.map((c) => {
          if (c.id !== convId) return c;
          const msgs = [...c.messages, message];
          const title =
            c.title === '새 대화' && message.role === 'user'
              ? message.content.slice(0, 40)
              : c.title;
          return { ...c, messages: msgs, title, updatedAt: Date.now() };
        });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
        return updated;
      });
    },
    [],
  );

  const updateLastAssistantMessage = useCallback(
    (convId: string, content: string) => {
      setConversations((prev) => {
        const updated = prev.map((c) => {
          if (c.id !== convId) return c;
          const msgs = [...c.messages];
          const lastIdx = msgs.length - 1;
          if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
            msgs[lastIdx] = { ...msgs[lastIdx], content };
          }
          return { ...c, messages: msgs, updatedAt: Date.now() };
        });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
        return updated;
      });
    },
    [],
  );

  const updateModel = useCallback(
    (convId: string, model: ModelId) => {
      setConversations((prev) => {
        const updated = prev.map((c) =>
          c.id === convId ? { ...c, model } : c,
        );
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
        return updated;
      });
    },
    [],
  );

  const activeConversation =
    conversations.find((c) => c.id === activeId) ?? null;

  return {
    conversations,
    activeId,
    activeConversation,
    setActiveId,
    createConversation,
    deleteConversation,
    appendMessage,
    updateLastAssistantMessage,
    updateModel,
  };
}
