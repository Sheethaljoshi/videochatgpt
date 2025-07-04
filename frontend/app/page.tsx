'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Play, Eye, MessageCircle, BookOpen } from 'lucide-react'

export default function Home() {
  type Message = { 
    type: 'user' | 'bot' | 'step'; 
    content: string; 
    stepNumber?: number;
    isLastStep?: boolean;
  }
  
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [currentVideoId, setCurrentVideoId] = useState('dQw4w9WgXcQ') // Default video
  const [currentVideoTitle, setCurrentVideoTitle] = useState('Rick Astley - Never Gonna Give You Up')
  const [currentVideoViews, setCurrentVideoViews] = useState(1000000000)
  const [isLoading, setIsLoading] = useState(false)
  const [isDisplayingSteps, setIsDisplayingSteps] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const displayStepsWithDelay = async (steps: string[]) => {
    setIsDisplayingSteps(true)
    
    // Add an intro message
    setMessages(prev => [...prev, { 
      type: 'bot', 
      content: "Let me break this down step by step:" 
    }])
    
    // Add each step with a delay
    for (let i = 0; i < steps.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 800)) // 800ms delay between steps
      
      setMessages(prev => [...prev, { 
        type: 'step', 
        content: steps[i],
        stepNumber: i + 1,
        isLastStep: i === steps.length - 1
      }])
    }
    
    setIsDisplayingSteps(false)
  }

  const sendMessage = async (e: { preventDefault: () => void; }) => {
    e.preventDefault()
    if (!inputMessage.trim()) return

    const userMessage = inputMessage.trim()
    setInputMessage('')
    setIsLoading(true)

    // Add user message to chat
    setMessages(prev => [...prev, { type: 'user', content: userMessage }])

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()
      
      // Change video first
      setCurrentVideoId(data.video_id)
      setCurrentVideoTitle(data.video_title)
      setCurrentVideoViews(data.video_views)
      
      // Display steps with animation
      if (data.reply_steps && data.reply_steps.length > 1) {
        await displayStepsWithDelay(data.reply_steps)
      } else {
        // Fallback for single response
        const content = data.reply_steps?.[0] || data.reply || "I've found a relevant video for you!"
        setMessages(prev => [...prev, { type: 'bot', content }])
      }
      
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, { 
        type: 'bot', 
        content: 'Sorry, there was an error processing your message.' 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: { key?: any; shiftKey?: any; preventDefault: any; }) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(e)
    }
  }

  const renderMessage = (message: Message, index: number) => {
    const isStep = message.type === 'step'
    const isUser = message.type === 'user'
    
    return (
      <div
        key={index}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-2 duration-500`}
      >
        <div className={`flex items-start space-x-2 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
          {isStep && (
            <div className="flex items-center justify-center w-6 h-6 bg-green-600 rounded-full text-white text-xs font-bold mt-1 flex-shrink-0">
              {message.stepNumber}
            </div>
          )}
          
          <div
            className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl shadow-lg ${
              isUser
                ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white'
                : isStep
                ? 'bg-gradient-to-r from-green-600 to-green-700 text-white border-l-4 border-green-400'
                : 'bg-gradient-to-r from-gray-600 to-gray-700 text-white border border-gray-500/30'
            }`}
          >
            <p className="text-sm leading-relaxed">{message.content}</p>
            {isStep && message.isLastStep && (
              <div className="mt-2 pt-2 border-t border-green-400/30">
                <div className="flex items-center space-x-1 text-xs text-green-200">
                  <BookOpen className="w-3 h-3" />
                  <span>Solution complete!</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Video Player Section - 3/4 of screen */}
      <div className="w-3/4 bg-black flex flex-col relative">
        {/* Video Info Header */}
        <div className="bg-gradient-to-r from-gray-900 to-gray-800 p-4 border-b border-gray-700/50 backdrop-blur-sm">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-8 h-8 bg-red-600 rounded-full">
              <Play className="w-4 h-4 text-white fill-white" />
            </div>
            <div className="flex-1">
              <h3 className="text-white text-base font-semibold truncate leading-tight">
                {currentVideoTitle}
              </h3>
              <div className="flex items-center space-x-2 mt-1">
                <Eye className="w-3 h-3 text-gray-400" />
                <p className="text-gray-400 text-xs">
                  {currentVideoViews.toLocaleString()} views
                </p>
              </div>
            </div>
          </div>
        </div>
        
        {/* Video Player */}
        <div className="flex-1 flex items-center justify-center relative">
          <div className="absolute inset-0 bg-gradient-to-t from-black/10 to-transparent pointer-events-none z-10"></div>
          <iframe
            width="100%"
            height="100%"
            src={`https://www.youtube.com/embed/${currentVideoId}?autoplay=1&mute=1`}
            title="YouTube video player"
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            className="w-full h-full"
          />
        </div>
      </div>

      {/* Chat Section - 1/4 of screen */}
      <div className="w-1/4 bg-gray-800/90 backdrop-blur-sm flex flex-col border-l border-gray-700/50">
        {/* Chat Header */}
        <div className="bg-gradient-to-r from-gray-700 to-gray-600 p-4 border-b border-gray-600/50">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-8 h-8 bg-blue-600 rounded-full">
              <MessageCircle className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-white text-lg font-bold">AI Math Tutor</h2>
              <p className="text-gray-300 text-xs">Ask me any math question!</p>
            </div>
          </div>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
          {messages.length === 0 && (
            <div className="text-center mt-12 px-2">
              <div className="bg-gray-700/50 rounded-xl p-6 backdrop-blur-sm border border-gray-600/30">
                <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-300 text-sm font-medium mb-2">Welcome to AI Math Tutor!</p>
                <p className="text-gray-400 text-xs leading-relaxed">
                  Ask me any math question and I'll break down the solution step by step while showing you relevant videos
                </p>
              </div>
            </div>
          )}
          
          {messages.map((message, index) => renderMessage(message, index))}
          
          {(isLoading || isDisplayingSteps) && (
            <div className="flex justify-start animate-in slide-in-from-bottom-2 duration-300">
              <div className="bg-gradient-to-r from-gray-600 to-gray-700 text-white px-4 py-3 rounded-2xl shadow-lg border border-gray-500/30">
                <div className="flex items-center space-x-3">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-white rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                  <span className="text-sm">
                    {isLoading ? 'Analyzing your question...' : 'Preparing next step...'}
                  </span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <div className="p-4 border-t border-gray-600/50 bg-gray-800/50">
          <div className="flex space-x-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me a math question..."
                className="w-full bg-gray-700/80 backdrop-blur-sm text-white px-4 py-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:bg-gray-700 transition-all duration-200 border border-gray-600/30 placeholder-gray-400"
                disabled={isLoading || isDisplayingSteps}
              />
            </div>
            <button
              type="submit"
              onClick={sendMessage}
              disabled={isLoading || isDisplayingSteps || !inputMessage.trim()}
              className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white p-3 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 active:scale-95 flex items-center justify-center min-w-[48px]"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(55, 65, 81, 0.3);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(107, 114, 128, 0.6);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(107, 114, 128, 0.8);
        }
        @keyframes slide-in-from-bottom-2 {
          from {
            transform: translateY(0.5rem);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        .animate-in {
          animation: slide-in-from-bottom-2 0.5s ease-out;
        }
      `}</style>
    </div>
  )
}