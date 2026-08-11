import { useState } from "react";

function WorkflowVisualizer({ agentStatuses = {}, metrics = {}, isVisible }) {
    const [selectedNode, setSelectedNode] = useState(null);

    if (!isVisible) return null;

    // Agent status bindings from backend LangGraph state
    const toolStatus = agentStatuses.tool || "WAITING";
    const researchStatus = agentStatuses.research || "WAITING";
    const planningStatus = agentStatuses.planning || "WAITING";
    const decisionStatus = agentStatuses.decision || "WAITING";
    const reportStatus = agentStatuses.report || "WAITING";

    const isGraphStarted = Object.values(agentStatuses).some((s) => s !== "WAITING");

    const queryStatus = isGraphStarted ? "COMPLETED" : "WAITING";
    const toolSelectionStatus = isGraphStarted ? "COMPLETED" : "WAITING";

    const steps = [
        {
            key: "query",
            status: queryStatus,
            label: "Business Query",
            purpose: "Receive and validate strategic business question",
            icon: "📝"
        },
        {
            key: "tool_selection",
            status: toolSelectionStatus,
            label: "Tool Selection",
            purpose: "Select relevant financial, ROI, or market risk model",
            icon: "🎯"
        },
        {
            key: "research",
            status: researchStatus,
            label: "Research Agent",
            purpose: "Analyze market demand, customer sentiment & competition",
            metricKey: "research_seconds",
            icon: "🔍"
        },
        {
            key: "tool",
            status: toolStatus,
            label: "Business Tools",
            purpose: "Execute Profit, ROI, Break-even, or Risk modeling",
            metricKey: "tool_seconds",
            icon: "📊"
        },
        {
            key: "planning",
            status: planningStatus,
            label: "Planning Agent",
            purpose: "Formulate multi-phase strategic execution roadmap",
            metricKey: "planning_seconds",
            icon: "🚀"
        },
        {
            key: "decision",
            status: decisionStatus,
            label: "Decision Agent",
            purpose: "Synthesize findings into executive decision recommendation",
            metricKey: "decision_seconds",
            icon: "⚖️"
        },
        {
            key: "report",
            status: reportStatus,
            label: "Report Generation",
            purpose: "Compile executive report & store in persistent DB",
            metricKey: "report_seconds",
            icon: "📄"
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
                return (
                    <span className="badge-running">
                        <span className="spinner-dot"></span> RUNNING
                    </span>
                );
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
        <section className="workflow-visualizer-card">
            <div className="visualizer-header">
                <div className="visualizer-title-area">
                    <span className="visualizer-eyebrow">LANGGRAPH ORCHESTRATION PIPELINE</span>
                    <h3 className="visualizer-headline">Autonomous Multi-Agent Workflow Execution</h3>
                </div>
                <span className="live-pill">
                    <span className="live-dot"></span> Real-time Graph State
                </span>
            </div>

            <div className="pipeline-flow-container">
                {steps.map((step, idx) => {
                    const statusClass = getStatusClass(step.status);
                    const timing = step.metricKey ? metrics[step.metricKey] : undefined;

                    return (
                        <div key={step.key} className="pipeline-node-wrapper">
                            <div
                                className={`pipeline-step-card ${statusClass}`}
                                onClick={() => setSelectedNode({ ...step, timing })}
                                title="Click to view node execution details"
                            >
                                <div className="step-card-top">
                                    <div className="step-num-icon-group">
                                        <span className="step-icon">{step.icon}</span>
                                        <span className="step-number">0{idx + 1}</span>
                                    </div>
                                    {getStatusBadge(step.status)}
                                </div>

                                <h4 className="step-label">{step.label}</h4>
                                <p className="step-desc">{step.purpose}</p>

                                {timing !== undefined && (
                                    <div className="step-timing-footer">
                                        <span>⏱ {timing}s</span>
                                    </div>
                                )}
                            </div>

                            {idx < steps.length - 1 && (
                                <div
                                    className={`pipeline-connector ${
                                        step.status === "COMPLETED" ? "completed" : ""
                                    }`}
                                >
                                    <span className="connector-arrow">→</span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Clickable Node Detail Popover Modal */}
            {selectedNode && (
                <div
                    className="node-detail-popover-backdrop"
                    onClick={() => setSelectedNode(null)}
                >
                    <div
                        className="node-detail-popover-card"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="popover-header">
                            <div className="popover-title-group">
                                <span className="popover-icon">{selectedNode.icon}</span>
                                <h4>{selectedNode.label}</h4>
                            </div>
                            <button
                                className="btn-close-popover"
                                onClick={() => setSelectedNode(null)}
                            >
                                ✕
                            </button>
                        </div>
                        <div className="popover-body">
                            <div className="popover-detail-row">
                                <span className="popover-label">Status:</span>
                                {getStatusBadge(selectedNode.status)}
                            </div>
                            <div className="popover-detail-row">
                                <span className="popover-label">Purpose:</span>
                                <span className="popover-val">{selectedNode.purpose}</span>
                            </div>
                            {selectedNode.timing !== undefined && (
                                <div className="popover-detail-row">
                                    <span className="popover-label">Execution Time:</span>
                                    <span className="popover-val">{selectedNode.timing} seconds</span>
                                </div>
                            )}
                            <div className="popover-info-callout">
                                <small>LANGGRAPH STATE GRAPH NODE</small>
                                <p>
                                    Executes within backend LangGraph orchestrator, updating shared
                                    state across agents and quantitative tools.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </section>
    );
}

export default WorkflowVisualizer;
