import { useState, useRef, useEffect } from "react";
import { getMedicalAdvice } from "../api";

export default function MedicalChat({ onBack, user }) {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  async function sendMessage() {
    if (!inputText.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: inputText,
      timestamp: new Date().toISOString(),
      sender: user?.name || "You"
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText("");
    setIsLoading(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      const response = await getMedicalAdvice(inputText);

      const aiMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: response.result,
        timestamp: new Date().toISOString(),
        sender: "HealthEcho AI",
        recommendations: response.recommendations
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error("Failed to get medical advice:", error);
      
      const errorMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: "I apologize, but I'm having trouble processing your request. Please try again or consult with a healthcare professional for immediate concerns.",
        timestamp: new Date().toISOString(),
        sender: "HealthEcho AI",
        isError: true
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyPress(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: "2-digit", 
      minute: "2-digit" 
    });
  }

  function clearChat() {
    if (window.confirm("Are you sure you want to clear the chat history?")) {
      setMessages([]);
    }
  }

  return (
    <div className="medical-chat-page">
      <div className="chat-header">
        <div className="chat-header-left">
          <button className="back-btn" onClick={onBack}>←</button>
          <div className="chat-title">
            <h2>
              <span>⚕️</span> HealthEcho
            </h2>
            <p>AI Medical Assistant</p>
          </div>
        </div>

        <div className="chat-header-actions">
          <button className="clear-chat-btn" onClick={clearChat}>
            Clear Chat
          </button>
        </div>
      </div>

      <div className="chat-main">
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-center">
              <div className="ai-icon">⚕️</div>
              <h1>How can I help you today?</h1>
              <p>
                I'm your AI medical assistant. Describe your symptoms, ask about medications, 
                or get general health advice. Remember, I'm here to assist, not replace 
                professional medical care.
              </p>
              <div className="chat-tips">
                <span className="tip">💊 Medication questions</span>
                <span className="tip">🤒 Symptom checker</span>
                <span className="tip">🏥 Treatment options</span>
                <span className="tip">📋 Health information</span>
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === "user" ? "👤" : "⚕️"}
                </div>
                <div className="message-content">
                  <div className="message-header">
                    <span className="message-sender">{msg.sender}</span>
                    <span className="message-time">{formatTime(msg.timestamp)}</span>
                  </div>
                  <div className="message-text">
                    {msg.content}
                  </div>
                  {msg.recommendations && (
                    <div className="medical-recommendation">
                      <div className="recommendation-title">
                        <span>📋</span> Medical Recommendations
                      </div>
                      <p>{msg.recommendations}</p>
                    </div>
                  )}
                  <div className="medical-disclaimer">
                    ⚠️ This is AI-generated information. Always consult with a healthcare professional.
                  </div>
                </div>
              </div>
            ))
          )}

          {isLoading && (
            <div className="message assistant">
              <div className="message-avatar">⚕️</div>
              <div className="message-content">
                <div className="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <div className="input-container">
            <textarea
              ref={textareaRef}
              placeholder="Describe your symptoms or ask a health question..."
              value={inputText}
              onChange={(e) => {
                setInputText(e.target.value);
                adjustTextareaHeight();
              }}
              onKeyDown={handleKeyPress}
              disabled={isLoading}
              rows="1"
            />
            <div className="input-actions">
              <button 
                className="action-btn send-btn"
                onClick={sendMessage}
                disabled={isLoading || !inputText.trim()}
              >
                ➤
              </button>
            </div>
          </div>
          <small style={{ color: '#64748b', marginTop: '0.5rem', display: 'block' }}>
            Press Enter to send, Shift+Enter for new line
          </small>
        </div>
      </div>
    </div>
  );
}