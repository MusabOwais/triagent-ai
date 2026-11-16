import { useEffect, useState } from 'react'
import { api } from './api'
import Ambulance from './screens/Ambulance'
import Board from './screens/Board'
import Patient from './screens/Patient'
import { Btn, Chip, cx, toast, Toaster, useOptions } from './ui'

const read = () => location.hash.replace(/^#/, '') || 'board'

export default function App() {
  const [hash, setHash] = useState(read)
  const [epoch, setEpoch] = useState(0) // bumps after "Reset demo" so screens reload
  const { error: offline } = useOptions() // also lets the header pick up the data-source label
  const src = api.source
  useEffect(() => { const f = () => setHash(read()); addEventListener('hashchange', f); return () => removeEventListener('hashchange', f) }, [])

  const tab = hash === 'ambulance' ? 'ambulance' : 'board'
  const link = (to: string, label: string) => (
    <a href={`#${to}`} aria-current={tab === to && !hash.startsWith('p-') ? 'page' : undefined}
      className={cx('rounded-md px-3 py-2 text-[15px] font-semibold', tab === to && !hash.startsWith('p-') ? 'bg-ink text-white' : 'text-ink hover:bg-sunk')}>
      {label}
    </a>
  )

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 border-b border-line bg-surface">
        <div className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-x-5 gap-y-2 px-4 py-2.5">
          <a href="#board" className="text-[18px] font-extrabold tracking-tight">Relay Triage</a>
          <nav className="flex gap-1" aria-label="Screens">{link('ambulance', 'Ambulance')}{link('board', 'Bed board')}</nav>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <Chip tone={src.mock || offline || /missing|checking/.test(src.label) ? 'warn' : 'ok'}>{offline ? 'Backend not reachable' : src.label}</Chip>
            <Btn className="min-h-9 px-3 text-[14px]" onClick={async () => { await api.reset(); setEpoch(e => e + 1); location.hash = 'board'; toast('Demo reset to the example patients.') }}>
              Reset demo
            </Btn>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1240px] flex-1 px-4 py-5 sm:py-6" key={epoch}>
        {hash.startsWith('p-') ? <Patient id={hash.slice(2)} /> : tab === 'ambulance' ? <Ambulance /> : <Board />}
      </main>

      <footer className="border-t border-line bg-surface">
        <p className="mx-auto max-w-[1240px] px-4 py-3 text-[13px] text-muted">
          Proof of concept built at SacHacks HackRx. All patients are fictional. AI outputs are flags, not diagnoses. A real version would limit access by role (HIPAA).
        </p>
      </footer>
      <Toaster />
    </div>
  )
}
