import { useState } from "react";
import { authService } from "../services/api";

function AuthScreen({ onAuthSuccess }) {
    const [mode, setMode] = useState("login"); // 'login' | 'register'
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        const cleanEmail = email.trim();
        if (!cleanEmail) {
            setError("Please enter your email address.");
            return;
        }

        if (!password) {
            setError("Please enter your password.");
            return;
        }

        if (mode === "register" && password.length < 6) {
            setError("Password must be at least 6 characters long.");
            return;
        }

        setLoading(true);
        try {
            const response =
                mode === "register"
                    ? await authService.register(cleanEmail, password)
                    : await authService.login(cleanEmail, password);

            if (response.data?.success && response.data?.token) {
                authService.setToken(response.data.token);
                onAuthSuccess(response.data.user, response.data.token);
            } else {
                setError(response.data?.error || "Authentication failed.");
            }
        } catch (err) {
            const errMsg =
                err.response?.data?.error ||
                (mode === "register"
                    ? "Failed to create account. Please check your details."
                    : "Invalid email or password.");
            setError(errMsg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-screen-wrapper">
            <div className="auth-card-container">
                <div className="auth-brand-header">
                    <div className="auth-brand-icon">⚡</div>
                    <h1 className="auth-brand-title">DECISION ENGINE</h1>
                    <p className="auth-brand-subtitle">
                        Enterprise Workflow Platform & Decision Automation System
                    </p>
                </div>

                <div className="auth-tabs">
                    <button
                        type="button"
                        className={`auth-tab-btn ${mode === "login" ? "active" : ""}`}
                        onClick={() => {
                            setMode("login");
                            setError(null);
                        }}
                    >
                        Sign In
                    </button>
                    <button
                        type="button"
                        className={`auth-tab-btn ${mode === "register" ? "active" : ""}`}
                        onClick={() => {
                            setMode("register");
                            setError(null);
                        }}
                    >
                        Register
                    </button>
                </div>

                {error && (
                    <div className="auth-error-banner" role="alert">
                        <span className="auth-error-icon">⚠️</span>
                        <span>{error}</span>
                    </div>
                )}

                <form className="auth-form" onSubmit={handleSubmit}>
                    <div className="auth-field-group">
                        <label htmlFor="auth-email" className="auth-label">
                            Email Address
                        </label>
                        <input
                            id="auth-email"
                            type="email"
                            className="auth-input"
                            placeholder="name@company.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            autoComplete="email"
                            required
                            disabled={loading}
                        />
                    </div>

                    <div className="auth-field-group">
                        <label htmlFor="auth-password" className="auth-label">
                            Password
                        </label>
                        <input
                            id="auth-password"
                            type="password"
                            className="auth-input"
                            placeholder={mode === "register" ? "At least 6 characters" : "••••••••"}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            autoComplete={mode === "register" ? "new-password" : "current-password"}
                            required
                            disabled={loading}
                        />
                    </div>

                    <button
                        type="submit"
                        className="auth-submit-btn"
                        disabled={loading}
                    >
                        {loading ? (
                            <span className="auth-btn-loading">
                                <span className="mini-spinner"></span>
                                {mode === "register" ? "Creating account..." : "Signing in..."}
                            </span>
                        ) : mode === "register" ? (
                            "Create Account"
                        ) : (
                            "Sign In"
                        )}
                    </button>
                </form>

                <div className="auth-footer-toggle">
                    {mode === "login" ? (
                        <p>
                            Don't have an account?{" "}
                            <button
                                type="button"
                                className="auth-link-btn"
                                onClick={() => {
                                    setMode("register");
                                    setError(null);
                                }}
                            >
                                Register
                            </button>
                        </p>
                    ) : (
                        <p>
                            Already have an account?{" "}
                            <button
                                type="button"
                                className="auth-link-btn"
                                onClick={() => {
                                    setMode("login");
                                    setError(null);
                                }}
                            >
                                Sign In
                            </button>
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}

export default AuthScreen;
