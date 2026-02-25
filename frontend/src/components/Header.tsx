export function Header() {
  return (
    <header className="sticky top-0 z-50 h-14 border-b border-[#1e2a6e] bg-[#0c0f29]/90 backdrop-blur-md">
      <div className="mx-auto flex h-full max-w-[420px] items-center justify-between px-4">
        <div className="text-lg font-bold tracking-tight">
          <span className="text-white">Data</span>
          <span className="text-[#097aff]">Derby</span>
        </div>
        <div className="rounded-full border border-[#1e2a6e] bg-[#121845] px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[#8891B8]">
          PL Predictor
        </div>
      </div>
    </header>
  );
}
