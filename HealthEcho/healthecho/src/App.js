import { useState, useEffect } from "react";
import MedicalLanding from "./components/MedicalLanding";
import MedicalChat from "./components/MedicalChat";
import { onAuthStateChange, logout } from "./firebase";
import "./index.css";

function App() {
  const [currentScreen, setCurrentScreen] = useState("landing");
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for saved session in localStorage first
    const savedUser = localStorage.getItem("healthecho_user");
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }

    // Listen for Firebase auth state changes
    const unsubscribe = onAuthStateChange((firebaseUser) => {
      if (firebaseUser) {
        setUser(firebaseUser);
        localStorage.setItem("healthecho_user", JSON.stringify(firebaseUser));
      } else {
        setUser(null);
        localStorage.removeItem("healthecho_user");
      }
      setIsLoading(false);
    });

    // Cleanup subscription
    return () => unsubscribe();
  }, []);

  const handleStartChat = () => setCurrentScreen("chat");
  const handleBackToLanding = () => setCurrentScreen("landing");

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem("healthecho_user", JSON.stringify(userData));
  };

  const handleLogout = async () => {
    await logout();
    // State will be updated by onAuthStateChange
  };

  if (isLoading) {
    return (
      <div style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#020617",
        color: "white"
      }}>
        <div className="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    );
  }

  return (
    <>
      {currentScreen === "landing" && (
        <MedicalLanding 
          onStartChat={handleStartChat}
          onLogin={handleLogin}
          user={user}
          onLogout={handleLogout}
        />
      )}
      {currentScreen === "chat" && (
        <MedicalChat 
          onBack={handleBackToLanding} 
          user={user}
          onLogout={handleLogout}
        />
      )}
    </>
  );
}

export default App;