import React, { useState } from "react";
import axios from "axios";
import {
  FolderOpen,
  FileCode,
  Activity,
  UploadCloud,
  Play,
  AlertTriangle,
  CheckCircle,
  ShieldAlert,
  X,
  AlertOctagon, // <--- Added for notification icon
} from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import "./App.css";

function App() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [reviewData, setReviewData] = useState(null);
  const [loading, setLoading] = useState(false);

  // --- NEW STATE: Notification Message ---
  const [notification, setNotification] = useState(null);

  // --- 1. HANDLE FILE UPLOAD (With Validation) ---
  const handleUpload = (e) => {
    const uploaded = Array.from(e.target.files);
    const validNewFiles = [];
    const rejectedErrors = [];

    uploaded.forEach((file) => {
      // Check 1: Empty File
      if (file.size === 0) {
        rejectedErrors.push(`${file.name} (Empty)`);
        return;
      }

      // Check 2: Duplicate File (Check against existing files AND new batch)
      const isDuplicate =
        files.some((f) => f.name === file.name) ||
        validNewFiles.some((f) => f.name === file.name);

      if (isDuplicate) {
        rejectedErrors.push(`${file.name} (Duplicate)`);
        return;
      }

      // If valid, add to temporary list
      validNewFiles.push(file);
    });

    // If there were errors, show notification for 4 seconds
    if (rejectedErrors.length > 0) {
      setNotification(`Ignored: ${rejectedErrors.join(", ")}`);
      setTimeout(() => setNotification(null), 4000);
    }

    // Only update state if we have valid files
    if (validNewFiles.length > 0) {
      setFiles((prevFiles) => {
        const newFiles = [...prevFiles, ...validNewFiles];
        return newFiles;
      });
    }

    // Reset the input value
    e.target.value = null;
  };

  // --- 2. HANDLE REMOVE FILE (Optional cleanup) ---
  const removeFile = (fileName, e) => {
    e.stopPropagation(); // Stop clicking the file from selecting it
    setFiles(files.filter((f) => f.name !== fileName));
    if (selectedFile === fileName) setSelectedFile(null);
  };

  // --- 3. HANDLE SCAN (Triggered by Button Only) ---
  const handleScan = async () => {
    if (files.length === 0) return;

    setLoading(true);
    const formData = new FormData();

    // Add all currently piled up files to the payload
    files.forEach((f) => formData.append("files", f));

    try {
      const res = await axios.post(
        "http://localhost:8000/api/review",
        formData
      );
      setReviewData(res.data);

      // Auto-select first file if none selected
      if (files.length > 0 && !selectedFile) {
        setSelectedFile(files[0].name);
      }
    } catch (err) {
      alert("Backend connection failed. Is Flask running?");
    } finally {
      setLoading(false);
    }
  };

  // --- HELPERS ---
  const getFileIcon = (fname) => {
    if (!reviewData) return <FileCode size={16} />;
    const issues = reviewData.comments.filter((c) => c.file_path === fname);
    if (issues.some((i) => i.severity === "CRITICAL"))
      return <ShieldAlert color="#ff4d4d" size={16} />;
    if (issues.length > 0) return <AlertTriangle color="orange" size={16} />;
    return <CheckCircle color="#00cc66" size={16} />;
  };

  const currentFileObj = files.find((f) => f.name === selectedFile);
  const currentIssues = reviewData
    ? reviewData.comments.filter((c) => c.file_path === selectedFile)
    : [];

  return (
    <div className="app-layout">
      {/* --- NEW: NOTIFICATION BANNER --- */}
      {notification && (
        <div className="toast-notification">
          <AlertOctagon size={18} color="#ff4d4d" />
          <span>{notification}</span>
        </div>
      )}

      {/* NAVBAR */}
      <nav className="navbar">
        <h1 className="cyber-header">
          <Activity /> AI CODE REVIEWER
        </h1>
      </nav>

      {/* LEFT PANEL: EXPLORER */}
      <aside className="panel panel-left">
        <div className="panel-content">
          <div className="section-title">
            <FolderOpen size={18} /> EXPLORER
          </div>

          {/* Upload Zone */}
          <label className="upload-zone">
            <UploadCloud size={32} color="#666" style={{ marginBottom: 10 }} />
            <div>Drag & drop files here</div>
            <input type="file" multiple onChange={handleUpload} hidden />
          </label>

          {/* SCAN BUTTON - Now triggers handleScan */}
          {files.length > 0 && (
            <button
              className="scan-btn"
              disabled={loading}
              onClick={handleScan} // <--- ACTION ATTACHED HERE
            >
              {loading ? (
                "SCANNING..."
              ) : (
                <>
                  <Play size={16} /> INITIATE SCAN
                </>
              )}
            </button>
          )}

          {/* File List */}
          <div style={{ marginTop: 20 }}>
            {files.map((f) => (
              <div
                key={f.name}
                className={`file-item ${
                  selectedFile === f.name ? "active" : ""
                }`}
                onClick={() => setSelectedFile(f.name)}
              >
                <div className="file-name">
                  {getFileIcon(f.name)} {f.name}
                </div>
                {/* Remove Button */}
                <button
                  onClick={(e) => removeFile(f.name, e)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#666",
                    cursor: "pointer",
                  }}
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* CENTER PANEL: EDITOR */}
      <main className="panel panel-center">
        <div className="editor-wrapper">
          <div className="editor-header section-title">
            <FileCode size={18} /> ACTIVE EDITOR
          </div>

          <div className="code-scroll-area">
            {currentFileObj ? (
              <CodeRenderer file={currentFileObj} issues={currentIssues} />
            ) : (
              <div style={{ padding: 20, color: "#666" }}>
                Select a file to view code.
              </div>
            )}
          </div>
        </div>
      </main>

      {/* RIGHT PANEL: INTELLIGENCE */}
      <aside className="panel panel-right">
        <div className="panel-content">
          <div className="section-title">
            <Activity size={18} /> INTELLIGENCE
          </div>

          {reviewData && (
            <>
              <div className="score-box">
                <div
                  className="score-val"
                  style={{
                    color:
                      reviewData.meta.quality_score > 70
                        ? "#00cc66"
                        : "#ff4d4d",
                  }}
                >
                  {reviewData.meta.quality_score}
                  <span style={{ fontSize: "1.5rem", color: "#666" }}>
                    /100
                  </span>
                </div>
                <div className="score-label">QUALITY SCORE</div>
              </div>

              <div style={{ marginTop: 20, marginBottom: 20 }}>
                <div style={{ marginBottom: 5, fontSize: "0.9rem" }}>
                  Verdict:{" "}
                  <span className="verdict-tag">
                    {reviewData.meta.final_verdict}
                  </span>
                </div>
                <div style={{ fontSize: "0.9rem" }}>
                  Risk Level:{" "}
                  <span style={{ color: "red", fontWeight: "bold" }}>
                    {reviewData.meta.risk_level}
                  </span>
                </div>
              </div>

              <div>
                <h4
                  style={{
                    fontFamily: "Orbitron",
                    color: "#ccc",
                    marginBottom: 10,
                  }}
                >
                  ⚖️ THE VERDICT
                </h4>
                <div className="summary-text">{reviewData.summary}</div>
              </div>

              <div style={{ marginTop: 20 }}>
                <h4
                  style={{
                    fontFamily: "Orbitron",
                    color: "#ccc",
                    marginBottom: 10,
                  }}
                >
                  👍 COMMENDATIONS
                </h4>
                {reviewData.praise.map((p, i) => (
                  <div key={i} className="praise-item">
                    <CheckCircle size={14} /> {p}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

// --- SUB-COMPONENT: Custom Line-by-Line Renderer ---
const CodeRenderer = ({ file, issues }) => {
  const [content, setContent] = useState("");
  const [activeIssueLine, setActiveIssueLine] = useState(null);

  React.useEffect(() => {
    const reader = new FileReader();
    reader.onload = (e) => setContent(e.target.result);
    reader.readAsText(file);
    setActiveIssueLine(null);
  }, [file]);

  const lines = content.split("\n");

  return (
    <div style={{ fontSize: 14, fontFamily: "Roboto Mono", lineHeight: 1.5 }}>
      {lines.map((line, index) => {
        const lineNum = index + 1;
        const lineIssues = issues.filter((i) => i.line_start === lineNum);
        const hasIssue = lineIssues.length > 0;
        const isOpen = activeIssueLine === lineNum;

        return (
          <React.Fragment key={index}>
            <div
              className={`code-line ${hasIssue ? "line-has-issue" : ""}`}
              onClick={() =>
                hasIssue && setActiveIssueLine(isOpen ? null : lineNum)
              }
            >
              <div
                style={{
                  width: 40,
                  color: "#666",
                  textAlign: "right",
                  paddingRight: 15,
                  userSelect: "none",
                }}
              >
                {lineNum}
              </div>
              <div style={{ flex: 1, paddingLeft: 10 }}>
                <SyntaxHighlighter
                  language="python"
                  style={vscDarkPlus}
                  customStyle={{
                    margin: 0,
                    padding: 0,
                    background: "transparent",
                  }}
                  PreTag="span"
                >
                  {line || " "}
                </SyntaxHighlighter>
              </div>
            </div>

            {hasIssue &&
              isOpen &&
              lineIssues.map((issue) => (
                <div key={issue.id} className="issue-card-overlay">
                  <div className="issue-title">
                    <ShieldAlert size={16} /> {issue.title}
                  </div>
                  <div className="issue-body">{issue.body}</div>
                  {issue.suggestion && (
                    <div className="issue-fix">Fix: {issue.suggestion}</div>
                  )}
                </div>
              ))}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default App;
