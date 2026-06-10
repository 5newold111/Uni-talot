"use client";

import { useState } from "react";
import { ScanLine, Loader2, X } from "lucide-react";
import { parseReceipt } from "@/lib/ocrParse";
import { formatYen } from "@/lib/format";

export interface ScanResult {
  fileName: string;
  mimeType: string;
  dataUrl: string;
  ocrText: string;
  amount: number | null;
  date: string | null;
}

// 画像を縮小して JPEG の data URL を返す（Sheets セル上限対策で小さめに）
function downscale(
  file: File,
  maxDim: number,
  quality: number,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
        const w = Math.round(img.width * scale);
        const h = Math.round(img.height * scale);
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) return reject(new Error("canvas error"));
        ctx.drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL("image/jpeg", quality));
      };
      img.onerror = reject;
      img.src = reader.result as string;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function ReceiptScanner({
  onResult,
}: {
  onResult: (r: ScanResult) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [preview, setPreview] = useState<string | null>(null);
  const [summary, setSummary] = useState<{ amount: number | null; date: string | null } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setError(null);
    setBusy(true);
    setProgress(0);
    setSummary(null);
    try {
      // 表示用プレビュー & OCR用（やや大きめ）と保存用（小さめ）を作成
      const ocrImage = await downscale(file, 1200, 0.7);
      const storeImage = await downscale(file, 480, 0.5);
      setPreview(storeImage);

      const Tesseract = await import("tesseract.js");
      const { data } = await Tesseract.recognize(ocrImage, "jpn+eng", {
        logger: (m: { status: string; progress: number }) => {
          if (m.status === "recognizing text") setProgress(Math.round(m.progress * 100));
        },
      });
      const text = data.text ?? "";
      const parsed = parseReceipt(text);
      setSummary(parsed);

      // 保存用 dataUrl が大きすぎる場合は本文のみ保持（Sheets セル上限対策）
      const safeDataUrl = storeImage.length <= 45000 ? storeImage : "";

      onResult({
        fileName: file.name,
        mimeType: "image/jpeg",
        dataUrl: safeDataUrl,
        ocrText: text.slice(0, 4000),
        amount: parsed.amount,
        date: parsed.date,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "OCRに失敗しました");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-dashed border-slate-300 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
          <ScanLine size={16} /> 領収書をスキャン（OCRで金額・日付を自動入力）
        </div>
        <label className="btn-secondary cursor-pointer text-xs">
          画像を選択
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
        </label>
      </div>

      {busy && (
        <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
          <Loader2 size={16} className="animate-spin" />
          解析中… {progress > 0 && `${progress}%`}
        </div>
      )}

      {error && <div className="mt-3 text-sm text-red-600">{error}</div>}

      {(preview || summary) && !busy && (
        <div className="mt-3 flex items-start gap-3">
          {preview && (
            <div className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={preview} alt="領収書" className="h-20 w-20 rounded-md border border-slate-200 object-cover" />
              <button
                type="button"
                className="absolute -right-2 -top-2 rounded-full bg-white p-0.5 text-slate-400 shadow hover:text-red-500"
                onClick={() => {
                  setPreview(null);
                  setSummary(null);
                }}
              >
                <X size={14} />
              </button>
            </div>
          )}
          {summary && (
            <div className="text-sm">
              <div className="text-xs text-slate-400">読み取り結果（自動入力済み）</div>
              <div>金額: {summary.amount != null ? formatYen(summary.amount) : "検出できず"}</div>
              <div>日付: {summary.date ?? "検出できず"}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
