import UploadForm from './components/UploadForm';
import RecentRuns from './components/RecentRuns';

export default function Home() {
  return (
    <section className="w-full max-w-4xl space-y-10">
      <UploadForm />
      <RecentRuns />
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 text-sm text-slate-300">
        <h2 className="text-lg font-semibold text-slate-100">How it works</h2>
        <ol className="mt-3 list-decimal space-y-1 pl-4">
          <li>Upload an IPA or APK/AAB. Metadata helps link to capture runs.</li>
          <li>Files land in <code>storage/uploads/&lt;timestamp&gt;</code> on the server, and logs live in <code>storage/logs/</code>.</li>
          <li>The automation pipeline runs automatically (configurable via <code>AUTO_RUN_PIPELINE</code>).</li>
        </ol>
      </div>
    </section>
  );
}
