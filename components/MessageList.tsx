'use client';

import { useEffect, useRef } from 'react';
import { Message } from '@/types';

interface Props {
  messages: Message[];
  streaming: boolean;
}

export default function MessageList({ messages, streaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
        <div className="text-5xl mb-4">✦</div>
        <p className="text-xl font-medium text-gray-400">무엇이든 물어보세요</p>
        <p className="text-sm mt-2">모델을 선택하고 메시지를 입력하세요</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto py-6 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.map((msg, idx) => (
          <div
            key={msg.id}
            className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-pink-500 flex items-center justify-center flex-shrink-0 text-white text-sm font-bold mt-1">
                A
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-sm'
                  : 'bg-gray-700 text-gray-100 rounded-bl-sm'
              }`}
            >
              {msg.content}
              {streaming && idx === messages.length - 1 && msg.role === 'assistant' && (
                <span className="inline-block w-0.5 h-4 bg-gray-400 ml-0.5 animate-pulse align-middle" />
              )}
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0 text-white text-sm font-bold mt-1">
                U
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
