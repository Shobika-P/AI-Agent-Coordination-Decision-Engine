function ReportViewer({ report, loading }) {

  if (loading) {
    return (
      <section className="report-section">

        <div className="report-card loading-card">

          <div className="loading-spinner"></div>

          <h2>Analyzing Your Business Idea</h2>

          <p>
            AI is evaluating your business opportunity,
            risks, research, and strategic factors.
          </p>

        </div>

      </section>
    );
  }

  if (!report) {
    return null;
  }

  // Detect the actual risk level from the report
  const riskMatch = report.match(
    /Risk Level:\s*(Low|Medium|High)/i
  );

  const riskLevel = riskMatch
    ? riskMatch[1].toLowerCase()
    : null;

  return (
    <section className="report-section">

      <div className="report-card">

        <div className="report-header">

          <h2>
            Business Decision Report
          </h2>

          <span className="report-status">
            AI ANALYSIS COMPLETE
          </span>

        </div>

        {/* RISK BADGE */}

        <div className="risk-container">

          {riskLevel === "medium" && (
            <span className="risk-badge risk-medium">
              🟡 Medium Risk
            </span>
          )}

          {riskLevel === "high" && (
            <span className="risk-badge risk-high">
              🔴 High Risk
            </span>
          )}

          {riskLevel === "low" && (
            <span className="risk-badge risk-low">
              🟢 Low Risk
            </span>
          )}

        </div>

        {/* REPORT */}

        <div className="report-content">
          {report}
        </div>

      </div>

    </section>
  );
}

export default ReportViewer;