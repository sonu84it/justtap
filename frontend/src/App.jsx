import React, { useEffect, useMemo, useRef, useState } from "react";
import { fetchHealth, generateMagicImage } from "./lib/api";

const STYLE_OPTIONS = [
  { id: "magic", label: "Magic", accent: "Aurora glow", icon: "✨" },
  { id: "viral", label: "Viral", accent: "Social-ready pop", icon: "🔥" },
  { id: "cinematic", label: "Cinematic", accent: "Film still drama", icon: "🎬" },
  { id: "fantasy", label: "Fantasy", accent: "Worldbuilding", icon: "🐉" },
  { id: "meme", label: "Meme", accent: "Internet chaos", icon: "🤡" }
];

const MODE_OPTIONS = [
  { id: "creative", label: "Creative", accent: "Prompt + Gemini" },
  { id: "preserve", label: "Preserve", accent: "Upload + Imagen" }
];

const ASPECT_RATIO_OPTIONS = [
  { id: "1:1", label: "Square" },
  { id: "3:4", label: "Portrait" },
  { id: "4:3", label: "Classic" },
  { id: "9:16", label: "Story" },
  { id: "16:9", label: "Wide" }
];

const PREVIEW_TABS = [
  { id: "before", label: "Original" },
  { id: "after", label: "Result" }
];

const UploadIcon = () => (
  <svg className="mb-2 h-6 w-6 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
  </svg>
);

