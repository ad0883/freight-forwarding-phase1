import { Bot, Send } from 'lucide-react';
import { useState } from 'react';
import api from '../api/client.js';

const prompts = [
  'Which tasks are pending?',
  'Which shipments have BL approval pending?',
  'Show shipment status.',
];

function MockAiPage() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function ask(event, promptOverride) {
    event?.preventDefault();
    const prompt = promptOverride || question;
    if (!prompt.trim()) return;
    setError('');
    setLoading(true);
    setMessages((current) => [...current, { role: 'user', text: prompt }]);
    setQuestion('');
    try {
      const response = await api.post('/ai/ask', { question: prompt });
      setMessages((current) => [...current, { role: 'assistant', text: response.data.answer }]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to ask mock AI');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Rule-based assistant</p>
          <h1>Mock AI</h1>
        </div>
      </div>

      <section className="panel ai-panel">
        <div className="prompt-row">
          {prompts.map((prompt) => (
            <button key={prompt} className="secondary-button" type="button" onClick={(event) => ask(event, prompt)}>
              {prompt}
            </button>
          ))}
        </div>

        <div className="chat-window">
          {!messages.length && (
            <div className="empty-chat">
              <Bot size={30} />
              <p>Ask a Phase 1 operations question.</p>
            </div>
          )}
          {messages.map((message, index) => (
            <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
              <span>{message.role === 'user' ? 'You' : 'Mock AI'}</span>
              <p>{message.text}</p>
            </div>
          ))}
        </div>

        {error && <p className="error-text">{error}</p>}
        <form className="ask-form" onSubmit={ask}>
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about tasks, BL approval, or shipment status"
          />
          <button className="primary-button" type="submit" disabled={loading}>
            <Send size={18} />
            <span>{loading ? 'Asking...' : 'Ask'}</span>
          </button>
        </form>
      </section>
    </div>
  );
}

export default MockAiPage;
