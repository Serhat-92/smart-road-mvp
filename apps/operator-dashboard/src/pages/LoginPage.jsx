import { useState } from "react";
import { apiConfig } from "../api/operatorApi";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const url = new URL("/auth/token", apiConfig.apiBaseUrl);
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);

      const response = await fetch(url.toString(), {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: params.toString(),
      });

      if (!response.ok) {
        throw new Error("Invalid username or password");
      }

      const data = await response.json();
      window.localStorage.setItem("auth_token", data.access_token);
      window.location.href = "/";
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box panel">
        <h2>Operator Login</h2>
        <p className="muted-copy">Sign in to access the Road Sentinel dashboard.</p>
        
        {error && <div className="status-pill status-critical" style={{marginBottom: "1rem", display: "block"}}>{error}</div>}
        
        <form onSubmit={handleLogin}>
          <div className="form-group" style={{ marginBottom: "1rem" }}>
            <label htmlFor="username" style={{ display: "block", marginBottom: "0.5rem" }}>Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #3f3f46", background: "#18181b", color: "#e4e4e7" }}
            />
          </div>
          <div className="form-group" style={{ marginBottom: "1.5rem" }}>
            <label htmlFor="password" style={{ display: "block", marginBottom: "0.5rem" }}>Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{ width: "100%", padding: "0.5rem", borderRadius: "4px", border: "1px solid #3f3f46", background: "#18181b", color: "#e4e4e7" }}
            />
          </div>
          <button 
            type="submit" 
            disabled={isLoading}
            style={{ 
              width: "100%", 
              padding: "0.75rem", 
              background: "#3b82f6", 
              color: "white", 
              border: "none", 
              borderRadius: "4px", 
              cursor: isLoading ? "not-allowed" : "pointer",
              fontWeight: "bold"
            }}
          >
            {isLoading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
