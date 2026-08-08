import { useState } from "react";

function BusinessForm({ onGenerate, loading }) {
  const [task, setTask] = useState(
    "Should we launch personalized phone cases online?"
  );

  const examples = [
    "Should we launch personalized phone cases online?",
    "Should we launch an eco-friendly water bottle for college students?",
    "Should we start an online food delivery business?",
    "Should we launch an AI-powered student learning app?"
  ];

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!task.trim()) return;

    onGenerate(task);
  };

  return (
    <>
      {/* HERO */}
      <section className="hero">

        <span className="hero-badge">
          AI-POWERED BUSINESS ANALYSIS
        </span>

        <h1>
          Turn Your Business Idea
          <br />
          Into a Smart Decision
        </h1>

        <p>
          Enter your business idea and let AI analyze market risk,
          research, planning, and strategic decision factors.
        </p>

      </section>

      {/* BUSINESS INPUT */}
      <section className="business-card">

        <form onSubmit={handleSubmit}>

          <label htmlFor="businessIdea">
            Enter your business idea
          </label>

          <textarea
            id="businessIdea"
            className="business-input"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Example: Should we launch a personalized phone case business?"
          />

          {/* EXAMPLES */}
          <div className="examples">

            <div className="examples-title">
              Not sure what to ask? Try an example:
            </div>

            <div className="example-buttons">

              {examples.map((example, index) => (
                <button
                  key={index}
                  type="button"
                  className="example-button"
                  onClick={() => setTask(example)}
                >
                  {example}
                </button>
              ))}

            </div>

          </div>

          {/* GENERATE */}
          <button
            type="submit"
            className="generate-button"
            disabled={loading}
          >
            {loading
              ? "Analyzing Business Idea..."
              : "Generate Business Report →"}
          </button>

        </form>

      </section>
    </>
  );
}

export default BusinessForm;