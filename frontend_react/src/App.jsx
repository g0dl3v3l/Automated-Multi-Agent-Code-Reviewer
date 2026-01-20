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
  AlertOctagon,
  Zap,
} from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import "./App.css";

function App() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [reviewData, setReviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // --- 1. HANDLE FILE UPLOAD ---
  const handleUpload = (e) => {
    const uploaded = Array.from(e.target.files);
    const validNewFiles = [];
    const rejectedErrors = [];

    uploaded.forEach((file) => {
      if (file.size === 0) {
        rejectedErrors.push(`${file.name} (Empty)`);
        return;
      }
      const isDuplicate =
        files.some((f) => f.name === file.name) ||
        validNewFiles.some((f) => f.name === file.name);

      if (isDuplicate) {
        rejectedErrors.push(`${file.name} (Duplicate)`);
        return;
      }
      validNewFiles.push(file);
    });

    if (rejectedErrors.length > 0) {
      setNotification(`Ignored: ${rejectedErrors.join(", ")}`);
      setTimeout(() => setNotification(null), 4000);
    }

    if (validNewFiles.length > 0) {
      setFiles((prevFiles) => [...prevFiles, ...validNewFiles]);
    }
    e.target.value = null;
  };

  // --- 2. HANDLE REMOVE FILE ---
  const removeFile = (fileName, e) => {
    e.stopPropagation();
    setFiles(files.filter((f) => f.name !== fileName));
    if (selectedFile === fileName) setSelectedFile(null);
  };

  // --- 3. HANDLE SCAN ---
  const handleScan = async () => {
    if (files.length === 0) return;

    setLoading(true);
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));

    try {
      const res = await axios.post(
        "http://localhost:8000/api/review/full",
        formData,
      );
      setReviewData(res.data);

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

    // Fallback support for both data structures
    const issueList = reviewData.clean_issues || reviewData.comments || [];
    const issues = issueList.filter((c) => c.file_path === fname);

    if (issues.some((i) => i.severity === "CRITICAL"))
      return <ShieldAlert color="#ff4d4d" size={16} />;
    if (issues.length > 0) return <AlertTriangle color="orange" size={16} />;
    return <CheckCircle color="#00cc66" size={16} />;
  };

  const currentFileObj = files.find((f) => f.name === selectedFile);
  const currentIssues = reviewData
    ? (reviewData.clean_issues || reviewData.comments || []).filter(
        (c) => c.file_path === selectedFile,
      )
    : [];

  return (
    <div className="app-layout">
      {notification && (
        <div className="toast-notification">
          <AlertOctagon size={18} color="#ff4d4d" />
          <span>{notification}</span>
        </div>
      )}

      <nav className="navbar">
        <h1 className="cyber-header">
          <Activity /> AI CODE REVIEWER
        </h1>
      </nav>

      <aside className="panel panel-left">
        <div className="panel-content">
          <div className="section-title">
            <FolderOpen size={18} /> EXPLORER
          </div>

          <label className="upload-zone">
            <UploadCloud size={32} color="#666" style={{ marginBottom: 10 }} />
            <div>Drag & drop files here</div>
            <input type="file" multiple onChange={handleUpload} hidden />
          </label>

          {files.length > 0 && (
            <button
              className="scan-btn"
              disabled={loading}
              onClick={handleScan}
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

      <aside className="panel panel-right">
        <div className="panel-content">
          <div className="section-title">
            <Activity size={18} /> INTELLIGENCE
          </div>

          {reviewData && reviewData.meta && (
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

              <div className="stat-grid">
                <div className="stat-box">
                  <div className="stat-value" style={{ color: "#ff4d4d" }}>
                    {reviewData.meta.total_vulnerabilities}
                  </div>
                  <div className="stat-label">TOTAL ISSUES</div>
                </div>
                <div className="stat-box">
                  <div className="stat-value" style={{ color: "#ffa500" }}>
                    {reviewData.meta.scan_duration_ms < 1000
                      ? `${reviewData.meta.scan_duration_ms}ms`
                      : `${(reviewData.meta.scan_duration_ms / 1000).toFixed(
                          1,
                        )}s`}
                  </div>
                  <div className="stat-label">SCAN TIME</div>
                </div>
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
                {(reviewData.praise || []).map((p, i) => (
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

// --- SUB-COMPONENT: ORIGINAL STRUCTURE WITH MULTI-TAG INJECTION ---
const CodeRenderer = ({ file, issues }) => {
  const [content, setContent] = useState("");

  // Tracks an ARRAY of open IDs to allow multiple active issues
  const [activeIssueIds, setActiveIssueIds] = useState([]);

  React.useEffect(() => {
    const reader = new FileReader();
    reader.onload = (e) => setContent(e.target.result);
    reader.readAsText(file);
    // Reset open issues when file changes
    setActiveIssueIds([]);
  }, [file]);

  // Helper to toggle a specific issue ID without closing others
  const toggleIssue = (id) => {
    setActiveIssueIds((prevIds) => {
      if (prevIds.includes(id)) {
        return prevIds.filter((i) => i !== id); // Close this one
      } else {
        return [...prevIds, id]; // Open this one (keep others)
      }
    });
  };

  const rawLines = content.split("\n");
  const renderedBlocks = [];

  let i = 0;
  while (i < rawLines.length) {
    const currentLineNum = i + 1;

    // Check if an issue STARTS at this line
    const startIssue = issues.find(
      (issue) => issue.line_start === currentLineNum,
    );

    if (startIssue) {
      // --- CASE 1: START OF A MULTI-LINE ISSUE ---

      // [NEW] Get ALL issues starting here for the badges
      const allIssuesHere = issues.filter(
        (issue) => issue.line_start === currentLineNum,
      );

      const endLine = startIssue.line_end;
      const linesInBlock = [];

      for (let j = i; j < endLine && j < rawLines.length; j++) {
        linesInBlock.push({
          text: rawLines[j],
          num: j + 1,
        });
      }

      // Check if THIS specific issue is in the active list
      const isOpen = activeIssueIds.includes(startIssue.id);

      renderedBlocks.push(
        <div
          key={`issue-group-${startIssue.id}`}
          className="issue-group-container"
          onClick={() => toggleIssue(startIssue.id)}
        >
          {linesInBlock.map((lineObj, idx) => (
            <div key={lineObj.num} className="code-line">
              <div
                style={{
                  width: 40,
                  color: "#666",
                  textAlign: "right",
                  paddingRight: 15,
                  userSelect: "none",
                }}
              >
                {lineObj.num}
              </div>
              <div
                style={{
                  flex: 1,
                  paddingLeft: 10,
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <SyntaxHighlighter
                  language="python"
                  style={vscDarkPlus}
                  customStyle={{
                    margin: 0,
                    padding: 0,
                    background: "transparent",
                    flex: 1,
                  }}
                  PreTag="span"
                >
                  {lineObj.text || " "}
                </SyntaxHighlighter>

                {/* [NEW] INJECT TAGS ONLY ON THE FIRST LINE OF THE BLOCK */}
                {idx === 0 && (
                  <div className="tag-container" style={{ marginLeft: "15px" }}>
                    {allIssuesHere.map((issue, tIdx) => (
                      <span
                        key={tIdx}
                        className={`issue-tag tag-${issue.category.toLowerCase()}`}
                      >
                        {issue.category}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Render Popup if ID is in the Active List */}
          {isOpen && (
            <div
              className="issue-card-overlay"
              onClick={(e) => e.stopPropagation()}
            >
              {/* [UPDATED] MAP OVER ALL ISSUES AT THIS LOCATION */}
              {allIssuesHere.map((issue, idx) => (
                <div
                  key={idx}
                  style={{
                    marginBottom: idx < allIssuesHere.length - 1 ? "15px" : "0",
                  }}
                >
                  <div className="issue-title">
                    <ShieldAlert size={16} /> {issue.title}
                  </div>
                  <div className="issue-body">{issue.body}</div>
                  {issue.suggestion && (
                    <div className="issue-fix">Fix: {issue.suggestion}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>,
      );

      i = endLine;
    } else {
      // --- CASE 2: NORMAL LINE ---
      renderedBlocks.push(
        <div key={currentLineNum} className="code-line">
          <div
            style={{
              width: 40,
              color: "#666",
              textAlign: "right",
              paddingRight: 15,
              userSelect: "none",
            }}
          >
            {currentLineNum}
          </div>
          <div style={{ flex: 1, paddingLeft: 10 }}>
            <SyntaxHighlighter
              language="python"
              style={vscDarkPlus}
              customStyle={{ margin: 0, padding: 0, background: "transparent" }}
              PreTag="span"
            >
              {rawLines[i] || " "}
            </SyntaxHighlighter>
          </div>
        </div>,
      );
      i++;
    }
  }

  return (
    <div style={{ fontSize: 14, fontFamily: "Roboto Mono", lineHeight: 1.5 }}>
      {renderedBlocks}
    </div>
  );
};

export default App;
