import { useEffect, useState } from 'react';
import Head from 'next/head';
import { apiClient } from '@/utils/api';
import { Province } from '@/types';
import Select from 'react-select';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        // 1) Try relative path (Next.js rewrite to backend)
        const r1 = await fetch('/api/provinces/');
        if (r1.ok) {
          const d = await r1.json();
          if (Array.isArray(d) && d.length) { setProvinces(d); return; }
        }
      } catch {}
      try {
        // 2) Try axios client baseURL
        const list = await apiClient.getProvinces();
        if (Array.isArray(list) && list.length) { setProvinces(list); return; }
      } catch {}
      try {
        // 3) Try explicit base URL
        const base = (require('@/utils/api').default as any).defaults.baseURL || '';
        const r = await fetch(`${base}/api/provinces/`);
        const data = await r.json();
        setProvinces(Array.isArray(data) ? data : []);
      } catch { setProvinces([]); }
    };
    load();
  }, []);

  const provinceOptions = provinces.map(p => ({ value: p.id, label: p.name }));

  // Dark theme styles for react-select to match input backgrounds
  const selectStyles = {
    control: (base: any, state: any) => ({
      ...base,
      backgroundColor: 'rgba(255,255,255,0.06)',
      borderColor: state.isFocused ? 'rgba(34,211,238,0.7)' : 'rgba(255,255,255,0.1)',
      boxShadow: 'none',
      borderRadius: 12,
      minHeight: 44,
      ':hover': { borderColor: 'rgba(34,211,238,0.7)' },
    }),
    menu: (base: any) => ({
      ...base,
      backgroundColor: 'rgba(2,6,23,0.95)',
      border: '1px solid rgba(255,255,255,0.1)',
      backdropFilter: 'blur(6px)',
      borderRadius: 12,
      overflow: 'hidden',
    }),
    menuList: (base: any) => ({
      ...base,
      padding: 6,
      backgroundColor: 'transparent',
    }),
    option: (base: any, state: any) => ({
      ...base,
      backgroundColor: state.isSelected
        ? 'rgba(34,211,238,0.35)'
        : state.isFocused
        ? 'rgba(34,211,238,0.15)'
        : 'transparent',
      color: 'white',
      ':active': { backgroundColor: 'rgba(34,211,238,0.25)' },
    }),
    placeholder: (base: any) => ({ ...base, color: 'rgb(148,163,184)' }),
    singleValue: (base: any) => ({ ...base, color: 'white' }),
    input: (base: any) => ({ ...base, color: 'white' }),
    multiValue: (base: any) => ({ ...base, backgroundColor: 'rgba(255,255,255,0.12)' }),
    multiValueLabel: (base: any) => ({ ...base, color: 'white' }),
    multiValueRemove: (base: any) => ({
      ...base,
      color: 'white',
      ':hover': { backgroundColor: 'rgba(239,68,68,0.5)', color: 'white' },
    }),
    dropdownIndicator: (base: any) => ({ ...base, color: 'rgb(148,163,184)' }),
    indicatorSeparator: (base: any) => ({ ...base, backgroundColor: 'rgba(255,255,255,0.1)' }),
    menuPortal: (base: any) => ({ ...base, zIndex: 9999 }),
  } as const;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null); setMessage(null);
    if (selected.length === 0) { setError('Select at least one province'); return; }
    setLoading(true);
    try {
      await apiClient.register({ email, password, province_ids: selected, health_group: 'general' });
      setMessage('Registration created. Verification email sent.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed');
    } finally { setLoading(false); }
  };

  return (
    <>
      <Head><title>Sign Up</title></Head>
      <div className="relative min-h-screen p-6 overflow-hidden bg-gradient-to-b from-slate-950 via-slate-900 to-black flex items-center">
        <div className="pointer-events-none absolute -top-24 -left-24 h-72 w-72 rounded-full bg-cyan-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 -right-24 h-72 w-72 rounded-full bg-indigo-500/20 blur-3xl" />

        <div className="relative mx-auto flex w-full max-w-7xl items-center justify-center">
          <div className="grid w-full gap-12 md:grid-cols-2 items-center">
            {/* Left hero */}
            <div className="hidden md:flex flex-col justify-center text-slate-100 p-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300 w-max">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                Create your alert profile
              </div>
              <h1 className="mt-4 text-4xl font-bold leading-tight sm:text-5xl lg:text-6xl">
                Sign up for Dust Alerts
              </h1>
              <p className="mt-4 max-w-xl text-slate-300 text-base sm:text-lg">
                Get personalized notifications based on PM2.5 and dust events across Turkey.
              </p>
              <div className="mt-8 flex flex-wrap gap-3 text-sm text-slate-300/80">
                <span className="rounded border border-white/10 bg-white/5 px-2 py-1">Email Alerts</span>
                <span className="rounded border border-white/10 bg-white/5 px-2 py-1">Province Tracking</span>
                <span className="rounded border border-white/10 bg-white/5 px-2 py-1">Health Groups</span>
              </div>
            </div>

            {/* Right form card */}
            <div className="flex items-center justify-center">
              <form onSubmit={onSubmit} className="w-full max-w-xl rounded-2xl border border-white/10 bg-white/5 p-8 lg:p-10 shadow-[0_10px_50px_-12px_rgba(0,0,0,0.6)] backdrop-blur-md">
                <h2 className="text-2xl lg:text-3xl font-semibold text-white">Create Account</h2>
                {message && <div className="mt-4 rounded-md border border-emerald-400/30 bg-emerald-400/10 p-4 text-sm lg:text-base text-emerald-200">{message}</div>}
                {error && <div className="mt-4 rounded-md border border-red-400/30 bg-red-400/10 p-4 text-sm lg:text-base text-red-200">{error}</div>}

                <label className="mt-6 block text-sm lg:text-base text-slate-300">Email</label>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="mt-2 w-full rounded-xl border border-white/10 bg-white/10 px-4 py-3 text-white placeholder:text-slate-400 outline-none focus:border-cyan-400/70" placeholder="you@example.com" />

                <label className="mt-4 block text-sm lg:text-base text-slate-300">Password</label>
                <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="mt-2 w-full rounded-xl border border-white/10 bg-white/10 px-4 py-3 text-white placeholder:text-slate-400 outline-none focus:border-cyan-400/70" placeholder="Your password" />

                <div className="mt-4">
                  <div className="text-sm lg:text-base text-slate-300 mb-2">Provinces you want to follow</div>
                  <Select
                    classNamePrefix="select"
                    isMulti
                    options={provinceOptions}
                    value={provinceOptions.filter(o => selected.includes(o.value))}
                    onChange={(vals) => setSelected((vals as any[]).map(v => v.value))}
                    placeholder="Select provinces..."
                    styles={selectStyles as any}
                    menuPortalTarget={typeof window !== 'undefined' ? document.body : undefined}
                  />
                  {provinces.length === 0 && (
                    <div className="text-xs lg:text-sm text-slate-300/80 mt-1">Failed to load provinces. Ensure backend is running.</div>
                  )}
                </div>

                <button disabled={loading} className="mt-6 w-full rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-500 px-5 py-3 text-base lg:text-lg font-semibold text-white shadow-lg transition hover:from-cyan-400 hover:to-indigo-400 disabled:opacity-60">{loading ? 'Submitting...' : 'Create Account'}</button>
                <p className="mt-4 text-center text-sm lg:text-base text-slate-300">Already have an account? <a className="font-semibold text-cyan-300 hover:text-cyan-200" href="/login">Sign in</a></p>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}


