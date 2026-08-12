import { useState } from "react";
import API from "../services/api";

function WhatIfPanel({ task, onUpdateMetrics }) {
    const [isOpen, setIsOpen] = useState(false);
    const [price, setPrice] = useState(500);
    const [monthlyOrders, setMonthlyOrders] = useState(150);
    const [marketingCost, setMarketingCost] = useState(10000);
    const [cac, setCac] = useState(45);
    const [fixedCost, setFixedCost] = useState(50000);
    const [variableCost, setVariableCost] = useState(300);

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    const handleRunAnalysis = async () => {
        setLoading(true);
        try {
            const res = await API.post("/what-if", {
                task: task || "Business Scenario",
                price: parseFloat(price),
                monthly_orders: parseFloat(monthlyOrders),
                marketing_cost: parseFloat(marketingCost),
                cac: parseFloat(cac),
                fixed_cost: parseFloat(fixedCost),
                variable_cost: parseFloat(variableCost)
            });

            if (res.data?.success) {
                setResult(res.data);
                if (onUpdateMetrics) {
                    onUpdateMetrics({
                        viability_score: res.data.updated_viability_score,
                        risk_level: res.data.updated_risk_level
                    });
                }
            }
        } catch (err) {
            console.error("What-If Analysis error:", err);
            alert("Failed to compute sensitivity analysis.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="what-if-panel-card">
            <div className="what-if-header" onClick={() => setIsOpen(!isOpen)}>
                <div className="header-left">
                    <span className="what-if-tag">SENSITIVITY & SCENARIO MODELING</span>
                    <h3 className="what-if-title">What-If Analysis Engine</h3>
                    <p className="what-if-sub">Test price, order volume, marketing, and CAC assumptions in real-time.</p>
                </div>
                <button className="btn-toggle-whatif">
                    {isOpen ? "Hide Controls ▲" : "Configure Parameters ▼"}
                </button>
            </div>

            {isOpen && (
                <div className="what-if-body">
                    <div className="controls-grid">
                        <div className="input-group-field">
                            <label>Product Selling Price (₹)</label>
                            <input
                                type="number"
                                value={price}
                                onChange={(e) => setPrice(e.target.value)}
                                min="10"
                                max="10000"
                            />
                        </div>

                        <div className="input-group-field">
                            <label>Expected Monthly Orders</label>
                            <input
                                type="number"
                                value={monthlyOrders}
                                onChange={(e) => setMonthlyOrders(e.target.value)}
                                min="1"
                                max="50000"
                            />
                        </div>

                        <div className="input-group-field">
                            <label>Monthly Marketing Budget (₹)</label>
                            <input
                                type="number"
                                value={marketingCost}
                                onChange={(e) => setMarketingCost(e.target.value)}
                                min="0"
                                max="100000"
                            />
                        </div>

                        <div className="input-group-field">
                            <label>Customer Acquisition Cost (₹)</label>
                            <input
                                type="number"
                                value={cac}
                                onChange={(e) => setCac(e.target.value)}
                                min="1"
                                max="500"
                            />
                        </div>

                        <div className="input-group-field">
                            <label>Fixed Monthly Cost (₹)</label>
                            <input
                                type="number"
                                value={fixedCost}
                                onChange={(e) => setFixedCost(e.target.value)}
                                min="0"
                                max="500000"
                            />
                        </div>

                        <div className="input-group-field">
                            <label>Variable Unit Cost (₹)</label>
                            <input
                                type="number"
                                value={variableCost}
                                onChange={(e) => setVariableCost(e.target.value)}
                                min="0"
                                max="5000"
                            />
                        </div>
                    </div>

                    <div className="what-if-actions">
                        <button
                            type="button"
                            className="btn-reanalyze"
                            onClick={handleRunAnalysis}
                            disabled={loading}
                        >
                            {loading ? "Re-evaluating Risk & Profit..." : "🔄 REANALYZE SCENARIO"}
                        </button>
                    </div>

                    {result && (
                        <div className="what-if-result-card">
                            <div className="result-metrics-grid">
                                <div className="metric-box">
                                    <small>UPDATED VIABILITY</small>
                                    <h4>{result.updated_viability_score} / 100</h4>
                                </div>
                                <div className="metric-box">
                                    <small>UPDATED RISK LEVEL</small>
                                    <h4 className={`risk-text-${result.updated_risk_level?.toLowerCase()}`}>
                                        {result.updated_risk_level?.toUpperCase()}
                                    </h4>
                                </div>
                                <div className="metric-box">
                                    <small>PROJECTED MONTHLY PROFIT</small>
                                    <h4 className={result.monthly_profit >= 0 ? "profit-positive" : "profit-negative"}>
                                        {result.monthly_profit < 0 ? `-₹${Math.abs(result.monthly_profit)?.toLocaleString('en-IN')}` : `₹${result.monthly_profit?.toLocaleString('en-IN')}`}
                                    </h4>
                                </div>
                                <div className="metric-box">
                                    <small>BREAK-EVEN UNITS</small>
                                    <h4>{result.break_even_units?.toLocaleString('en-IN')} units</h4>
                                </div>
                            </div>

                            <p className="result-explanation">{result.explanation}</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default WhatIfPanel;
