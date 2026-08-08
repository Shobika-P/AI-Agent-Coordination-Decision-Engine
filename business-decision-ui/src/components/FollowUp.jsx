import { useState } from "react";

function FollowUp({ onAsk, loading, disabled }) {

  const [question, setQuestion] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!question.trim()) return;

    onAsk(question);
    setQuestion("");
  };

  return (
    <div className="followup-card">

      <div className="followup-header">

        <div>
          <h2>Ask About This Decision</h2>

          <p>
            Have a follow-up question? Ask the AI using your
            business report as context.
          </p>
        </div>

        <span className="followup-icon">
          💬
        </span>

      </div>

      <form onSubmit={handleSubmit}>

        <textarea
          className="followup-input"
          placeholder="Example: What should we do first to reduce the market risk?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={disabled || loading}
        />

        <button
          type="submit"
          className="followup-button"
          disabled={
            disabled ||
            loading ||
            !question.trim()
          }
        >
          {loading ? "Thinking..." : "Ask AI →"}
        </button>

      </form>

    </div>
  );
}

export default FollowUp;