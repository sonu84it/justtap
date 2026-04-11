import React, { useEffect, useMemo, useRef, useState } from "react";
import { generateMagicImage } from "./lib/api";

// --- Constants ---
const STYLE_OPTIONS = [
  { id: "magic", label: "Magic", accent: "Aurora glow", icon: "✨" },
  { id: "viral", label: "Viral", accent: "Social-ready pop", icon: "🔥" },
  { id: "cinematic", label: "Cinematic", accent: "Film still drama", icon: "🎬" },
  { id: "fantasy", label: "Fantasy", accent: "Worldbuilding", icon: "🐉" },
  { id: "meme", label: "Meme", accent: "Internet chaos", icon: "🤡" }
];

// --- Icons (Inline SVGs for portability) ---
const UploadIcon = () => (
  <svg className="w-8 h-8 text-neutral-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
  </svg>
);

const DownloadIcon = () => (
  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

const SparklesIcon = () => (
  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
);

// --- Main Application ---
export default function App() {
  const fileInputRef = useRef(null);
  const [selectedStyle, setSelectedStyle] = useState("magic");
  const [selectedFile, setSelectedFile] = useState(null);
  const [beforeUrl, setBeforeUrl] = useState("");
  const [afterUrl, setAfterUrl] = useState("");
  const [resultName, setResultName] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Cleanup object URLs to avoid memory leaks
  useEffect(() => {
    return () => {
      if (beforeUrl) URL.revokeObjectURL(beforeUrl);
      if (afterUrl) URL.revokeObjectURL(afterUrl);
    };
  }, []);

  const canGenerate = useMemo(
    () => Boolean(selectedFile) && Boolean(selectedStyle) && !isLoading,
    [selectedFile, selectedStyle, isLoading]
  );

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setErrorMessage("Please choose a valid image file (PNG, JPG, WEBP).");
      return;
    }

    if (beforeUrl) URL.revokeObjectURL(beforeUrl);

    setSelectedFile(file);
    setBeforeUrl(URL.createObjectURL(file));
    setAfterUrl("");
    setResultName("");
    setErrorMessage("");
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleGenerate = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    setErrorMessage("");

    try {
      const payload = await generateMagicImage({
        file: selectedFile,
        style: selectedStyle
      });

      setAfterUrl(payload.result_image_url);
      setResultName(payload.output_filename || "justtap-result.png");
    } catch (error) {
      setErrorMessage(error.message || "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-50 font-sans selection:bg-violet-500/30">
      <nav className="sticky top-0 z-50 border-b border-neutral-900 bg-neutral-950/50 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-fuchsia-600">
              <SparklesIcon />
            </div>
            <span className="text-xl font-bold tracking-tight">JustTap</span>
          </div>
          <div className="rounded-full border border-neutral-800 bg-neutral-900 px-3 py-1 text-sm font-medium text-neutral-500">
            Beta Mode
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-10 max-w-2xl">
          <h1 className="mb-4 text-4xl font-extrabold tracking-tight sm:text-5xl">
            No prompts.<br />
            <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
              Just one word.
            </span>
          </h1>
          <p className="text-lg leading-relaxed text-neutral-400">
            Upload your photo, choose a vibe, and let AI do the rest.
            No complicated tools, no learning curve. Just simple, powerful magic.
          </p>
        </div>

        <div className="flex flex-col items-start gap-8 lg:flex-row lg:gap-12">
          <div className="sticky top-24 flex w-full flex-col gap-8 lg:w-1/3">
            <section>
              <div className="mb-3 flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-800 text-xs font-bold text-neutral-300">1</div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-300">Upload Image</h2>
              </div>

              <button
                onClick={handleBrowseClick}
                className={`group relative flex w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all duration-200 ease-out ${
                  selectedFile
                    ? "border-violet-500/50 bg-violet-500/5"
                    : "border-neutral-800 hover:border-neutral-600 hover:bg-neutral-900/50"
                }`}
              >
                <UploadIcon />
                <span className="mb-1 text-sm font-medium text-neutral-200">
                  {selectedFile ? selectedFile.name : "Click or drag to upload"}
                </span>
                <span className="text-xs text-neutral-500">
                  {selectedFile ? "Click to replace image" : "Supports PNG, JPG, WEBP"}
                </span>
              </button>
              <input
                ref={fileInputRef}
                className="hidden"
                type="file"
                accept="image/*"
                onChange={handleFileChange}
              />
            </section>

            <section>
              <div className="mb-3 flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-800 text-xs font-bold text-neutral-300">2</div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-300">Select Vibe</h2>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {STYLE_OPTIONS.map((style) => (
                  <button
                    key={style.id}
                    onClick={() => setSelectedStyle(style.id)}
                    className={`flex flex-col items-start rounded-xl border p-4 text-left transition-all duration-200 ${
                      selectedStyle === style.id
                        ? "border-violet-500 bg-violet-500/10 shadow-[0_0_15px_rgba(139,92,246,0.15)]"
                        : "border-neutral-800 bg-neutral-900/40 hover:border-neutral-700 hover:bg-neutral-800/50"
                    }`}
                  >
                    <span className="mb-2 text-xl">{style.icon}</span>
                    <span className={`mb-0.5 text-sm font-semibold ${selectedStyle === style.id ? "text-violet-300" : "text-neutral-200"}`}>
                      {style.label}
                    </span>
                    <span className="w-full truncate text-xs text-neutral-500">{style.accent}</span>
                  </button>
                ))}
              </div>
            </section>

            <div className="border-t border-neutral-900 pt-4">
              {errorMessage && (
                <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
                  {errorMessage}
                </div>
              )}

              <button
                onClick={handleGenerate}
                disabled={!canGenerate}
                className={`flex w-full items-center justify-center rounded-xl px-6 py-4 text-lg font-bold transition-all duration-300 ${
                  canGenerate
                    ? "bg-neutral-50 text-neutral-950 shadow-[0_0_20px_rgba(255,255,255,0.15)] hover:scale-[1.02]"
                    : "cursor-not-allowed border border-neutral-800 bg-neutral-900 text-neutral-600"
                }`}
              >
                {isLoading ? (
                  <span className="flex items-center">
                    <svg className="-ml-1 mr-3 h-5 w-5 animate-spin text-neutral-500" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Generating...
                  </span>
                ) : (
                  <span className="flex items-center">
                    <SparklesIcon />
                    Generate Magic
                  </span>
                )}
              </button>
            </div>
          </div>

          <div className="flex w-full flex-col gap-6 lg:w-2/3">
            <div className="flex min-h-[300px] w-full flex-col overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-900">
              <div className="flex items-center justify-between border-b border-neutral-800 bg-neutral-900/80 px-4 py-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500">Original Upload</span>
              </div>
              <div className="flex flex-1 items-center justify-center bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMiIgY3k9IjIiIHI9IjIiIGZpbGw9IiMzMzMiLz48L3N2Zz4=')] p-4">
                {beforeUrl ? (
                  <img src={beforeUrl} alt="Original" className="max-h-[500px] w-auto rounded-lg object-contain shadow-2xl" />
                ) : (
                  <div className="flex flex-col items-center text-sm text-neutral-600">
                    <svg className="mb-3 h-12 w-12 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                    Waiting for image...
                  </div>
                )}
              </div>
            </div>

            <div className="group relative flex min-h-[400px] w-full flex-col overflow-hidden rounded-2xl border border-neutral-800">
              {afterUrl && !isLoading && (
                <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-r from-violet-500/20 to-fuchsia-500/20 blur-xl"></div>
              )}

              <div className="z-10 flex items-center justify-between border-b border-neutral-800 bg-neutral-900/90 px-4 py-3">
                <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-400">
                  <SparklesIcon /> Result
                </span>

                {afterUrl && (
                  <a
                    href={afterUrl}
                    download={resultName}
                    className="flex items-center rounded-md bg-white px-3 py-1.5 text-xs font-semibold text-black transition-colors hover:bg-neutral-200"
                  >
                    <DownloadIcon /> Download
                  </a>
                )}
              </div>

              <div className="relative z-0 flex flex-1 items-center justify-center overflow-hidden bg-[#0a0a0a] p-4">
                {isLoading ? (
                  <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-neutral-900/50 backdrop-blur-sm">
                    <div className="mb-4 h-16 w-16 animate-spin rounded-full border-4 border-neutral-800 border-t-violet-500"></div>
                    <p className="animate-pulse font-medium text-violet-400">Applying {selectedStyle} magic...</p>
                  </div>
                ) : afterUrl ? (
                  <img src={afterUrl} alt="Transformed Result" className="max-h-[600px] w-auto animate-in rounded-lg object-contain shadow-2xl fade-in duration-700" />
                ) : (
                  <div className="flex max-w-xs flex-col items-center text-center text-sm text-neutral-600">
                    <div className="mb-4 flex h-16 w-16 -rotate-6 items-center justify-center rounded-2xl border border-neutral-800 bg-neutral-900">
                      <SparklesIcon />
                    </div>
                    <p>Your AI-transformed image will appear here instantly.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
