import { useEffect, useMemo, useRef, useState } from "react";
import { generateMagicImage } from "./lib/api";

const STYLE_OPTIONS = [
  { id: "magic", label: "Magic", accent: "Aurora glow" },
  { id: "viral", label: "Viral", accent: "Social-ready pop" },
  { id: "cinematic", label: "Cinematic", accent: "Film still drama" },
  { id: "fantasy", label: "Fantasy", accent: "Worldbuilding energy" },
  { id: "meme", label: "Meme", accent: "Internet chaos" }
];

function App() {
  const fileInputRef = useRef(null);
  const [selectedStyle, setSelectedStyle] = useState("magic");
  const [selectedFile, setSelectedFile] = useState(null);
  const [beforeUrl, setBeforeUrl] = useState("");
  const [afterUrl, setAfterUrl] = useState("");
  const [resultName, setResultName] = useState("");
  const [resultFormat, setResultFormat] = useState("");
  const [statusMessage, setStatusMessage] = useState("Upload an image to begin.");
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    return () => {
      if (beforeUrl) {
        URL.revokeObjectURL(beforeUrl);
      }
    };
  }, [beforeUrl]);

  const canGenerate = useMemo(
    () => Boolean(selectedFile) && Boolean(selectedStyle) && !isLoading,
    [selectedFile, selectedStyle, isLoading]
  );

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    if (!file.type.startsWith("image/")) {
      setErrorMessage("Please choose an image file such as PNG, JPG, or WEBP.");
      return;
    }

    if (beforeUrl) {
      URL.revokeObjectURL(beforeUrl);
    }

    setSelectedFile(file);
    setBeforeUrl(URL.createObjectURL(file));
    setAfterUrl("");
    setResultName("");
    setResultFormat("");
    setErrorMessage("");
    setStatusMessage(`Ready to generate a ${selectedStyle} version of ${file.name}.`);
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleGenerate = async () => {
    if (!selectedFile) {
      setErrorMessage("Upload an image before generating.");
      return;
    }

    setIsLoading(true);
    setErrorMessage("");
    setStatusMessage(`Transforming your image in ${selectedStyle} mode...`);

    try {
      const payload = await generateMagicImage({
        file: selectedFile,
        style: selectedStyle
      });

      setAfterUrl(payload.result_image_url);
      setResultName(payload.output_filename || "magic-image-result");
      setResultFormat(payload.content_type || "");
      setStatusMessage(payload.message || "Transformation complete.");
    } catch (error) {
      setErrorMessage(error.message || "Something went wrong.");
      setStatusMessage("We couldn't generate your image this time.");
    } finally {
      setIsLoading(false);
    }
  };

  const activeStyle = STYLE_OPTIONS.find((style) => style.id === selectedStyle);

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <main className="page">
        <section className="hero-card">
          <div className="hero-copy">
            <span className="eyebrow">Magic Image Studio</span>
            <h1>Turn one image into five distinct internet-ready moods.</h1>
            <p>
              Upload a photo, choose a one-word style, and generate a polished variation.
              The MVP runs in demo mode by default, so you can launch it now and plug in live
              AI editing later.
            </p>
          </div>

          <div className="hero-stats">
            <div className="stat-tile">
              <strong>5</strong>
              <span>Styles</span>
            </div>
            <div className="stat-tile">
              <strong>FastAPI</strong>
              <span>Backend</span>
            </div>
            <div className="stat-tile">
              <strong>Cloud Run</strong>
              <span>Ready</span>
            </div>
          </div>
        </section>

        <section className="studio-grid">
          <div className="panel panel-controls">
            <div className="panel-header">
              <h2>1. Upload</h2>
              <p>PNG, JPG, WEBP, GIF, or BMP</p>
            </div>

            <button className="upload-dropzone" type="button" onClick={handleBrowseClick}>
              <span className="upload-icon">+</span>
              <span>{selectedFile ? selectedFile.name : "Choose an image"}</span>
              <small>{selectedFile ? "Click to replace" : "Drag-and-drop friendly button"}</small>
            </button>

            <input
              ref={fileInputRef}
              className="visually-hidden"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
            />

            <div className="panel-header">
              <h2>2. Pick a style</h2>
              <p>One word, one direction</p>
            </div>

            <div className="style-grid">
              {STYLE_OPTIONS.map((style) => (
                <button
                  key={style.id}
                  type="button"
                  className={`style-chip ${selectedStyle === style.id ? "active" : ""}`}
                  onClick={() => setSelectedStyle(style.id)}
                >
                  <span>{style.label}</span>
                  <small>{style.accent}</small>
                </button>
              ))}
            </div>

            <div className="style-summary">
              <span>Current style</span>
              <strong>{activeStyle?.label}</strong>
              <p>{activeStyle?.accent}</p>
            </div>

            <button className="generate-button" type="button" onClick={handleGenerate} disabled={!canGenerate}>
              {isLoading ? "Generating..." : "Generate Image"}
            </button>

            <div className="status-card">
              <span className="status-label">Status</span>
              <p>{statusMessage}</p>
              {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
            </div>
          </div>

          <div className="panel panel-preview">
            <div className="preview-header">
              <div>
                <h2>3. Compare</h2>
                <p>Before and after in one place</p>
              </div>

              {afterUrl ? (
                <a className="download-button" href={afterUrl} download={resultName}>
                  Download
                </a>
              ) : null}
            </div>

            <div className="comparison-grid">
              <article className="image-card">
                <div className="image-card-label">Before</div>
                {beforeUrl ? (
                  <img src={beforeUrl} alt="Uploaded preview" className="preview-image" />
                ) : (
                  <div className="empty-state">
                    <strong>No image yet</strong>
                    <p>Your upload preview appears here.</p>
                  </div>
                )}
              </article>

              <article className="image-card">
                <div className="image-card-label">After</div>
                {isLoading ? (
                  <div className="loading-state">
                    <div className="spinner" />
                    <strong>Working on it...</strong>
                    <p>Preparing your {selectedStyle} version.</p>
                  </div>
                ) : afterUrl ? (
                  <img
                    src={afterUrl}
                    alt={`${selectedStyle} generated result`}
                    className="preview-image"
                  />
                ) : (
                  <div className="empty-state">
                    <strong>Awaiting generation</strong>
                    <p>Your transformed image will appear here.</p>
                  </div>
                )}
              </article>
            </div>

            <div className="result-meta">
              <div>
                <span>Filename</span>
                <strong>{resultName || "Not generated yet"}</strong>
              </div>
              <div>
                <span>Format</span>
                <strong>{resultFormat || "Pending"}</strong>
              </div>
              <div>
                <span>Mode</span>
                <strong>{afterUrl ? "Ready" : "Standby"}</strong>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
