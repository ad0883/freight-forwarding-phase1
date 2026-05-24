import { Bot, Send } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import api from '../api/client.js';
import { ErrorState } from '../components/States.jsx';

const fallbackPrompts = [
  'What shipments need attention today?',
  'Which tasks are overdue?',
  'Which shipments have demurrage running?',
  'Which BL approvals are pending?',
  'How much freight is uncollected?',
  'Which shipments are loss-making?',
];

function PriorityBadge({ priority }) {
  const value = priority || 'none';
  return <span className={`badge ai-priority-${value}`}>{value}</span>;
}

function AssistantMessage({ message }) {
  const response = message.response || {};
  const suggestedActions = response.suggested_actions || [];
  const dataPoints = response.data_points || [];

  return (
    <div className="chat-message assistant">
      <div className="message-meta">
        <span>AI Assistant</span>
        <PriorityBadge priority={response.priority} />
        {response.fallback_used && <span className="badge ai-fallback">Fallback mode</span>}
      </div>
      <p>{message.text}</p>
      {!!suggestedActions.length && (
        <div className="ai-response-block">
          <strong>Suggested actions</strong>
          <ul>
            {suggestedActions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </div>
      )}
      {!!dataPoints.length && (
        <div className="data-point-grid">
          {dataPoints.map((point) => (
            <div className="data-point" key={`${point.label}-${point.value}`}>
              <span>{point.label}</span>
              <strong>{point.value}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MockAiPage() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [examples, setExamples] = useState(fallbackPrompts);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    async function loadAssistantMeta() {
      try {
        const [examplesResponse, statusResponse] = await Promise.all([
          api.get('/ai/examples'),
          api.get('/ai/status'),
        ]);
        setExamples(examplesResponse.data.examples || fallbackPrompts);
        setStatus(statusResponse.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Unable to load AI assistant status');
      }
    }
    loadAssistantMeta();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: response.data.answer,
          response: response.data,
        },
      ]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to ask AI assistant');
    } finally {
      setLoading(false);
    }
  }

  const statusText = status?.ai_enabled
    ? `${status.provider} · ${status.model}`
    : 'Fallback mode available';

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Database-aware assistant</p>
          <h1>AI Assistant</h1>
        </div>
        <div className="ai-status">
          <span className={`status-dot ${status?.ai_enabled ? 'ready' : 'fallback'}`} />
          <strong>{statusText}</strong>
        </div>
      </div>

      <section className="panel ai-panel">
        <div className="prompt-row">
          {examples.slice(0, 11).map((prompt) => (
            <button key={prompt} className="secondary-button" type="button" onClick={(event) => ask(event, prompt)}>
              {prompt}
            </button>
          ))}
        </div>

        <div className="chat-window">
          {!messages.length && (
            <div className="empty-chat">
              <Bot size={32} />
              <p>Ask about shipments, risks, tasks, finance, follow-ups, or next actions.</p>
            </div>
          )}
          {messages.map((message, index) =>
            message.role === 'assistant' ? (
              <AssistantMessage message={message} key={`${message.role}-${index}`} />
            ) : (
              <div className="chat-message user" key={`${message.role}-${index}`}>
                <span>You</span>
                <p>{message.text}</p>
              </div>
            )
          )}
          {loading && (
            <div className="chat-message assistant">
              <span>AI Assistant</span>
              <p className="muted">Thinking...</p>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <ErrorState message={error} />
        <form className="ask-form" onSubmit={ask}>
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about shipments, finance, demurrage, BL, or next actions"
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
