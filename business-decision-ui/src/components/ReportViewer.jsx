import { useState, useRef, useEffect } from "react";
import API from "../services/api";

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

function parseTextSections(rawText) {
    if (!rawText || typeof rawText !== "string") return {};

    const sections = {};
    const lines = rawText.split("\n");
    let currentHeader = "main";
    let currentContent = [];

    lines.forEach((line) => {
        const trimmed = line.trim();
        if (/^(RECOMMENDATION|EXECUTIVE SUMMARY|RESEARCH INSIGHTS|BUSINESS PLAN|EXECUTION PLAN|HISTORICAL INSIGHTS|CONDITIONS|REQUIREMENTS|CONCLUSION|FINAL ASSESSMENT)/i.test(trimmed)) {
            if (currentContent.length > 0) {
                sections[currentHeader] = currentContent.join("\n").trim();
            }
            currentHeader = trimmed.toUpperCase().replace(/[:#]/g, "").trim();
            currentContent = [];
        } else {
            currentContent.push(line);
        }
    });

    if (currentContent.length > 0) {
        sections[currentHeader] = currentContent.join("\n").trim();
    }

    return sections;
}

function ReportViewer({
    report,
    task,
    loading,
    error,
    followupMessages = [],
    onFollowup,
    onClearFollowup,
    onRetry
}) {
    const [localFollowupText, setLocalFollowupText] = useState("");
    const [showExportMenu, setShowExportMenu] = useState(false);
    const [exporting, setExporting] = useState(false);
    const [toastMsg, setToastMsg] = useState("");
    const threadEndRef = useRef(null);

    useEffect(() => {
        if (followupMessages.length > 0) {
            threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [followupMessages]);

    const suggestedChips = [
        "Why is the market risk medium?",
        "How can we reduce CAC?",
        "Would targeting students change the recommendation?",
        "What are the top 3 execution priorities?"
    ];

    // Export Handlers
    const handleExport = async (format) => {
        setShowExportMenu(false);

        if (format === "copy") {
            const decisionText = safeString(report?.decision);
            const riskText = safeString(report?.risk_level || report?.tool_analysis?.risk_level, "Medium");
            const copyContent = `AI EXECUTIVE DECISION REPORT\nQuery: ${task}\nRisk Level: ${riskText}\n\n${decisionText}`;
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
                    <span className="error-hint">Please check server connectivity or Gemini API quota limits.</span>
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
                <div className="empty-badge">ENTERPRISE DECISION SUPPORT</div>
                <h2>Awaiting Business Inquiry</h2>
                <p>
                    Submit a business idea above to initiate autonomous multi-agent analysis,
                    risk scoring, financial tool modeling, and executive report generation.
                </p>
                <div className="empty-features-grid">
                    <div className="feature-item">
                        <span>🔍</span>
                        <strong>Research Agent</strong>
                        <p>Evaluates market size and competitive pressure</p>
                    </div>
                    <div className="feature-item">
                        <span>📊</span>
                        <strong>Financial Tools</strong>
                        <p>Quantifies risk & break-even points</p>
                    </div>
                    <div className="feature-item">
                        <span>🚀</span>
                        <strong>Planning Agent</strong>
                        <p>Creates phased strategic roadmap</p>
                    </div>
                    <div className="feature-item">
                        <span>⚖️</span>
                        <strong>Decision Agent</strong>
                        <p>Delivers final actionable recommendation</p>
                    </div>
                </div>
            </section>
        );
    }

    const rawDecisionText = safeString(report.decision);
    const parsedSections = parseTextSections(rawDecisionText);

    const riskLevelStr = safeString(
        report.risk_level || report.tool_analysis?.risk_level,
        "Medium"
    );
    const normalizedRisk = riskLevelStr.toLowerCase();
    const riskBadgeClass =
        normalizedRisk === "low"
            ? "risk-badge-low"
            : normalizedRisk === "high"
            ? "risk-badge-high"
            : "risk-badge-medium";
    const riskIcon =
        normalizedRisk === "low"
            ? "🛡️ LOW RISK"
            : normalizedRisk === "high"
            ? "⚠️ HIGH RISK"
            : "⚡ MEDIUM RISK";

    let recommendationTitle = rawDecisionText.split("\n")[0] || "RECOMMENDATION GENERATED";
    if (recommendationTitle.length > 120) {
        recommendationTitle = recommendationTitle.substring(0, 117) + "...";
    }

    const isAnyFollowupLoading = followupMessages.some((msg) => msg.loading);

    const handleSendFollowup = (textToSend) => {
        const queryText = textToSend || localFollowupText;
        if (!queryText.trim() || isAnyFollowupLoading) return;
        onFollowup(queryText.trim());
        setLocalFollowupText("");
    };

    return (
        <section className="report-container">
            {/* EXECUTIVE REPORT WRAPPER */}
            <div className="executive-report-card">
                {/* REPORT METADATA HEADER WITH EXPORT CONTROLS */}
                <div className="report-meta-header">
                    <div className="report-meta-left">
                        <span className="meta-eyebrow">AI DECISION REPORT</span>
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

                {/* DECISION HERO BANNER */}
                <div className={`decision-hero-banner ${riskBadgeClass}`}>
                    <div className="hero-banner-content">
                        <span className="banner-eyebrow">EXECUTIVE RECOMMENDATION</span>
                        <h1 className="banner-headline">{recommendationTitle}</h1>
                        <p className="banner-subtext">
                            Synthesized from Research, Planning, and Quantitative Business Tools.
                        </p>
                    </div>

                    <div className="hero-risk-container">
                        <div className={`risk-badge-pill ${riskBadgeClass}`}>
                            <span className="risk-pill-icon">{riskIcon}</span>
                        </div>
                    </div>
                </div>

                {/* SECTION 01: EXECUTIVE SUMMARY */}
                <div className="report-section-block">
                    <div className="section-header-title">
                        <span className="section-num">01</span>
                        <div>
                            <small className="section-tag">OVERVIEW</small>
                            <h3 className="section-heading">Executive Summary</h3>
                        </div>
                    </div>
                    <div className="summary-card-body">
                        <p className="summary-text">
                            {parsedSections["EXECUTIVE SUMMARY"] || rawDecisionText}
                        </p>
                    </div>
                </div>

                {/* SECTION 02: BUSINESS TOOL ANALYSIS */}
                {report.tool_analysis && (
                    <div className="report-section-block">
                        <div className="section-header-title">
                            <span className="section-num">02</span>
                            <div>
                                <small className="section-tag">QUANTITATIVE INTELLIGENCE</small>
                                <h3 className="section-heading">Business Tool Analysis</h3>
                            </div>
                        </div>

                        <div className="tool-cards-grid">
                            <div className="tool-metric-card">
                                <span className="metric-card-label">ANALYSIS TOOL</span>
                                <h4 className="metric-card-val">
                                    {safeString(report.tool_analysis.tool_name, "Market Risk Tool")}
                                </h4>
                            </div>

                            <div className="tool-metric-card">
                                <span className="metric-card-label">RISK LEVEL</span>
                                <h4 className={`metric-card-val ${riskBadgeClass}`}>
                                    {safeString(report.tool_analysis.risk_level, riskLevelStr)}
                                </h4>
                            </div>
                        </div>

                        {Array.isArray(report.tool_analysis.observations) &&
                            report.tool_analysis.observations.length > 0 && (
                                <div className="tool-observations-box">
                                    <h4 className="observations-title">Key Observations</h4>
                                    <div className="observations-list">
                                        {report.tool_analysis.observations.map((obs, idx) => (
                                            <div className="observation-row" key={idx}>
                                                <span className="obs-check">✓</span>
                                                <span className="obs-text">{safeString(obs)}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                        {report.tool_analysis.recommendation && (
                            <div className="tool-rec-callout">
                                <span className="rec-callout-label">TOOL RECOMMENDATION</span>
                                <p className="rec-callout-text">
                                    {safeString(report.tool_analysis.recommendation)}
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* SECTION 03: RESEARCH INSIGHTS */}
                {Array.isArray(report.research_summary) && report.research_summary.length > 0 && (
                    <div className="report-section-block">
                        <div className="section-header-title">
                            <span className="section-num">03</span>
                            <div>
                                <small className="section-tag">MARKET RESEARCH</small>
                                <h3 className="section-heading">Market Insights</h3>
                            </div>
                        </div>

                        <div className="insights-cards-grid">
                            {report.research_summary.map((insight, idx) => (
                                <div className="insight-item-card" key={idx}>
                                    <div className="insight-card-top">
                                        <span className="insight-idx">
                                            {String(idx + 1).padStart(2, "0")}
                                        </span>
                                        <span className="insight-arrow-icon">↗</span>
                                    </div>
                                    <p className="insight-card-body">{safeString(insight)}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* SECTION 04: BUSINESS EXECUTION PLAN */}
                {Array.isArray(report.business_plan) && report.business_plan.length > 0 && (
                    <div className="report-section-block">
                        <div className="section-header-title">
                            <span className="section-num">04</span>
                            <div>
                                <small className="section-tag">STRATEGIC ROADMAP</small>
                                <h3 className="section-heading">Execution Plan</h3>
                            </div>
                        </div>

                        <div className="timeline-container">
                            {report.business_plan.map((phase, idx) => (
                                <div className="timeline-card-item" key={idx}>
                                    <div className="timeline-node">
                                        <span>{String(idx + 1).padStart(2, "0")}</span>
                                    </div>
                                    <div className="timeline-body-card">
                                        <span className="phase-pill">
                                            {safeString(phase.phase, `PHASE ${idx + 1}`)}
                                        </span>
                                        <h4 className="phase-headline">{safeString(phase.title)}</h4>
                                        <p className="phase-description">
                                            {safeString(phase.description)}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* SECTION 05: CONDITIONS & FINAL CONCLUSION */}
                {parsedSections["CONCLUSION"] || parsedSections["FINAL ASSESSMENT"] ? (
                    <div className="report-conclusion-card">
                        <span className="conclusion-tag">FINAL ASSESSMENT</span>
                        <h3 className="conclusion-title">What should happen next?</h3>
                        <p className="conclusion-text">
                            {parsedSections["CONCLUSION"] || parsedSections["FINAL ASSESSMENT"]}
                        </p>
                    </div>
                ) : null}
            </div>

            {/* =========================================================
                FOLLOW-UP CONVERSATION PANEL ("ASK THE DECISION ENGINE")
            ========================================================= */}
            <div className="followup-panel">
                <div className="followup-panel-header">
                    <div>
                        <span className="panel-eyebrow">CONTINUE THE ANALYSIS</span>
                        <h3 className="panel-title">Ask the Decision Engine</h3>
                        <p className="panel-subtitle">
                            Explore any part of the recommendation, risk, market, pricing, customers, strategy, or next steps.
                        </p>
                    </div>
                    <div className="panel-header-right" style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        {followupMessages.length > 0 && onClearFollowup && (
                            <button
                                type="button"
                                className="btn-clear-discussion"
                                onClick={onClearFollowup}
                                title="Clear follow-up conversation history"
                            >
                                🗑️ Clear History
                            </button>
                        )}
                        <div className="panel-header-icon">💬</div>
                    </div>
                </div>

                <div className="suggested-chips-container">
                    <span className="chips-hint">Suggested follow-ups:</span>
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
                        placeholder="Ask your own question about this decision..."
                        rows={3}
                        disabled={isAnyFollowupLoading}
                    />

                    <div className="input-card-footer">
                        <span className="footer-keyboard-tip">
                            Press Ctrl + Enter to send
                        </span>

                        <button
                            type="button"
                            className="btn-followup-submit"
                            onClick={() => handleSendFollowup()}
                            disabled={isAnyFollowupLoading || !localFollowupText.trim()}
                        >
                            {isAnyFollowupLoading ? (
                                <span className="btn-loading-inline">
                                    <span className="mini-spinner"></span>
                                    <span>Analyzing...</span>
                                </span>
                            ) : (
                                <span>Ask Decision Engine →</span>
                            )}
                        </button>
                    </div>
                </div>

                {followupMessages.length > 0 && (
                    <div className="conversation-thread-list">
                        <h4 className="thread-section-title">Follow-up Discussion</h4>

                        {followupMessages.map((msg) => (
                            <div className="conversation-item-block" key={msg.id}>
                                <div className="user-question-bubble">
                                    <div className="bubble-header">
                                        <span className="bubble-role">YOUR QUESTION</span>
                                    </div>
                                    <p className="bubble-text">{msg.question}</p>
                                </div>

                                <div className="ai-response-bubble">
                                    <div className="bubble-header">
                                        <span className="bubble-role ai">AI DECISION ENGINE</span>
                                        <span className="ai-sparkle">✦</span>
                                    </div>

                                    {msg.loading && (
                                        <div className="ai-inline-loading">
                                            <span className="pulse-mini-dot"></span>
                                            <span>Analyzing your question with decision context...</span>
                                        </div>
                                    )}

                                    {msg.error && (
                                        <div className="ai-inline-error">
                                            <span className="error-badge-icon">⚠️</span>
                                            <p>{safeString(msg.error)}</p>
                                        </div>
                                    )}

                                    {msg.answer && !msg.loading && (
                                        <div className="ai-answer-content">
                                            <p className="answer-paragraph">{safeString(msg.answer)}</p>
                                            <button
                                                className="btn-copy-inline"
                                                onClick={() => navigator.clipboard.writeText(safeString(msg.answer))}
                                                title="Copy answer to clipboard"
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