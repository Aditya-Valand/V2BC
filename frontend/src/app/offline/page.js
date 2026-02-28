"use client";

export default function OfflinePage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 px-6 text-center">
      <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mb-5">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M1 1l22 22M16.72 11.06A10.94 10.94 0 0 1 19 12.55M5 12.55a10.94 10.94 0 0 1 5.17-2.39M10.71 5.05A16 16 0 0 1 22.56 9M1.42 9a15.91 15.91 0 0 1 4.7-2.88M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01" stroke="#1d4ed8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <h1 className="text-xl font-bold text-slate-800 mb-2">No Internet Connection</h1>
      <p className="text-sm text-slate-500 mb-6 max-w-xs leading-relaxed">
        You are offline. Please check your connection and try again.
        Your data is safe and will sync when you reconnect.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="bg-blue-700 text-white font-semibold px-6 py-3 rounded-xl hover:bg-blue-800 active:scale-95 transition-all"
      >
        Try Again
      </button>
    </div>
  );
}
