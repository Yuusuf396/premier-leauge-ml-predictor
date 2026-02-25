import { ChevronDown, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { Team } from '../types/api';

interface TeamSelectorProps {
  side: 'Home' | 'Away';
  selectedTeam: Team | null;
  otherTeam: Team | null;
  teams: Team[];
  onSelect: (team: Team) => void;
  onClear: () => void;
}

export function TeamSelector({
  side,
  selectedTeam,
  otherTeam,
  teams,
  onSelect,
  onClear,
}: TeamSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement | null>(null);
  const searchRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) return;

    const onMouseDown = (event: MouseEvent) => {
      if (
        containerRef.current &&
        event.target instanceof Node &&
        !containerRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => searchRef.current?.focus(), 0);
    return () => window.clearTimeout(timer);
  }, [open]);

  const query = search.trim().toLowerCase();
  const filteredTeams = query
    ? teams.filter((team) => team.name.toLowerCase().includes(query))
    : teams;

  const showConflict =
    selectedTeam !== null &&
    otherTeam !== null &&
    selectedTeam.id === otherTeam.id;

  const handleSelect = (team: Team) => {
    onSelect(team);
    setSearch('');
    setOpen(false);
  };

  const cardBase =
    'w-full rounded-2xl p-5 transition-all duration-200 relative min-w-0';

  const emptyCardClass =
    'border-2 border-dashed border-[#1e2a6e] bg-[#121845] hover:border-[#097aff]/50 hover:bg-[#1a2260]/30 cursor-pointer';

  const selectedCardClass =
    'border-2 border-[#097aff] bg-[#1a2260] shadow-[0_0_0_3px_rgba(9,122,255,0.2)] cursor-pointer';

  return (
    <div className="relative min-w-0" ref={containerRef}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            setOpen((v) => !v);
          }
          if (event.key === 'Escape') {
            setOpen(false);
          }
        }}
        className={`${cardBase} ${
          selectedTeam ? selectedCardClass : emptyCardClass
        }`}
      >
        {selectedTeam ? (
          <>
            <div className="absolute right-2 top-2">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onClear();
                  setOpen(false);
                  setSearch('');
                }}
                aria-label={`Clear ${side} team`}
                className="rounded-md p-1 text-[#8891B8] transition-colors hover:text-white"
              >
                <X size={16} />
              </button>
            </div>

            <div
              className="mx-auto flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold text-white"
              style={{ backgroundColor: selectedTeam.color }}
            >
              {selectedTeam.name.charAt(0).toUpperCase()}
            </div>
            <p className="mt-2 truncate text-center text-sm font-bold text-white">
              {selectedTeam.name}
            </p>
            <p className="text-center text-xs text-[#8891B8]">
              {selectedTeam.short}
            </p>
          </>
        ) : (
          <>
            <div className="mx-auto h-10 w-10 rounded-full bg-[#1a2260]" />
            <p className="mt-3 text-center text-sm text-[#8891B8]">
              Select {side} team
            </p>
          </>
        )}

        <div className="pointer-events-none absolute bottom-2 right-2 text-[#8891B8]">
          <ChevronDown size={16} className={open ? 'rotate-180' : ''} />
        </div>
      </div>

      {showConflict && (
        <p className="mt-1 text-xs text-[#FF3B5C]">
          Must differ from {side === 'Home' ? 'Away' : 'Home'} team
        </p>
      )}

      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-2xl border border-[#1e2a6e] bg-[#121845] shadow-2xl">
          <div className="m-2">
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search teams..."
              className="w-full rounded-xl border-none bg-[#1a2260] px-4 py-2 text-sm text-white outline-none placeholder:text-[#8891B8]"
            />
          </div>
          <div className="max-h-64 overflow-y-auto">
            {filteredTeams.length === 0 ? (
              <div className="px-4 py-4 text-sm text-[#8891B8]">
                No teams found.
              </div>
            ) : (
              filteredTeams.map((team) => {
                const disabled = team.id === otherTeam?.id;
                return (
                  <button
                    key={team.id}
                    type="button"
                    onClick={() => handleSelect(team)}
                    disabled={disabled}
                    className={`flex h-14 w-full items-center gap-3 px-4 text-left transition-colors ${
                      disabled
                        ? 'cursor-not-allowed opacity-30'
                        : 'cursor-pointer hover:bg-[#1a2260]'
                    }`}
                  >
                    <div
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                      style={{ backgroundColor: team.color }}
                    >
                      {team.short}
                    </div>
                    <span className="truncate text-sm text-white">{team.name}</span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
