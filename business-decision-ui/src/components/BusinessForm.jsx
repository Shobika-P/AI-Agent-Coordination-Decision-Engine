import { useState, useEffect } from "react";

function BusinessForm({ onGenerate, loading, initialTask }) {
    const [task, setTask] = useState(
        initialTask || "Should we launch personalized phone cases online?"
    );

    useEffect(() => {
        if (initialTask) {
            setTask(initialTask);
        }
    }, [initialTask]);

    const examples = [
        { text: "Should we launch personalized phone cases online?", tag: "E-Commerce" },
        { text: "Should we launch an eco-friendly water bottle for college students?", tag: "Consumer Product" },
        { text: "Should we start an online food delivery business?", tag: "Services" },
        { text: "Should we launch an AI-powered student learning app?", tag: "SaaS / Tech" }
    ];

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!task.trim() || loading) return;
        onGenerate(task);
    };

    return (
        <section className="hero-section">
            <div className="hero-header">
                <div className="hero-eyebrow">
                    <span className="pulse-dot"></span>
                    <span>MULTI-AGENT DECISION ENGINE</span>
                </div>

                <h1 className="hero-title">
                    Turn complex business questions <br />
                    into <span className="gradient-text">strategic decisions.</span>
                </h1>

                <p className="hero-subtitle">
                    Autonomous AI agents execute market research, quantitative financial risk modeling,
                    and step-by-step strategic planning orchestrated via LangGraph workflows.
                </p>
            </div>

            <div className="input-card">
                <form onSubmit={handleSubmit}>
                    <div className="input-header-row">
                        <label className="input-label" htmlFor="business-task-input">
                            What business decision are you evaluating?
                        </label>
                        <span className="char-counter">
                            {task.length} characters
                        </span>
                    </div>

                    <div className="textarea-wrapper">
                        <textarea
                            id="business-task-input"
                            value={task}
                            onChange={(e) => setTask(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                                    e.preventDefault();
                                    if (task.trim() && !loading) {
                                        onGenerate(task);
                                    }
                                }
                            }}
                            placeholder="Describe your business idea, target market, pricing model, or strategic dilemma..."
                            rows={4}
                            disabled={loading}
                        />

                        {task && !loading && (
                            <button
                                type="button"
                                className="clear-input-btn"
                                onClick={() => setTask("")}
                                title="Clear input"
                            >
                                ✕
                            </button>
                        )}
                    </div>

                    <div className="examples-area">
                        <span className="examples-label">
                            💡 Try a curated business scenario:
                        </span>

                        <div className="example-chips-grid">
                            {examples.map((item, index) => (
                                <button
                                    type="button"
                                    key={index}
                                    className={`example-chip ${task === item.text ? "active" : ""}`}
                                    onClick={() => setTask(item.text)}
                                    disabled={loading}
                                >
                                    <span className="chip-tag">{item.tag}</span>
                                    <span className="chip-text">{item.text}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="form-submit-row">
                        <span className="keyboard-hint">
                            Press Ctrl + Enter to launch graph workflow
                        </span>

                        <button
                            type="submit"
                            className="btn-primary-gradient"
                            disabled={loading || !task.trim()}
                        >
                            {loading ? (
                                <span className="btn-spinner-state">
                                    <span className="spinner-icon"></span>
                                    <span>Orchestrating Graph Workflow...</span>
                                </span>
                            ) : (
                                <span>Run Multi-Agent Engine →</span>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </section>
    );
}

export default BusinessForm;