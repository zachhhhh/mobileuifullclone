'use client';

import { useCallback, useState } from 'react';

type SubmissionState =
  | { status: 'idle' }
  | { status: 'uploading'; progress: number }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

const ACCEPTED_TYPES = ['application/octet-stream', 'application/x-itunes-ipa'];
const ACCEPTED_EXT = ['.ipa', '.apk', '.aab'];

function isBinaryAllowed(file: File) {
  return (
    ACCEPTED_EXT.some((ext) => file.name.toLowerCase().endsWith(ext)) ||
    ACCEPTED_TYPES.includes(file.type)
  );
}

export default function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [appName, setAppName] = useState('');
  const [version, setVersion] = useState('');
  const [notes, setNotes] = useState('');
  const [submission, setSubmission] = useState<SubmissionState>({ status: 'idle' });

  const onFileSelected = useCallback((selected: FileList | null) => {
    if (!selected || selected.length === 0) {
      setFile(null);
      return;
    }
    const candidate = selected[0];
    if (!isBinaryAllowed(candidate)) {
      setSubmission({ status: 'error', message: 'Unsupported file type. Use IPA, APK, or AAB.' });
      return;
    }
    setFile(candidate);
    setSubmission({ status: 'idle' });
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const items = event.dataTransfer.files;
      onFileSelected(items);
    },
    [onFileSelected]
  );

  const onSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!file) {
        setSubmission({ status: 'error', message: 'Select a binary before submitting.' });
        return;
      }
      const payload = new FormData();
      payload.append('binary', file);
      payload.append('appName', appName);
      payload.append('version', version);
      payload.append('notes', notes);

      try {
        setSubmission({ status: 'uploading', progress: 0 });
        const response = await fetch('/api/upload', {
          method: 'POST',
          body: payload,
        });
        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || 'Upload failed');
        }
        const data = await response.json();
        setSubmission({
          status: 'success',
          message: `Stored upload ${data.id} (${data.filename})`,
        });
        setFile(null);
        setVersion('');
        setNotes('');
      } catch (error) {
        setSubmission({
          status: 'error',
          message:
            error instanceof Error ? error.message : 'Unexpected error while uploading',
        });
      }
    },
    [file, appName, version, notes]
  );

  return (
    <form
      onSubmit={onSubmit}
      className="w-full max-w-3xl space-y-6 rounded-2xl bg-slate-900/70 p-8 shadow-xl border border-slate-800"
    >
      <div>
        <h1 className="text-3xl font-semibold">Clone Intake Portal</h1>
        <p className="mt-2 text-sm text-slate-300">
          Drop an IPA or APK build. We capture metadata and stage it for the automation pipeline.
        </p>
      </div>

      <div
        onDragOver={(event) => {
          event.preventDefault();
          event.dataTransfer.dropEffect = 'copy';
        }}
        onDrop={onDrop}
        className="flex h-48 w-full cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-600 bg-slate-950/60 p-6 text-center transition hover:border-blue-400"
      >
        <input
          id="binary"
          name="binary"
          type="file"
          className="hidden"
          accept={ACCEPTED_EXT.join(',')}
          onChange={(event) => onFileSelected(event.target.files)}
        />
        <label htmlFor="binary" className="flex flex-col items-center justify-center">
          <span className="text-lg font-medium">Click to browse</span>
          <span className="mt-1 text-sm text-slate-400">or drag & drop your IPA/APK here</span>
          <span className="mt-3 rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
            Allowed: .ipa, .apk, .aab
          </span>
        </label>
        {file ? (
          <p className="mt-4 text-sm text-blue-300">Selected: {file.name}</p>
        ) : (
          <p className="mt-4 text-sm text-slate-500">No file selected</p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col">
          <label htmlFor="appName" className="text-sm text-slate-300">
            App name
          </label>
          <input
            id="appName"
            name="appName"
            type="text"
            value={appName}
            onChange={(event) => setAppName(event.target.value)}
            className="mt-2 rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2 text-slate-100 focus:border-blue-400 focus:outline-none"
            placeholder="My Fitness App"
            required
          />
        </div>
        <div className="flex flex-col">
          <label htmlFor="version" className="text-sm text-slate-300">
            Version label
          </label>
          <input
            id="version"
            name="version"
            type="text"
            value={version}
            onChange={(event) => setVersion(event.target.value)}
            className="mt-2 rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2 text-slate-100 focus:border-blue-400 focus:outline-none"
            placeholder="1.2.3"
          />
        </div>
      </div>

      <div className="flex flex-col">
        <label htmlFor="notes" className="text-sm text-slate-300">
          Notes
        </label>
        <textarea
          id="notes"
          name="notes"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          rows={3}
          className="mt-2 rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2 text-slate-100 focus:border-blue-400 focus:outline-none"
          placeholder="Release channel, build provenance, extra context"
        />
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-400">
          {submission.status === 'uploading' && 'Uploading…'}
          {submission.status === 'success' && submission.message}
          {submission.status === 'error' && <span className="text-red-400">{submission.message}</span>}
        </div>
        <button
          type="submit"
          disabled={submission.status === 'uploading'}
          className="rounded-xl bg-blue-500 px-5 py-2 text-sm font-semibold text-white shadow hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submission.status === 'uploading' ? 'Uploading…' : 'Submit build'}
        </button>
      </div>
    </form>
  );
}
