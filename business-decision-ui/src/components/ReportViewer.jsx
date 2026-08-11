import { useState, useRef, useEffect } from "react";
import API from "../services/api";
import WhatIfPanel from "./WhatIfPanel";

function safeString(value, fallback = "") {
    if (value === null || value === undefined) return fallback;
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    if (Array.isArray(value)) {
        return value.map((item) => safeString(item)).join("\n");
    }
    if (typeof value === "object") {
        try {
            return JSON.stringify(value, null, 2);
        } catch {
            return fallback;
        }
    }
    return fallback;
}

function ReportViewer({
    report,
    task,
    loading,
    error,
    quotaNotice,
    followupMessages = [],
    onFollowup,
    onClearFollowup,
    onRetry
}) {
    const [localFollowupText, setLocalFollowupText] = useState("");
    const [showExportMenu, setShowExportMenu] = useState(false);
    const [exporting, setExporting] = useState(false);
    const [toastMsg, setToastMsg] = useState("");
    const [dynamicViability, setDynamicViability] = useState(null);
    const [dynamicRisk, setDynamicRisk] = useState(null);

    const threadEndRef = useRef(null);

    useEffect(() => {
        if (followupMessages.length > 0) {
            threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [followupMessages]);

    useEffect(() => {
        setDynamicViability(null);
        setDynamicRisk(null);
    }, [report]);

    const suggestedChips = [
        "Why is the market risk medium?",
        "How can we lower customer acquisition cost?",
        "What happens if sales volume drops by 20%?",
        "What are our top 3 execution priorities?"
    ];

    const handleExport = async (format) => {
        setShowExportMenu(false);

        if (format === "copy") {
            const decisionText = safeString(report?.decision);
            const riskText = safeString(dynamicRisk || report?.risk_level || report?.tool_analysis?.risk_level, "Medium");
            const copyContent = `ENTERPRISE AI DECISION REPORT\nQuery: ${task}\nRisk Level: ${riskText}\nViability Score: ${dynamicViability || report?.viability_score || 78}/100\n\n${decisionText}`;
            navigator.clipboard.writeText(copyContent);
            setToastMsg("Report copied to clipboard!");
            setTimeout(() => setToastMsg(""), 3000);
            return;
        }

        if (format === "print") {
            window.print();
            return;
        }

        setExporting(true);
        try {
            const response = await API.post(
                "/export-report",
                {
                    task: task || "Business Decision Query",
                    report: report,
                    conversation_history: followupMessages.map(m => ({ question: m.question, answer: m.answer })),
                    format: format
                },
                { responseType: format === "pdf" ? "blob" : "text" }
            );

            if (format === "pdf") {
                const blob = new Blob([response.data], { type: "application/pdf" });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `Decision_Report_${Date.now().toString().slice(-6)}.pdf`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } else if (format === "json") {
                const blob = new Blob([typeof response.data === 'string' ? response.data : JSON.stringify(response.data, null, 2)], { type: "application/json" });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `Decision_Report_${Date.now().toString().slice(-6)}.json`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            } else if (format === "markdown") {
                const blob = new Blob([response.data], { type: "text/markdown" });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `Decision_Report_${Date.now().toString().slice(-6)}.md`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            }
            setToastMsg(`Exported report as ${format.toUpperCase()}`);
            setTimeout(() => setToastMsg(""), 3000);
        } catch (err) {
            console.error("EXPORT ERROR:", err);
            alert("Failed to export report document.");
        } finally {
            setExporting(false);
        }
    };

    if (loading) return null;

    if (error && !report) {
        return (
            <section className="report-container">
                <div className="error-card">
                    <div className="error-icon">⚠️</div>
                    <h3>Analysis Could Not Be Completed</h3>
                    <p>{safeString(error, "An unexpected error occurred.")}</p>
                    <span className="error-hint">System is protected by automatic DEMO/CACHE mode. Click below to retry.</span>
                    {onRetry && (
                        <button className="btn-retry-action" onClick={onRetry} style={{ marginTop: "16px" }}>
                            🔄 Retry Request
                        </button>
                    )}
                </div>
            </section>
        );
    }

    if (!report) {
        return (
            <section className="report-container empty-state-card">
                <div className="empty-badge">ENTERPRISE DECISION WORKSPACE</div>
                <h2>Awaiting Business Query</h2>
                <p>
                    Submit a strategic business problem above to initiate autonomous multi-agent analysis,
                    risk modeling, financial tool calculations, and decision intelligence.
                </p>
                <div className="empty-features-grid">
                    <div className="feature-item">
                        <span>🔍</span>
                        <strong>Research Agent</strong>
                        <p>Evaluates market demand and competitor positioning</p>
                    </div>
                    <div className="feature-item">
                        <span>📊</span>
                        <strong>Quantitative Tools</strong>
                        <p>Calculates profit, ROI, break-even & market risk</p>
                    </div>
                    <div className="feature-item">
                        <span>🚀</span>
                        <strong>Planning Agent</strong>
                        <p>Formulates phased strategic execution roadmap</p>
                    </div>
                    <div className="feature-item">
                        <span>⚖️</span>
                        <strong>Decision Agent</strong>
                        <p>Delivers Viability Score & actionable recommendation</p>
                    </div>
                </div>
            </section>
        );
    }

    const decisionText = safeString(report.decision);
    const viabilityScore = dynamicViability || report.viability_score || 78;
    const confidenceScore = report.confidence || 82;

    const riskLevelStr = safeString(
        dynamicRisk || report.risk_level || report.tool_analysis?.risk_level,
        "Medium"
    );
    const normalizedRisk = riskLevelStr.toLowerCase();
    const riskBadgeClass =
        normalizedRisk === "low"
            ? "risk-badge-low"
            : normalizedRisk === "high"
            ? "risk-badge-high"
            : "risk-badge-medium";

    const isAnyFollowupLoading = followupMessages.some((msg) => msg.loading);

    const handleSendFollowup = (textToSend) => {
        const queryText = textToSend || localFollowupText;
        if (!queryText.trim() || isAnyFollowupLoading) return;
        onFollowup(queryText.trim());
        setLocalFollowupText("");
    };

    return (
        <section className="report-container">
            {/* QUOTA WARNING NOTICE BANNER */}
            {quotaNotice && (
                <div className="quota-notice-banner">
                    <span className="banner-icon">⚡</span>
                    <span>AI quota temporarily unavailable. Cached analysis or demo mode is being used.</span>
                </div>
            )}

            {/* EXECUTIVE REPORT CARD */}
            <div className="executive-report-card">
                {/* METADATA HEADER */}
                <div className="report-meta-header">
                    <div className="report-meta-left">
                        <span className="meta-eyebrow">AI DECISION INTELLIGENCE</span>
                        <h2 className="report-meta-title">Executive Strategic Assessment</h2>
                    </div>

                    <div className="report-meta-right">
                        <div className="export-dropdown-wrapper">
                            <button
                                className="btn-export-trigger"
                                onClick={() => setShowExportMenu(!showExportMenu)}
                                disabled={exporting}
                            >
                                <span>📥 Export Report</span>
                                <span className="dropdown-caret">▼</span>
                            </button>

                            {showExportMenu && (
                                <div className="export-menu-dropdown">
                                    <button onClick={() => handleExport("pdf")}>📄 Download PDF Report</button>
                                    <button onClick={() => handleExport("json")}>📊 Download JSON Data</button>
                                    <button onClick={() => handleExport("markdown")}>📝 Download Markdown</button>
                                    <button onClick={() => handleExport("copy")}>📋 Copy Report Text</button>
                                    <button onClick={() => handleExport("print")}>🖨️ Print Document</button>
                                </div>
                            )}
                        </div>

                        {toastMsg && (
                            <div className="toast-notification-inline">
                                <span>{toastMsg}</span>
                            </div>
                        )}

                        <span className="status-pill green">
                            <span className="pill-dot"></span>
                            Analysis Complete
                        </span>
                    </div>
                </div>

                {/* DECISION INTELLIGENCE SCORECARDS */}
                <div className="intelligence-scorecard-grid">
                    <div className="scorecard-item">
                        <span className="scorecard-label">BUSINESS VIABILITY</span>
                        <div className="scorecard-value-group">
                            <span className="scorecard-number">{viabilityScore}</span>
                            <span className="scorecard-max">/ 100</span>
                        </div>
                        <div className="scorecard-bar-track">
                            <div className="scorecard-bar-fill blue" style={{ width: `${viabilityScore}%` }}></div>
                        </div>
                    </div>

                    <div className="scorecard-item">
                        <span className="scorecard-label">AI CONFIDENCE</span>
                        <div className="scorecard-value-group">
                            <span className="scorecard-number green">{confidenceScore}%</span>
                        </div>
                        <div className="scorecard-bar-track">
                            <div className="scorecard-bar-fill green" style={{ width: `${confidenceScore}%` }}></div>
                        </div>
                    </div>

                    <div className="scorecard-item">
                        <span className="scorecard-label">MARKET RISK LEVEL</span>
                        <div className="scorecard-value-group">
                            <span className={`risk-pill-badge ${riskBadgeClass}`}>
                                {riskLevelStr.toUpperCase()} RISK
                            </span>
                        </div>
                        <small className="scorecard-subtext">Quantified by Multi-Agent Engine</small>
                    </div>
                </div>

                {/* EXECUTIVE SUMMARY BLOCK */}
                <div className="report-section-block">
                    <div className="section-header-title">
                        <span className="section-num">01</span>
                        <div>
                            <small className="section-tag">EXECUTIVE RECOMMENDATION</small>
                            <h3 className="section-heading">Strategic Summary</h3>
                        </div>
                    </div>
                    <div className="summary-card-body">
                        <p className="summary-text">{decisionText}</p>
                    </div>
                </div>

                {/* WHY THIS DECISION DRIVERS */}
                {Array.isArray(report.why_this_decision) && report.why_this_decision.length > 0 && (
                    <div className="report-section-block">
                        <h4 className="drivers-title">Why This Decision?</h4>
                        <div className="drivers-grid">
                            {report.why_this_decision.map((driver, idx) => (
                                <div key={idx} className="driver-chip-item">
                                    <span className="driver-icon">✓</span>
                                    <span className="driver-text">{safeString(driver)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* RISKS & OPPORTUNITIES GRID */}
                {((Array.isArray(report.key_risks) && report.key_risks.length > 0) ||
                    (Array.isArray(report.key_opportunities) && report.key_opportunities.length > 0)) && (
                    <div className="risks-opportunities-grid">
                        {Array.isArray(report.key_risks) && report.key_risks.length > 0 && (
                            <div className="risk-box-card">
                                <h4 className="box-heading risk">⚠️ Key Risks</h4>
                                <ul>
                                    {report.key_risks.map((riskItem, idx) => (
                                        <li key={idx}>{safeString(riskItem)}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {Array.isArray(report.key_opportunities) && report.key_opportunities.length > 0 && (
                            <div className="opportunity-box-card">
                                <h4 className="box-heading opportunity">✦ Key Opportunities</h4>
                                <ul>
                                    {report.key_opportunities.map((oppItem, idx) => (
                                        <li key={idx}>{safeString(oppItem)}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}

                {/* QUANTITATIVE TOOL ANALYSIS */}
                {report.tool_analysis && (
                    <div className="report-section-block">
                        <div className="section-header-title">
                            <span className="section-num">02</span>
                            <div>
                                <small className="section-tag">QUANTITATIVE MODELING</small>
                                <h3 className="section-heading">Business Tool Analysis</h3>
                            </div>
                        </div>

                        <div className="tool-metric-cards-grid">
                            <div className="tool-metric-card">
                                <small>EXECUTED TOOL</small>
                                <h4>{safeString(report.tool_analysis.tool_name || report.tool_analysis.tool, "Market Risk Tool")}</h4>
                            </div>
                            <div className="tool-metric-card">
                                <small>TOOL RATING</small>
                                <h4 className={riskBadgeClass}>{safeString(report.tool_analysis.risk_level, riskLevelStr)}</h4>
                            </div>
                        </div>

                        {Array.isArray(report.tool_analysis.observations) &&
                            report.tool_analysis.observations.length > 0 && (
                                <div className="observations-list-box">
                                    <h5 className="obs-title">Observations</h5>
                                    {report.tool_analysis.observations.map((obs, idx) => (
                                        <p key={idx} className="obs-item">
                                            <span>•</span> {safeString(obs)}
                                        </p>
                                    ))}
                                </div>
                            )}
                    </div>
                )}

                {/* SENSITIVITY WHAT-IF ANALYSIS ENGINE */}
                <WhatIfPanel
                    task={task}
                    onUpdateMetrics={({ viability_score, risk_level }) => {
                        if (viability_score) setDynamicViability(viability_score);
                        if (risk_level) setDynamicRisk(risk_level);
                    }}
                />
            </div>

            {/* DYNAMIC UNLIMITED FOLLOW-UP CONVERSATION */}
            <div className="followup-panel">
                <div className="followup-panel-header">
                    <div>
                        <span className="panel-eyebrow">CONTINUE THE ANALYSIS</span>
                        <h3 className="panel-title">Ask the Decision Engine</h3>
                        <p className="panel-subtitle">
                            Ask any strategic, financial, marketing, operational, or pricing follow-up question.
                        </p>
                    </div>
                    {followupMessages.length > 0 && onClearFollowup && (
                        <button
                            type="button"
                            className="btn-clear-discussion"
                            onClick={onClearFollowup}
                        >
                            🗑️ Clear Thread
                        </button>
                    )}
                </div>

                <div className="suggested-chips-container">
                    <span className="chips-hint">Suggested questions:</span>
                    <div className="chips-flex">
                        {suggestedChips.map((chipText, idx) => (
                            <button
                                key={idx}
                                type="button"
                                className="suggestion-chip-btn"
                                onClick={() => setLocalFollowupText(chipText)}
                                disabled={isAnyFollowupLoading}
                            >
                                {chipText}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="followup-input-card">
                    <textarea
                        value={localFollowupText}
                        onChange={(e) => setLocalFollowupText(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                                e.preventDefault();
                                handleSendFollowup();
                            }
                        }}
                        placeholder="Ask any follow-up question about this decision..."
                        rows={3}
                        disabled={isAnyFollowupLoading}
                    />

                    <div className="input-card-footer">
                        <span className="footer-keyboard-tip">Press Ctrl + Enter to submit</span>

                        <button
                            type="button"
                            className="btn-followup-submit"
                            onClick={() => handleSendFollowup()}
                            disabled={isAnyFollowupLoading || !localFollowupText.trim()}
                        >
                            {isAnyFollowupLoading ? (
                                <span>Analyzing...</span>
                            ) : (
                                <span>Ask Decision Engine →</span>
                            )}
                        </button>
                    </div>
                </div>

                {followupMessages.length > 0 && (
                    <div className="conversation-thread-list">
                        <h4 className="thread-section-title">Follow-up Conversation History</h4>

                        {followupMessages.map((msg) => (
                            <div className="conversation-item-block" key={msg.id}>
                                <div className="user-question-bubble">
                                    <span className="bubble-role">YOUR QUESTION</span>
                                    <p>{msg.question}</p>
                                </div>

                                <div className="ai-response-bubble">
                                    <span className="bubble-role ai">AI DECISION ENGINE ✦</span>

                                    {msg.loading && (
                                        <div className="ai-inline-loading">
                                            <span className="spinner-dot"></span>
                                            <span>Analyzing with decision context...</span>
                                        </div>
                                    )}

                                    {msg.error && (
                                        <div className="ai-inline-error">
                                            <span>⚠️ {safeString(msg.error)}</span>
                                        </div>
                                    )}

                                    {msg.answer && !msg.loading && (
                                        <div className="ai-answer-content">
                                            <p>{safeString(msg.answer)}</p>
                                            <button
                                                className="btn-copy-inline"
                                                onClick={() => navigator.clipboard.writeText(safeString(msg.answer))}
                                            >
                                                📋 Copy
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={threadEndRef} />
                    </div>
                )}
            </div>
        </section>
    );
}

export default ReportViewer;