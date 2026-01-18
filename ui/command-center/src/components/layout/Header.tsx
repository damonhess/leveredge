'use client';

import { Clock, DollarSign, Calendar, Activity } from 'lucide-react';
import { useEffect, useState } from 'react';

export function Header() {
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    setTime(new Date().toLocaleTimeString());
    const interval = setInterval(() => {
      setTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const daysToLaunch = Math.ceil(
    (new Date('2026-03-01').getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );

  return (
    <header className="h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-6">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-sm">
          <Calendar size={16} className="text-amber-400" />
          <span className="text-slate-400">Launch in</span>
          <span className="font-bold text-amber-400">{daysToLaunch} days</span>
        </div>

        <div className="flex items-center gap-2 text-sm">
          <DollarSign size={16} className="text-green-400" />
          <span className="text-slate-400">Portfolio</span>
          <span className="font-bold text-green-400">$58K - $117K</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <Activity size={16} className="text-cyan-400" />
          <span className="text-slate-400">Agents</span>
          <span className="font-bold text-cyan-400">40+</span>
        </div>

        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Clock size={16} />
          <span>{time}</span>
        </div>
      </div>
    </header>
  );
}
