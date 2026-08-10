function WorkflowVisualizer({ agentStatuses = {}, isVisible }) {
    if (!isVisible) return null;

    const steps = [
        { key: "tool", label: "Business Tool", desc: "Quantifying financial & market risk" },
        { key: "research", label: "Research Agent", desc: "Evaluating market demand & competition" },
        { key: "planning", label: "Planning Agent", desc: "Structuring execution roadmap" },
        { key: "decision", label: "Decision Agent", desc: "Synthesizing executive recommendation" },
        { key: "report", label: "Report Node", desc: "Compiling decision document" }
    ];

    const getStatusClass = (status) => {
        switch (status) {
            case "RUNNING":
                return "status-running";
            case "COMPLETED":
                return "status-completed";
            case "FAILED":
                return "status-failed";
            case "SKIPPED":
                return "status-skipped";
            default:
                return "status-queued";
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case "RUNNING":
                return <span className="mini-spinner-blue"></span>;
            case "COMPLETED":
                return <span className="icon-check">✓</span>;
            case "FAILED":
                return <span className="icon-fail">✕</span>;
            case "SKIPPED":
                return <span className="icon-skip">⊘</span>;
            default:
                return <span className="icon-dot">•</span>;
        }
    };

    return (
        <div className="workflow-visualizer-card">
            <div className="visualizer-header">
                <div className="visualizer-title-area">
                    <span className="visualizer-eyebrow">LANGGRAPH ORCHESTRATION</span>
                    <h3 className="visualizer-headline">Active Multi-Agent Workflow</h3>
                </div>
                <span className="live-pill">
                    <span className="live-dot"></span> Real-time Graph State
                </span>
            </div>

            <div className="pipeline-steps-grid">
                {steps.map((step, idx) => {
                    const status = agentStatuses[step.key] || "QUEUED";
                    const statusClass = getStatusClass(status);

                    return (
                        <div key={step.key} className={`pipeline-step-card ${statusClass}`}>
                            <div className="step-card-top">
                                <span className="step-number">0{idx + 1}</span>
                                <span className={`step-badge-status ${statusClass}`}>
                                    {getStatusIcon(status)}
                                    <span className="badge-text">{status}</span>
                                </span>
                            </div>

                            <h4 className="step-label">{step.label}</h4>
                            <p className="step-desc">{step.desc}</p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default WorkflowVisualizer;
