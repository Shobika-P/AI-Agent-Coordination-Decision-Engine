import { useState, useEffect } from "react";

function BusinessForm({ onGenerate, loading, initialTask }) {
    const [taskInput, setTaskInput] = useState(initialTask || "");
    const [forceRefresh, setForceRefresh] = useState(false);

    useEffect(() => {
        if (initialTask) {
            setTaskInput(initialTask);
        }
    }, [initialTask]);

    const presetPrompts = [
        "Should we launch personalized phone cases online?",
        "Should we expand our B2B SaaS platform to SMB markets?",
        "Is it profitable to start an eco-friendly direct-to-consumer apparel line?",
        "What is the break-even volume for launching a specialty coffee subscription?"
    ];

    const handleSubmit = (e) => {
        if (e) e.preventDefault();
        if (!taskInput.trim() || loading) return;
        onGenerate(taskInput.trim(), forceRefresh);
    };

    return (
        <section className="business-form-hero-card">
            <div className="hero-text-block">
                <span className="hero-eyebrow">ENTERPRISE DECISION INTELLIGENCE</span>
                <h2 className="hero-headline">Synthesize Autonomous AI Strategic Assessments</h2>
                <p className="hero-subtext">
                    Input your strategic business question to initiate LangGraph state graph orchestration,
                    quantitative tool execution, research modeling, and persistent SQLite report generation.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="query-input-wrapper">
                <div className="textarea-container">
                    <textarea
                        value={taskInput}
                        onChange={(e) => setTaskInput(e.target.value)}
                        placeholder="Describe your business problem, launch idea, or investment decision in detail..."
                        rows={3}
                        disabled={loading}
                    />
                </div>

                <div className="form-bottom-bar">
                    <div className="preset-prompts-flex">
                        <span className="presets-label">Preset Scenarios:</span>
                        {presetPrompts.map((promptText, idx) => (
                            <button
                                key={idx}
                                type="button"
                                className="btn-preset-chip"
                                onClick={() => setTaskInput(promptText)}
                                disabled={loading}
                            >
                                {promptText}
                            </button>
                        ))}
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12.5px", color: "var(--text-secondary, #9ca3af)", cursor: "pointer", userSelect: "none" }}>
                            <input
                                type="checkbox"
                                checked={forceRefresh}
                                onChange={(e) => setForceRefresh(e.target.checked)}
                                disabled={loading}
                                style={{ cursor: "pointer" }}
                            />
                            <span>Force Fresh AI</span>
                        </label>

                        <button
                            type="submit"
                            className="btn-submit-decision"
                            disabled={loading || !taskInput.trim()}
                        >
                            {loading ? (
                                <span className="btn-loading">
                                    <span className="spinner-dot"></span>
                                    <span>Analyzing Business Decision...</span>
                                </span>
                            ) : (
                                <span>Run Decision Engine →</span>
                            )}
                        </button>
                    </div>
                </div>
            </form>
        </section>
    );
}

export default BusinessForm;