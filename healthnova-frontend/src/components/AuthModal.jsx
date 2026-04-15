import { useEffect, useMemo, useState } from "react";
import { ArrowRight, KeyRound, Mail, ShieldCheck, Sparkles } from "lucide-react";
import { requestEmailOtp, resetEmailPassword, verifyEmailOtp } from "../services/api";
import {
  authCapabilities,
  checkEmailRegistration,
  logoutUser,
  signInWithEmailPassword,
  signInWithGoogle,
  signUpWithEmailPassword,
} from "../services/firebase";

function AuthModal({ mode = "login", onClose, onAuthenticated }) {
  const [activeMode, setActiveMode] = useState(mode);
  const [fullName, setFullName] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);
  const [resetEmailSent, setResetEmailSent] = useState(false);
  const [resetOtpVerified, setResetOtpVerified] = useState(false);
  const [resetToken, setResetToken] = useState("");

  useEffect(() => {
    resetToMode(mode);
  }, [mode]);

  const introCopy = useMemo(() => {
    if (activeMode === "signup") {
      return {
        title: "Create your account",
        body: "Use your email to verify your account and finish your HealthNova setup.",
      };
    }
    if (activeMode === "forgot") {
      return {
        title: "Reset your password",
        body: "We'll verify your email with an OTP, then let you set your new password right here.",
      };
    }
    return {
      title: "Welcome back",
      body: "Login with your email and password, or continue with Google.",
    };
  }, [activeMode]);

  function resetToMode(nextMode, keepIdentifier = false) {
    setActiveMode(nextMode);
    setFullName("");
    setIdentifier(keepIdentifier ? identifier : "");
    setPassword("");
    setConfirmPassword("");
    setOtp("");
    setStatus("");
    setError("");
    setOtpSent(false);
    setOtpVerified(false);
    setResetEmailSent(false);
    setResetOtpVerified(false);
    setResetToken("");
  }

  function showSuccessMessage(message) {
    setStatus(message);
    setError("");
  }

  function showErrorMessage(message) {
    setError(message);
    setStatus("");
  }

  function getIdentifierDetails(rawValue = identifier) {
    const value = `${rawValue || ""}`.trim();
    const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    return {
      value,
      type: isEmail ? "email" : "invalid",
      isEmail,
      isPhone: false,
    };
  }

  function authFeedback() {
    if (error) return <div className="auth-alert auth-alert--error">{error}</div>;
    if (status) return <div className="auth-alert auth-alert--success">{status}</div>;
    return null;
  }

  async function handleLogin(event) {
    event.preventDefault();
    const identity = getIdentifierDetails();
    if (!identity.value) return showErrorMessage("Please enter your email address.");
    if (identity.type === "invalid") return showErrorMessage("Enter a valid email address.");
    if (!password) return showErrorMessage("Please enter your password.");

    setLoading(true);
    setError("");
    setStatus("");
    try {
      const result = await signInWithEmailPassword(identity.value, password);
      showSuccessMessage("Login successful! Redirecting...");
      window.setTimeout(() => onAuthenticated({ user: result?.user }), 600);
    } catch (authError) {
      try {
        const registration = await checkEmailRegistration(identity.value);
        if (registration.hasGoogle && !registration.hasPassword) {
          showErrorMessage("This email is linked to Google sign-in. Use Continue with Google.");
        } else if (!registration.exists) {
          showErrorMessage("No password account exists for this email yet. Please sign up first.");
        } else {
          showErrorMessage(authError.message || "The email or password is incorrect.");
        }
      } catch {
        showErrorMessage(authError.message || "The email or password is incorrect.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSendSignupOtp(event) {
    event.preventDefault();
    if (!fullName.trim()) return showErrorMessage("Please enter your full name.");
    const identity = getIdentifierDetails();
    if (!identity.value) return showErrorMessage("Please enter your email address.");
    if (identity.type === "invalid") return showErrorMessage("Enter a valid email address.");

    setLoading(true);
    setError("");
    setStatus("");
    try {
      const registration = await checkEmailRegistration(identity.value);
      if (registration.hasGoogle) {
        showErrorMessage("This email is already registered with Google. Please use Google Sign-In.");
        return;
      }
      if (registration.exists && registration.hasPassword) {
        showErrorMessage("This email already has an account. Please login instead.");
        return;
      }
      await requestEmailOtp({ email: identity.value, name: fullName.trim() });
      showSuccessMessage(`OTP sent to ${identity.value}. Please check your inbox.`);
      setOtpSent(true);
    } catch (authError) {
      showErrorMessage(authError.message || "Failed to send OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifySignupOtp() {
    if (!otp.trim()) return showErrorMessage("Please enter the OTP code.");
    setLoading(true);
    setError("");
    setStatus("");
    try {
      const verification = await verifyEmailOtp({
        email: identifier.trim(),
        otp: otp.trim(),
        code: otp.trim(),
        name: fullName.trim(),
      });
      if (verification?.token && verification?.user) {
        onAuthenticated({ otpSession: verification, user: verification.user });
        return;
      }
      setOtpVerified(true);
      showSuccessMessage("Email verified successfully! Now set your password.");
    } catch (authError) {
      showErrorMessage(authError.message || "Invalid OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateAccount() {
    if (password.length < 6) return showErrorMessage("Password must be at least 6 characters long.");
    if (password !== confirmPassword) return showErrorMessage("Passwords do not match.");

    setLoading(true);
    setError("");
    setStatus("");
    try {
      await signUpWithEmailPassword(identifier.trim(), password, fullName.trim());
      await logoutUser();
      showSuccessMessage("Account created successfully! Please login with your credentials.");
      window.setTimeout(() => resetToMode("login", true), 1000);
    } catch (authError) {
      showErrorMessage(authError.message || "Account creation failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSendResetOtp(event) {
    event.preventDefault();
    const identity = getIdentifierDetails();
    if (!identity.value) return showErrorMessage("Please enter your email address.");
    if (identity.type !== "email") return showErrorMessage("Password reset is available only for email accounts.");

    setLoading(true);
    setError("");
    setStatus("");
    try {
      await requestEmailOtp({ email: identity.value, purpose: "password_reset" });
      setResetEmailSent(true);
      showSuccessMessage(`Password reset OTP sent to ${identity.value}. Please check your inbox.`);
    } catch (authError) {
      showErrorMessage(authError.message || "Failed to send reset OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyResetOtp() {
    if (!otp.trim()) return showErrorMessage("Please enter the OTP code.");
    setLoading(true);
    setError("");
    setStatus("");
    try {
      const verification = await verifyEmailOtp({
        email: identifier.trim(),
        otp: otp.trim(),
        code: otp.trim(),
        name: "",
        purpose: "password_reset",
      });
      if (!verification?.reset_token) {
        throw new Error("Reset session expired. Please request a fresh OTP and try again.");
      }
      setResetToken(verification.reset_token);
      setResetOtpVerified(true);
      showSuccessMessage("OTP verified. You can now set your new password.");
    } catch (authError) {
      showErrorMessage(authError.message || "Invalid OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword() {
    if (password.length < 6) return showErrorMessage("Password must be at least 6 characters long.");
    if (password !== confirmPassword) return showErrorMessage("Passwords do not match.");
    if (!resetToken) return showErrorMessage("Password reset session expired. Please verify OTP again.");

    setLoading(true);
    setError("");
    setStatus("");
    try {
      await resetEmailPassword({
        email: identifier.trim(),
        reset_token: resetToken,
        new_password: password,
      });
      showSuccessMessage("Password updated successfully. Please login with your new password.");
      window.setTimeout(() => resetToMode("login", true), 1000);
    } catch (authError) {
      showErrorMessage(authError.message || "Failed to update the password. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleLogin() {
    setLoading(true);
    setError("");
    setStatus("");
    try {
      const result = await signInWithGoogle();
      showSuccessMessage("Google login successful! Redirecting...");
      window.setTimeout(() => onAuthenticated({ user: result?.user }), 600);
    } catch (authError) {
      showErrorMessage(authError.message || "Google sign-in failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const renderLogin = () => (
    <>
      <button className="google-btn" onClick={handleGoogleLogin} disabled={loading} type="button">
        <ShieldCheck size={18} />
        <span>{loading ? "Please wait..." : "Continue with Google"}</span>
      </button>
      <div className="auth-divider">
        <span>or continue with email</span>
      </div>
      {!authCapabilities.googleSignIn ? (
        <div className="auth-alert auth-alert--success">
          Google sign-in button is visible again, but local mode still needs real Firebase setup to complete Google login.
        </div>
      ) : null}
      <form className="auth-form" onSubmit={handleLogin}>
        <label className="form-field">
          <span>Email address</span>
          <input type="email" value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="you@example.com" required disabled={loading} />
        </label>
        <label className="form-field">
          <span>Password</span>
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" required disabled={loading} />
        </label>
        <button className="primary-btn auth-submit" type="submit" disabled={loading}>
          <KeyRound size={16} />
          <span>{loading ? "Please wait..." : "Login now"}</span>
          <ArrowRight size={15} />
        </button>
        {authFeedback()}
      </form>
      <div className="auth-links">
        <button className="text-btn" onClick={() => resetToMode("forgot", true)} type="button" disabled={loading}>
          Forgot password?
        </button>
      </div>
      <p className="auth-switch">
        New to HealthNova?{" "}
        <button className="text-btn" onClick={() => resetToMode("signup")} type="button" disabled={loading}>
          Sign up
        </button>
      </p>
    </>
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(event) => event.stopPropagation()}>
        <button className="modal-close" onClick={onClose} type="button" aria-label="Close">
          x
        </button>
        <div className="auth-modal__layout">
          <section className="auth-modal__intro">
            <span className="eyebrow">Secure access</span>
            <h2>{introCopy.title}</h2>
            <p>{introCopy.body}</p>
            <div className="auth-feature-list auth-feature-list--single">
              <div className="auth-feature auth-feature--compact">
                <Sparkles size={16} />
                <span>Secure authentication with email verification and password protection.</span>
              </div>
            </div>
          </section>
          <section className="auth-modal__card">
            <div className="auth-mode-switch">
              <button className={`auth-mode-tab ${activeMode === "login" ? "active" : ""}`} onClick={() => resetToMode("login")} type="button" disabled={loading}>
                Login
              </button>
              <button className={`auth-mode-tab ${activeMode === "signup" ? "active" : ""}`} onClick={() => resetToMode("signup")} type="button" disabled={loading}>
                Sign up
              </button>
            </div>

            {activeMode === "login" && renderLogin()}

            {activeMode === "signup" && !otpSent ? (
              <form className="auth-form" onSubmit={handleSendSignupOtp}>
                <label className="form-field">
                  <span>Full name</span>
                  <input type="text" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Enter your full name" required disabled={loading} />
                </label>
                <label className="form-field">
                  <span>Email address</span>
                  <input type="email" value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="you@example.com" required disabled={loading} />
                </label>
                <button className="primary-btn auth-submit" type="submit" disabled={loading}>
                  <Mail size={16} />
                  <span>{loading ? "Sending OTP..." : "Send Verification OTP"}</span>
                  <ArrowRight size={15} />
                </button>
                {authFeedback()}
              </form>
            ) : null}

            {activeMode === "signup" && otpSent && !otpVerified ? (
              <div className="otp-panel">
                <div className="otp-panel__header">
                  <strong>Verify your email</strong>
                  <p>Enter the 6-digit code sent to <strong>{identifier}</strong></p>
                </div>
                <label className="form-field">
                  <span>Verification code</span>
                  <input type="text" value={otp} onChange={(event) => setOtp(event.target.value)} placeholder="Enter 6-digit OTP" disabled={loading} maxLength={6} />
                </label>
                <button className="primary-btn otp-btn" onClick={handleVerifySignupOtp} disabled={loading || !otp.trim()} type="button">
                  <ShieldCheck size={16} />
                  <span>{loading ? "Verifying..." : "Verify OTP"}</span>
                </button>
                <button className="text-btn" onClick={() => setOtpSent(false)} type="button" disabled={loading}>
                  {"<-"} Change email or resend OTP
                </button>
                {authFeedback()}
              </div>
            ) : null}

            {activeMode === "signup" && otpVerified ? (
              <div className="password-lock">
                <div className="password-lock__head">
                  <KeyRound size={16} />
                  <span>Set your password</span>
                </div>
                <label className="form-field">
                  <span>Password</span>
                  <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 6 characters" disabled={loading} />
                </label>
                <label className="form-field">
                  <span>Confirm password</span>
                  <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Re-enter your password" disabled={loading} />
                </label>
                <button className="primary-btn auth-submit" onClick={handleCreateAccount} disabled={loading} type="button">
                  <KeyRound size={16} />
                  <span>{loading ? "Creating account..." : "Create Account"}</span>
                  <ArrowRight size={15} />
                </button>
                {authFeedback()}
              </div>
            ) : null}

            {activeMode === "forgot" && !resetEmailSent ? (
              <form className="auth-form" onSubmit={handleSendResetOtp}>
                <label className="form-field">
                  <span>Email address</span>
                  <input type="email" value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="you@example.com" required disabled={loading} />
                </label>
                <button className="primary-btn auth-submit" type="submit" disabled={loading}>
                  <Mail size={16} />
                  <span>{loading ? "Sending OTP..." : "Send Reset OTP"}</span>
                  <ArrowRight size={15} />
                </button>
                <button className="text-btn" onClick={() => resetToMode("login", true)} type="button" disabled={loading}>
                  {"<-"} Back to login
                </button>
                {authFeedback()}
              </form>
            ) : null}

            {activeMode === "forgot" && resetEmailSent && !resetOtpVerified ? (
              <div className="otp-panel">
                <div className="otp-panel__header">
                  <strong>Verify your email</strong>
                  <p>Enter the 6-digit reset code sent to <strong>{identifier}</strong></p>
                </div>
                <label className="form-field">
                  <span>Verification code</span>
                  <input type="text" value={otp} onChange={(event) => setOtp(event.target.value)} placeholder="Enter 6-digit OTP" disabled={loading} maxLength={6} />
                </label>
                <button className="primary-btn otp-btn" onClick={handleVerifyResetOtp} disabled={loading || !otp.trim()} type="button">
                  <ShieldCheck size={16} />
                  <span>{loading ? "Verifying..." : "Verify OTP"}</span>
                </button>
                <button className="text-btn" onClick={() => setResetEmailSent(false)} type="button" disabled={loading}>
                  {"<-"} Resend OTP
                </button>
                {authFeedback()}
              </div>
            ) : null}

            {activeMode === "forgot" && resetOtpVerified ? (
              <div className="password-lock">
                <div className="password-lock__head">
                  <KeyRound size={16} />
                  <span>Set your new password</span>
                </div>
                <p className="auth-reset-note">
                  Your email has been verified for <strong>{identifier}</strong>. Choose a new password below.
                </p>
                <label className="form-field">
                  <span>New password</span>
                  <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 6 characters" disabled={loading} />
                </label>
                <label className="form-field">
                  <span>Confirm new password</span>
                  <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Re-enter your new password" disabled={loading} />
                </label>
                <button className="primary-btn auth-submit" onClick={handleResetPassword} disabled={loading} type="button">
                  <KeyRound size={16} />
                  <span>{loading ? "Updating password..." : "Save new password"}</span>
                  <ArrowRight size={15} />
                </button>
                <button className="text-btn" onClick={() => resetToMode("login", true)} disabled={loading} type="button">
                  <KeyRound size={16} />
                  <span>Back to login</span>
                </button>
                {authFeedback()}
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </div>
  );
}

export default AuthModal;
