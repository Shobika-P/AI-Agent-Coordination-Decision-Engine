import { useState } from "react";

function WorkflowVisualizer({ agentStatuses = {}, metrics = {}, isVisible }) {
    const [selectedNode, setSelectedNode] = useState(null);

    if (!isVisible) return null;

    const steps = [
        {
            key: "tool",
            label: "Tool Selection & Execution",
            purpose: "Evaluate business problem to select & execute financial or market risk tool",
            metricKey: "tool_seconds"
        },
        {
            key: "research",
            label: "Research Agent",
            purpose: "Analyze market size, customer demand, and competitive pressure",
            metricKey: "research_seconds"
        },
        {
            key: "planning",
            label: "Planning Agent",
            purpose: "Formulate strategic multi-phase business execution roadmap",
            metricKey: "planning_seconds"
        },
        {
            key: "decision",
            label: "Decision Agent",
            purpose: "Synthesize quantitative & qualitative agent data into final decision",
            metricKey: "decision_seconds"
        },
        {
            key: "report",
            label: "Report Compilation Node",
            purpose: "Assemble executive assessment document and save to SQLite DB",
            metricKey: "report_seconds"
        }
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
                return "status-waiting";
        }
    };

    const getStatusBadge = (status) => {
        switch (status) {
            case "RUNNING":
                return <span className="badge-running"><span className="spinner-dot"></span> RUNNING</span>;
            case "COMPLETED":
                return <span className="badge-completed">✓ COMPLETED</span>;
            case "FAILED":
                return <span className="badge-failed">✕ FAILED</span>;
            case "SKIPPED":
                return <span className="badge-skipped">⊘ SKIPPED</span>;
            default:
                return <span className="badge-waiting">• WAITING</span>;
        }
    };

    return (
        <div className="workflow-visualizer-card">
            <div className="visualizer-header">
                <div className="visualizer-title-area">
                    <span className="visualizer-eyebrow">LANGGRAPH STATEGRAPH PIPELINE</span>
                    <h3 className="visualizer-headline">Autonomous Multi-Agent Workflow Execution</h3>
                </div>
                <span className="live-pill">
                    <span className="live-dot"></span> Real-time Graph State
                </span>
            </div>

            <div className="pipeline-steps-grid">
                {steps.map((step, idx) => {
                    const status = agentStatuses[step.key] || "WAITING";
                    const statusClass = getStatusClass(status);
                    const timing = metrics[step.metricKey] || metrics[`step_${idx+1}_${step.key}_seconds`];

                    return (
                        <div
                            key={step.key}
                            className={`pipeline-step-card ${statusClass}`}
                            onClick={() => setSelectedNode({ ...step, status, timing })}
                        >
                            <div className="step-card-top">
                                <span className="step-number">0{idx + 1}</span>
                                {getStatusBadge(status)}
                            </div>

                            <h4 className="step-label">{step.label}</h4>
                            <p className="step-desc">{step.purpose}</p>

                            {timing !== undefined && (
                                <div className="step-timing-footer">
                                    <span>⏱ {timing}s</span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Clickable Node Detail Modal */}
            {selectedNode && (
                <div className="node-detail-popover-backdrop" onClick={() => setSelectedNode(null)}>
                    <div className="node-detail-popover-card" onClick={(e) => e.stopPropagation()}>
                        <div className="popover-header">
                            <h4>{selectedNode.label}</h4>
                            <button className="btn-close-popover" onClick={() => setSelectedNode(null)}>✕</button>
                        </div>
                        <div className="popover-body">
                            <p><strong>Status:</strong> {selectedNode.status}</p>
                            <p><strong>Purpose:</strong> {selectedNode.purpose}</p>
                            {selectedNode.timing && <p><strong>Execution Time:</strong> {selectedNode.timing} seconds</p>}
                            <div className="popover-info-callout">
                                <small>LANGGRAPH NODE METADATA</small>
                                <p>Executed inside backend StateGraph workflow context with isolated state scope.</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default WorkflowVisualizer;

