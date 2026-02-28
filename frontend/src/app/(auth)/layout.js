/**
 * Auth group layout — split screen.
 * Left: brand panel  |  Right: form card
 */
export default function AuthLayout({ children }) {
  return (
    <div className="min-h-screen flex">
      {/* ── Left brand panel ── */}
      <div
        className="hidden lg:flex lg:w-[44%] flex-col justify-between p-12"
        style={{ background: "linear-gradient(145deg, #1e3a8a 0%, #1a56db 60%, #3b82f6 100%)" }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="white" />
              <path d="M2 17l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <path d="M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <span className="text-white font-bold text-xl tracking-tight">BharatCompliance</span>
        </div>

        {/* Hero text */}
        <div>
          <h2 className="text-white text-4xl font-bold leading-tight mb-4">
            Smart compliance for<br />India&apos;s businesses
          </h2>
          <p className="text-blue-200 text-base leading-relaxed max-w-xs">
            Manage GST filings, track deadlines, and keep clients compliant — all from one platform.
          </p>

          {/* Trust badges */}
          <div className="mt-10 space-y-3">
            {[
              { icon: "✓", text: "GST & Advance Tax deadline tracking" },
              { icon: "✓", text: "WhatsApp-first for micro-businesses" },
              { icon: "✓", text: "Real-time compliance scoring" },
            ].map((b) => (
              <div key={b.text} className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-white text-xs font-bold">
                  {b.icon}
                </div>
                <span className="text-blue-100 text-sm">{b.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <p className="text-blue-300 text-xs">
          © 2026 BharatCompliance · Built for Bharat
        </p>
      </div>

      {/* ── Right form area ── */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 bg-slate-50">
        {/* Mobile logo */}
        <div className="lg:hidden flex items-center gap-2 mb-8">
          <div className="w-8 h-8 bg-blue-700 rounded-lg flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="white" />
              <path d="M2 17l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <span className="text-blue-800 font-bold text-lg">BharatCompliance</span>
        </div>

        <div className="w-full max-w-[420px]">
          {children}
        </div>
      </div>
    </div>
  );
}
