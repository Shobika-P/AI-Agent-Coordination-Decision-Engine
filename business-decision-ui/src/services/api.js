import axios from "axios";

const API = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000",
    headers: {
        "Content-Type": "application/json"
    }
});

// Automatically attach Bearer auth token if present in localStorage
API.interceptors.request.use((config) => {
    const token = localStorage.getItem("auth_token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

// Helper authentication methods
export const authService = {
    getToken: () => localStorage.getItem("auth_token"),
    setToken: (token) => {
        if (token) {
            localStorage.setItem("auth_token", token);
        } else {
            localStorage.removeItem("auth_token");
        }
    },
    removeToken: () => localStorage.removeItem("auth_token"),
    register: (email, password) => API.post("/register", { email, password }),
    login: (email, password) => API.post("/login", { email, password }),
    logout: async () => {
        try {
            await API.post("/logout");
        } catch {
            // Ignore logout network errors
        } finally {
            localStorage.removeItem("auth_token");
        }
    },
    getMe: () => API.get("/auth/me")
};

export default API;