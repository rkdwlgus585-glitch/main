'use client';

import { useState, useCallback } from 'react';
import { ModelId } from '@/types';
import { useConversations } from '@/hooks/useConversations';
import Sidebar from './Sidebar';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import ModelSelector from './ModelSelector';

function generateId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export default function ChatInterface() {
  const [streaming, setStreaming] = useState(false);
  const {
    conversations,
    activeId,
    activeConversation,
    setActiveId,
    createConversation,
    deleteConversation,
    appendMessage,
    updateLastAssistantMessage,
    updateModel,
  } = useConversations();

  const [pendingModel, setPendingModel] = useState<ModelId>('claude-sonnet-4-5-20250929');

  const currentModel: ModelId =
    (activeConversation?.model as ModelId) ?? pendingModel;

  const handleModelChange = (model: ModelId) => {
    if (activeConversation) {
      updateModel(activeConversation.id, model);
    } else {
      setPendingModel(model);
    }
  };

  const handleNewConversation = useCallback(() => {
    createConversation(pendingModel);
  }, [createConversation, pendingModel]);

  const handleSend = useCallback(
    async (content: string) => {
      let conv = activeConversation;
      if (!conv) {
        conv = createConversation(pendingModel);
      }

      const userMsg = {
        id: generateId(),
        role: 'user' as const,
        content,
        timestamp: Date.now(),
      };
      appendMessage(conv.id, userMsg);

      const assistantMsg = {
        id: generateId(),
        role: 'assistant' as const,
        content: '',
        timestamp: Date.now(),
      };
      appendMessage(conv.id, assistantMsg);
      setStreaming(true);

      try {
        const messages = [
          ...conv.messages.map((m) => ({ role: m.role, content: m.content })),
          { role: 'user', content },
        ];

        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages, model: conv.model }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: 'Unknown error' }));
          updateLastAssistantMessage(conv.id, `오류: ${err.error ?? res.statusText}`);
          return;
        }

        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        let accumulated = '';

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            accumulated += decoder.decode(value, { stream: true });
            updateLastAssistantMessage(conv.id, accumulated);
          }
        }
      } catch (err) {
        updateLastAssistantMessage(conv.id, `네트워크 오류가 발생했습니다.`);
        console.error(err);
      } finally {
        setStreaming(false);
      }
    },
    [
      activeConversation,
      createConversation,
      pendingModel,
      appendMessage,
      updateLastAssistantMessage,
    ],
  );

  return (
    <div className="flex h-screen bg-gray-800 text-white">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNewConversation}
        onDelete={deleteConversation}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800">
          <h1 className="font-semibold text-gray-200">Claude Chat</h1>
          <ModelSelector
            value={currentModel}
            onChange={handleModelChange}
            disabled={streaming}
          />
        </header>

        <MessageList
          messages={activeConversation?.messages ?? []}
          streaming={streaming}
        />

        <MessageInput onSend={handleSend} disabled={streaming} />
      </div>
    </div>
  );
}