const DownloadIcon = () => (
  <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

const SparklesIcon = ({ className = "mr-2 h-5 w-5" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
);

function PreviewPanel({ title, imageUrl, emptyCopy, loading = false, action = null }) {
  return (
    <section className="flex min-h-[250px] flex-1 flex-col overflow-hidden rounded-3xl border border-white/10 bg-white/[0.03] shadow-[0_24px_80px_rgba(0,0,0,0.35)] lg:min-h-0">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">{title}</span>
        {action}
      </div>
      <div className="relative flex flex-1 items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(139,92,246,0.12),_transparent_45%),linear-gradient(180deg,_rgba(255,255,255,0.02),_rgba(255,255,255,0.01))] p-4 lg:p-5">
        {loading ? (
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="h-16 w-16 animate-spin rounded-full border-4 border-white/10 border-t-violet-400" />
            <div>
              <p className="font-medium text-violet-300">Crafting your new look</p>
              <p className="mt-1 text-sm text-neutral-500">This usually takes a few seconds.</p>
            </div>
          </div>
        ) : imageUrl ? (
          <img src={imageUrl} alt={title} className="max-h-[42vh] w-auto rounded-2xl object-contain shadow-2xl lg:max-h-[calc(100vh-17rem)]" />
        ) : (
          <div className="max-w-[18rem] text-center text-sm text-neutral-500">{emptyCopy}</div>
        )}
      </div>
    </section>
  );
}

export default function App() {
  const fileInputRef = useRef(null);
  const beforeObjectUrlRef = useRef("");
  const [generationMode, setGenerationMode] = useState("creative");
  const [selectedStyle, setSelectedStyle] = useState("magic");
  const [selectedFile, setSelectedFile] = useState(null);
  const [aspectRatio, setAspectRatio] = useState("1:1");
  const [beforeUrl, setBeforeUrl] = useState("");
  const [afterUrl, setAfterUrl] = useState("");
  const [resultName, setResultName] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activePreview, setActivePreview] = useState("before");
  const [usageInfo, setUsageInfo] = useState({
    dailyLimit: 10,
    remainingGenerations: 10,
    usedToday: 0
  });

  useEffect(() => {
    return () => {
      if (beforeObjectUrlRef.current) {
        URL.revokeObjectURL(beforeObjectUrlRef.current);
      }
    };
  }, []);

  useEffect(() => {
    let isActive = true;

    async function loadHealth() {
      try {
        const health = await fetchHealth();
        if (!isActive) {
          return;
        }

        setUsageInfo((current) => ({
          dailyLimit: health.daily_generation_limit ?? current.dailyLimit,
          remainingGenerations: health.daily_generation_limit ?? current.remainingGenerations,
          usedToday: current.usedToday
        }));
      } catch {
        // Keep UI usable even if the backend does not expose health metadata yet.
      }
    }

    loadHealth();

    return () => {
      isActive = false;
    };
  }, []);

  const canGenerate = useMemo(
    () => {
      if (!selectedStyle || isLoading) {
        return false;
      }

      return Boolean(selectedFile);
    },
    [selectedFile, selectedStyle, isLoading]
  );

  const selectedStyleMeta = STYLE_OPTIONS.find((style) => style.id === selectedStyle) ?? STYLE_OPTIONS[0];

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    if (!file.type.startsWith("image/")) {
      setErrorMessage("Please choose a valid image file in PNG, JPG, or WEBP format.");
      return;
    }

    if (beforeObjectUrlRef.current) {
      URL.revokeObjectURL(beforeObjectUrlRef.current);
    }

    const objectUrl = URL.createObjectURL(file);
    beforeObjectUrlRef.current = objectUrl;
    setSelectedFile(file);
    setBeforeUrl(objectUrl);
    setAfterUrl("");
    setResultName("");
    setErrorMessage("");
    setSuccessMessage("");
    setActivePreview("before");
  };

  const handleGenerate = async () => {
    if (!canGenerate) {
      return;
    }

    setIsLoading(true);
    setErrorMessage("");
    setSuccessMessage("");
    setActivePreview("after");

    try {
      const payload = await generateMagicImage({
        file: selectedFile,
        style: selectedStyle,
        mode: generationMode,
        aspectRatio
      });

      setAfterUrl(payload.result_image_url);
      setResultName(payload.output_filename || "justtap-result.png");
      setUsageInfo((current) => {
        const nextUsedToday = payload.used_today ?? current.usedToday + 1;
        const nextDailyLimit = payload.daily_limit ?? current.dailyLimit;
        const nextRemaining = payload.remaining_generations ?? Math.max(nextDailyLimit - nextUsedToday, 0);

        return {
          dailyLimit: nextDailyLimit,
          remainingGenerations: nextRemaining,
          usedToday: nextUsedToday
        };
      });
      setSuccessMessage(payload.message || "Your image is ready to download.");
    } catch (error) {
      setErrorMessage(error.message || "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  };

  const visibleMobileImage = activePreview === "after" ? afterUrl : beforeUrl;
  const visibleMobileCopy = activePreview === "after"
    ? "Your generated result will appear here after creation."
    : "Upload a photo to preview it here before generating.";

  return (
    <div className="min-h-screen bg-[#050816] text-neutral-50 selection:bg-violet-500/30 lg:h-screen lg:overflow-hidden">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-4 sm:px-5 sm:py-5 lg:h-screen lg:min-h-0 lg:px-6 lg:py-4">
        <header className="mb-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 backdrop-blur sm:px-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white shadow-[0_14px_40px_rgba(139,92,246,0.35)]">
                <SparklesIcon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-lg font-semibold tracking-tight">JustTap</p>
                <p className="text-xs uppercase tracking-[0.2em] text-neutral-500">One-word image styling</p>
                <h1 className="mt-2 text-lg font-semibold tracking-tight text-neutral-50 sm:text-xl">
                  Style a photo or generate a fresh concept.
                </h1>
                <p className="mt-1 max-w-2xl text-sm leading-5 text-neutral-400">
                  Upload a photo, then choose Creative for bolder Gemini edits or Preserve for steadier Imagen transformations.
                </p>
              </div>
            </div>
            <div className="shrink-0 rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 text-right text-xs font-medium text-neutral-300">
              <p className="uppercase tracking-[0.18em] text-neutral-500">Usage today</p>
              <p className="mt-1 text-sm font-semibold text-neutral-100">
                {usageInfo.remainingGenerations} of {usageInfo.dailyLimit} left
              </p>
            </div>
          </div>
        </header>

        <main className="grid flex-1 gap-3 lg:min-h-0 lg:grid-cols-[340px_minmax(0,1fr)] lg:overflow-hidden">
          <section className="flex flex-col rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] p-4 shadow-[0_30px_100px_rgba(0,0,0,0.4)] sm:p-5 lg:min-h-0 lg:overflow-y-auto lg:pr-2">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              <div className="rounded-3xl border border-white/10 bg-black/20 p-3.5">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[13px] font-semibold text-neutral-100">Generation mode</p>
                  <p className="text-[11px] text-neutral-500">Smart model routing</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {MODE_OPTIONS.map((option) => (
                    <button
                      key={option.id}
                      onClick={() => setGenerationMode(option.id)}
                      className={`rounded-2xl border px-3 py-2.5 text-left transition-all ${
                        generationMode === option.id
                          ? "border-violet-400 bg-violet-500/10 text-violet-100"
                          : "border-white/10 bg-white/[0.03] text-neutral-200 hover:border-white/20 hover:bg-white/[0.06]"
                      }`}
                    >
                      <p className="text-[13px] font-semibold">{option.label}</p>
                      <p className="mt-0.5 text-[10px] leading-4 text-neutral-500">{option.accent}</p>
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={() => fileInputRef.current?.click()}
                className={`flex min-h-[96px] flex-col items-center justify-center rounded-3xl border border-dashed px-4 py-4 text-center transition-all ${
                  selectedFile
                    ? "border-violet-400/50 bg-violet-500/10"
                    : "border-white/15 bg-white/[0.03] hover:border-white/30 hover:bg-white/[0.05]"
                }`}
              >
                <UploadIcon />
                <p className="text-[13px] font-semibold text-neutral-100">
                  {selectedFile ? selectedFile.name : "Upload your image"}
                </p>
                <p className="mt-0.5 text-[11px] text-neutral-500">
                  {selectedFile ? "Tap to replace it" : "PNG, JPG, and WEBP are supported"}
                </p>
              </button>

              <div className="rounded-3xl border border-white/10 bg-black/20 p-3.5">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[13px] font-semibold text-neutral-100">Choose a vibe</p>
                  <p className="text-[11px] text-neutral-500">One word only</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {STYLE_OPTIONS.map((style) => (
                    <button
                      key={style.id}
                      onClick={() => setSelectedStyle(style.id)}
                      className={`rounded-2xl border px-3 py-2.5 text-left transition-all ${
                        selectedStyle === style.id
                          ? "border-violet-400 bg-violet-500/10 text-violet-100"
                          : "border-white/10 bg-white/[0.03] text-neutral-200 hover:border-white/20 hover:bg-white/[0.06]"
                      }`}
                    >
                      <p className="text-base">{style.icon}</p>
                      <p className="mt-1.5 text-[13px] font-semibold">{style.label}</p>
                      <p className="mt-0.5 text-[10px] leading-4 text-neutral-500">{style.accent}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {generationMode === "creative" ? (
              <div className="mt-3 rounded-3xl border border-white/10 bg-black/20 p-3.5">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[13px] font-semibold text-neutral-100">Aspect ratio</p>
                  <p className="text-[11px] text-neutral-500">Gemini output shape</p>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {ASPECT_RATIO_OPTIONS.map((option) => (
                    <button
                      key={option.id}
                      onClick={() => setAspectRatio(option.id)}
                      className={`rounded-2xl border px-3 py-2 text-left transition-all ${
                        aspectRatio === option.id
                          ? "border-violet-400 bg-violet-500/10 text-violet-100"
                          : "border-white/10 bg-white/[0.03] text-neutral-200 hover:border-white/20 hover:bg-white/[0.06]"
                      }`}
                    >
                      <p className="text-[13px] font-semibold">{option.id}</p>
                      <p className="mt-0.5 text-[10px] leading-4 text-neutral-500">{option.label}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            <input
              ref={fileInputRef}
              className="hidden"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
            />

            {(errorMessage || successMessage) && (
              <div
                className={`mt-4 rounded-2xl border px-4 py-3 text-sm ${
                  errorMessage
                    ? "border-red-500/25 bg-red-500/10 text-red-300"
                    : "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                }`}
              >
                {errorMessage || successMessage}
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={!canGenerate}
              className={`mt-3 flex items-center justify-center rounded-2xl px-5 py-3.5 text-sm font-semibold transition-all ${
                canGenerate
                  ? "bg-white text-neutral-950 shadow-[0_18px_45px_rgba(255,255,255,0.18)] hover:-translate-y-0.5"
                  : "cursor-not-allowed border border-white/10 bg-white/[0.06] text-neutral-500"
              }`}
            >
              {isLoading ? (
                <>
                  <span className="mr-3 inline-block h-5 w-5 animate-spin rounded-full border-2 border-neutral-400 border-t-neutral-900" />
                  {generationMode === "creative" ? "Generating your concept" : "Generating your image"}
                </>
              ) : (
                <>
                  <SparklesIcon />
                  {generationMode === "creative" ? `Create ${selectedStyleMeta.label}` : `Generate ${selectedStyleMeta.label}`}
                </>
              )}
            </button>
          </section>

          <section className="flex min-h-0 flex-col rounded-[28px] border border-white/10 bg-white/[0.03] p-4 shadow-[0_30px_100px_rgba(0,0,0,0.4)] sm:p-5 lg:overflow-hidden">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">Preview studio</p>
                <h2 className="mt-1 text-xl font-semibold tracking-tight">Original and result, side by side</h2>
              </div>
              <div className="inline-flex rounded-full border border-white/10 bg-black/20 p-1 lg:hidden">
                {PREVIEW_TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActivePreview(tab.id)}
                    className={`rounded-full px-4 py-2 text-sm transition ${
                      activePreview === tab.id ? "bg-white text-neutral-950" : "text-neutral-400"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="hidden flex-1 gap-3 lg:grid lg:grid-cols-2 lg:min-h-0">
              <PreviewPanel
                title="Original"
                imageUrl={beforeUrl}
                emptyCopy="Upload an image to preview the source photo here."
              />
              <PreviewPanel
                title="Result"
                imageUrl={afterUrl}
                loading={isLoading}
                emptyCopy="Choose a mode and style, then generate to see the transformed image here."
                action={afterUrl ? (
                  <a
                    href={afterUrl}
                    download={resultName}
                    className="inline-flex items-center rounded-full bg-white px-3 py-2 text-xs font-semibold text-neutral-950 transition hover:bg-neutral-200"
                  >
                    <DownloadIcon />
                    Download
                  </a>
                ) : null}
              />
            </div>

            <div className="flex flex-1 lg:hidden">
              <PreviewPanel
                title={activePreview === "after" ? "Result" : "Original"}
                imageUrl={visibleMobileImage}
                loading={activePreview === "after" && isLoading}
                emptyCopy={visibleMobileCopy}
                action={activePreview === "after" && afterUrl ? (
                  <a
                    href={afterUrl}
                    download={resultName}
                    className="inline-flex items-center rounded-full bg-white px-3 py-2 text-xs font-semibold text-neutral-950 transition hover:bg-neutral-200"
                  >
                    <DownloadIcon />
                    Download
                  </a>
                ) : null}
              />
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
