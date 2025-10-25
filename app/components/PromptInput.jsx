"use client"
import React, { useState } from 'react'
import { PaperAirplaneIcon } from '@heroicons/react/24/solid'

export default function PromptInput({ onSend }) {
  const [input, setInput] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim()) {
      onSend(input.trim())
      setInput('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative flex-1">
      <div className="flex items-center gap-3 px-2 py-2 rounded-full border border-neutral-700 bg-neutral-800/50 backdrop-blur-sm">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about nearby restaurants..."
          className="flex-1 ml-5 bg-transparent text-white placeholder-neutral-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!input.trim()}
          className="p-2 rounded-full bg-blue-600 hover:bg-blue-700 hover:cursor-pointer disabled:bg-neutral-600 disabled:cursor-not-allowed transition-colors"
        >
          <PaperAirplaneIcon className="size-7 shrink-0 text-white" />
        </button>
      </div>
    </form>
  )
}
