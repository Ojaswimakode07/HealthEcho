import { useState, useEffect } from "react";
import { api, summarizeText, getPatientData, getAppointments } from "./api";

export default function MedicalDashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [patients, setPatients] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState({
    totalPatients: 0,
    todayAppointments: 0,
    criticalCases: 0,
    pendingReports: 0
  });

  useEffect(() => {
    loadDashboardData();
  }, []);

  async function loadDashboardData() {
    try {
      const patientsData = await getPatientData();
      const appointmentsData = await getAppointments();
      
      setPatients(patientsData);
      setAppointments(appointmentsData);
      
      // Calculate stats
      setStats({
        totalPatients: patientsData.length,
        todayAppointments: appointmentsData.filter(a => 
          new Date(a.date).toDateString() === new Date().toDateString()
        ).length,
        criticalCases: patientsData.filter(p => p.status === "critical").length,
        pendingReports: patientsData.filter(p => p.reports?.some(r => !r.reviewed)).length
      });
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
    }
  }

  async function sendMedicalQuery() {
    if (!inputMessage.trim() || !selectedPatient) return;

    const userMsg = {
      role: "user",
      content: inputMessage,
      timestamp: new Date().toISOString(),
      sender: user?.name || "Doctor"
    };

    setChatMessages(prev => [...prev, userMsg]);
    setInputMessage("");
    setIsLoading(true);

    try {
      // Prepare context with patient data
      const patientContext = `
        Patient: ${selectedPatient.name}
        Age: ${selectedPatient.age}
        Condition: ${selectedPatient.condition}
        Medical History: ${selectedPatient.history || "Not available"}
        Current Medications: ${selectedPatient.medications?.join(", ") || "None"}
        Last Visit: ${selectedPatient.lastVisit || "Unknown"}
      `;

      const fullQuery = `Based on patient data:\n${patientContext}\n\nQuestion: ${inputMessage}`;
      const response = await summarizeText(fullQuery);

      const aiMsg = {
        role: "assistant",
        content: response.result,
        timestamp: new Date().toISOString(),
        sender: "Medical AI Assistant"
      };

      setChatMessages(prev => [...prev, aiMsg]);
    } catch (error) {
      console.error("Failed to get medical advice:", error);
      
      const errorMsg = {
        role: "assistant",
        content: "I apologize, but I'm having trouble processing your medical query. Please try again or consult with a specialist.",
        timestamp: new Date().toISOString(),
        sender: "Medical AI Assistant",
        isError: true
      };
      
      setChatMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }

  function formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: "2-digit", 
      minute: "2-digit" 
    });
  }

  return (
    <div className="medical-dashboard">
      {/* Sidebar */}
      <div className="medical-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">⚕️</div>
          <div>
            <h2>MediAssist Pro</h2>
            <p>Clinical Dashboard</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div 
            className={`nav-item ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            <span className="nav-icon">📊</span>
            <span>Dashboard</span>
          </div>
          <div 
            className={`nav-item ${activeTab === "patients" ? "active" : ""}`}
            onClick={() => setActiveTab("patients")}
          >
            <span className="nav-icon">👥</span>
            <span>Patients</span>
          </div>
          <div 
            className={`nav-item ${activeTab === "appointments" ? "active" : ""}`}
            onClick={() => setActiveTab("appointments")}
          >
            <span className="nav-icon">📅</span>
            <span>Appointments</span>
          </div>
          <div 
            className={`nav-item ${activeTab === "chat" ? "active" : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            <span className="nav-icon">💬</span>
            <span>Medical Chat</span>
          </div>
          <div 
            className={`nav-item ${activeTab === "reports" ? "active" : ""}`}
            onClick={() => setActiveTab("reports")}
          >
            <span className="nav-icon">📋</span>
            <span>Reports</span>
          </div>
          <div 
            className={`nav-item ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => setActiveTab("settings")}
          >
            <span className="nav-icon">⚙️</span>
            <span>Settings</span>
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="doctor-profile">
            <div className="doctor-avatar">
              {user?.name?.[0] || "D"}
            </div>
            <div className="doctor-info">
              <h4>Dr. {user?.name || "User"}</h4>
              <p>General Physician</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="medical-main">
        {/* Top Bar */}
        <div className="medical-topbar">
          <div className="page-title">
            <h1>
              {activeTab === "dashboard" && "Clinical Dashboard"}
              {activeTab === "patients" && "Patient Management"}
              {activeTab === "appointments" && "Appointments"}
              {activeTab === "chat" && "Medical AI Assistant"}
              {activeTab === "reports" && "Medical Reports"}
              {activeTab === "settings" && "Settings"}
            </h1>
            <p>
              {new Date().toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}
            </p>
          </div>

          <div className="topbar-actions">
            <div className="search-bar">
              <span>🔍</span>
              <input 
                type="text" 
                placeholder="Search patients, reports..."
              />
            </div>
            <div className="notification-badge">
              <span>🔔</span>
            </div>
            <button className="login-btn" onClick={onLogout}>
              Logout
            </button>
          </div>
        </div>

        {/* Dashboard View */}
        {activeTab === "dashboard" && (
          <>
            {/* Stats Cards */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon">👥</div>
                <div className="stat-value">{stats.totalPatients}</div>
                <div className="stat-label">Total Patients</div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">📅</div>
                <div className="stat-value">{stats.todayAppointments}</div>
                <div className="stat-label">Today's Appointments</div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">⚠️</div>
                <div className="stat-value">{stats.criticalCases}</div>
                <div className="stat-label">Critical Cases</div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">📋</div>
                <div className="stat-value">{stats.pendingReports}</div>
                <div className="stat-label">Pending Reports</div>
              </div>
            </div>

            {/* Recent Patients */}
            <div className="patients-section">
              <div className="section-header">
                <h2>Recent Patients</h2>
                <button className="add-patient-btn">+ Add Patient</button>
              </div>

              <div className="patients-grid">
                {patients.slice(0, 4).map((patient, index) => (
                  <div key={index} className="patient-card">
                    <div className="patient-header">
                      <div className="patient-avatar">
                        {patient.name[0]}
                      </div>
                      <span className={`patient-status status-${patient.status}`}>
                        {patient.status}
                      </span>
                    </div>
                    <h3 className="patient-name">{patient.name}</h3>
                    <div className="patient-details">
                      <div className="detail-item">
                        <span className="detail-icon">📅</span>
                        <span>{patient.age} years • {patient.gender}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-icon">🏥</span>
                        <span>{patient.condition}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-icon">💊</span>
                        <span>{patient.medications?.length || 0} medications</span>
                      </div>
                    </div>
                    <div className="patient-footer">
                      <span className="last-visit">
                        Last visit: {patient.lastVisit}
                      </span>
                      <button className="view-btn">View</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Today's Appointments */}
            <div className="appointments-section">
              <div className="section-header">
                <h2>Today's Appointments</h2>
                <button className="add-patient-btn">Schedule New</button>
              </div>

              <div className="appointments-list">
                {appointments.slice(0, 5).map((apt, index) => (
                  <div key={index} className="appointment-item">
                    <div className="appointment-time">
                      <span className="time-hour">{apt.time}</span>
                    </div>
                    <div className="appointment-info">
                      <div className="appointment-patient">{apt.patientName}</div>
                      <div className="appointment-type">{apt.type}</div>
                    </div>
                    <span className={`appointment-status status-${apt.status}`}>
                      {apt.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Chat View */}
        {activeTab === "chat" && (
          <div className="medical-chat-page">
            <div className="chat-container">
              <div className="chat-sidebar">
                <div className="chat-sidebar-header">
                  <h3>Patients</h3>
                  <button className="new-chat-btn">+</button>
                </div>

                <div className="patient-selector">
                  {patients.map((patient, index) => (
                    <div
                      key={index}
                      className={`patient-option ${selectedPatient?.id === patient.id ? "active" : ""}`}
                      onClick={() => setSelectedPatient(patient)}
                    >
                      <div className="patient-option-avatar">
                        {patient.name[0]}
                      </div>
                      <div className="patient-option-info">
                        <h4>{patient.name}</h4>
                        <p>{patient.condition}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="chat-main">
                <div className="chat-messages">
                  {selectedPatient ? (
                    chatMessages.length > 0 ? (
                      chatMessages.map((msg, index) => (
                        <div key={index} className={`message ${msg.role === "user" ? "user" : ""}`}>
                          <div className="message-avatar">
                            {msg.role === "user" ? "👤" : "🤖"}
                          </div>
                          <div className="message-content">
                            <div className="message-header">
                              <span className="message-sender">{msg.sender}</span>
                              <span className="message-time">{formatTime(msg.timestamp)}</span>
                            </div>
                            <div className="message-text">{msg.content}</div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="chat-center">
                        <div className="ai-icon">⚕️</div>
                        <h2>Medical AI Assistant</h2>
                        <p>
                          Ask me about {selectedPatient.name}'s case, get treatment 
                          suggestions, or analyze medical data.
                        </p>
                      </div>
                    )
                  ) : (
                    <div className="chat-center">
                      <div className="ai-icon">👥</div>
                      <h2>Select a Patient</h2>
                      <p>Choose a patient from the list to start a consultation</p>
                    </div>
                  )}

                  {isLoading && (
                    <div className="message">
                      <div className="message-avatar">🤖</div>
                      <div className="message-content">
                        <div className="loading-dots">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="chat-input-area">
                  <div className="input-container">
                    <textarea
                      placeholder={selectedPatient ? 
                        `Ask about ${selectedPatient.name}'s case...` : 
                        "Select a patient first..."
                      }
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          sendMedicalQuery();
                        }
                      }}
                      disabled={!selectedPatient || isLoading}
                      rows="2"
                    />
                    <div className="input-actions">
                      <button className="action-btn">📎</button>
                      <button 
                        className="action-btn send-btn"
                        onClick={sendMedicalQuery}
                        disabled={!selectedPatient || isLoading || !inputMessage.trim()}
                      >
                        ➤
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}