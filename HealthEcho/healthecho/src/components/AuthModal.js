import { useState } from "react";
import { signInWithGoogle } from "../firebase";

export default function AuthModal({ onClose, onLogin }) {
  const [mode, setMode] = useState("login");
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    name: ""
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleEmailSubmit(e) {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await new Promise(resolve => setTimeout(resolve, 1000));

      if (!formData.email || !formData.password) {
        throw new Error("Please fill in all fields");
      }

      if (mode === "signup" && !formData.name) {
        throw new Error("Please enter your name");
      }

      // Mock successful email login (replace with Firebase email auth if needed)
      const userData = {
        uid: Date.now().toString(),
        name: formData.name || formData.email.split("@")[0],
        email: formData.email,
        photoURL: null
      };

      onLogin(userData);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleGoogleSignIn() {
    setError("");
    setIsLoading(true);

    try {
      const result = await signInWithGoogle();
      
      if (result.success) {
        onLogin(result.user);
        onClose();
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError("Failed to sign in with Google");
    } finally {
      setIsLoading(false);
    }
  }

  function handleChange(e) {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-header">
          <h2>{mode === "login" ? "Welcome Back" : "Join HealthEcho"}</h2>
          <p>
            {mode === "login" 
              ? "Sign in to access your medical history" 
              : "Create an account to save your conversations"}
          </p>
        </div>

        {error && <div className="auth-error">{error}</div>}

        {/* Google Sign-In Button */}
        <button 
          className="google-auth-btn"
          onClick={handleGoogleSignIn}
          disabled={isLoading}
        >
          <img 
            src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" 
            alt="Google"
            className="google-icon"
          />
          <span>Continue with Google</span>
        </button>

        <div className="auth-divider">
          <span>or</span>
        </div>

        {/* Email/Password Form */}
        <form onSubmit={handleEmailSubmit}>
          {mode === "signup" && (
            <div className="form-group">
              <label>Full Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="John Doe"
                disabled={isLoading}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label>Email Address</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="you@example.com"
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="••••••••"
              disabled={isLoading}
              required
            />
          </div>

          <button 
            type="submit" 
            className="auth-btn"
            disabled={isLoading}
          >
            {isLoading ? "Please wait..." : mode === "login" ? "Sign In with Email" : "Create Account"}
          </button>
        </form>

        <div className="auth-footer">
          {mode === "login" ? (
            <p>
              Don't have an account?{" "}
              <span onClick={() => setMode("signup")} className="auth-link">
                Sign up
              </span>
            </p>
          ) : (
            <p>
              Already have an account?{" "}
              <span onClick={() => setMode("login")} className="auth-link">
                Sign in
              </span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}