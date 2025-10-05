import { useState } from 'react';
import Head from 'next/head';
import { apiClient } from '@/utils/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { accessToken } = await apiClient.login(email, password);
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', accessToken);
        window.location.href = '/';
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Sign In</title>
      </Head>
      <div className="relative min-h-screen p-4 overflow-hidden bg-gradient-to-b from-slate-950 via-slate-900 to-black flex items-center">
        {/* Decorative space glow */}
        <div className="pointer-events-none absolute -top-24 -left-24 h-72 w-72 rounded-full bg-cyan-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 -right-24 h-72 w-72 rounded-full bg-indigo-500/20 blur-3xl" />

        <div className="relative mx-auto flex w-full max-w-7xl items-center justify-center">
          <div className="grid w-full gap-12 md:grid-cols-2 items-center">
            {/* Left hero */}
            <div className="hidden md:flex flex-col justify-center text-slate-100 p-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300 w-max">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                Real-time Dust & PM2.5 Monitoring
              </div>
              <h1 className="mt-4 text-4xl font-bold leading-tight sm:text-5xl lg:text-6xl">
                Sign in to Dust Monitoring
              </h1>
              <p className="mt-4 max-w-xl text-slate-300 text-base sm:text-lg">
                NASA-inspired interface with clear visuals and modern design. Access your personalized air quality insights.
              </p>
              <div className="mt-8 flex flex-wrap gap-3 text-sm text-slate-300/80">
                <span className="rounded border border-white/10 bg-white/5 px-2 py-1">ECMWF CAMS</span>
                <span className="rounded border border-white/10 bg-white/5 px-2 py-1">NASA MODIS</span>
                <span className="rounded border border-white/10 bg-white/5 px-2 py-1">ERA5</span>
              </div>
            </div>

            {/* Right form card */}
            <div className="flex items-center justify-center">
              <form onSubmit={onSubmit} className="w-full max-w-xl rounded-2xl border border-white/10 bg-white/5 p-8 lg:p-10 shadow-[0_10px_50px_-12px_rgba(0,0,0,0.6)] backdrop-blur-md">
                <h2 className="text-2xl lg:text-3xl font-semibold text-white">Sign In</h2>
                {error && (
                  <div className="mt-4 rounded-md border border-red-400/30 bg-red-400/10 p-4 text-sm lg:text-base text-red-200">
                    {error}
                  </div>
                )}

                <label className="mt-6 block text-sm lg:text-base text-slate-300">Email</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-2 w-full rounded-xl border border-white/10 bg-white/10 px-4 py-3 text-white placeholder:text-slate-400 outline-none focus:border-cyan-400/70"
                  placeholder="you@example.com"
                />

                <label className="mt-4 block text-sm lg:text-base text-slate-300">Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-2 w-full rounded-xl border border-white/10 bg-white/10 px-4 py-3 text-white placeholder:text-slate-400 outline-none focus:border-cyan-400/70"
                  placeholder="Your password"
                />

                <button disabled={loading} className="mt-6 w-full rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-500 px-5 py-3 text-base lg:text-lg font-semibold text-white shadow-lg transition hover:from-cyan-400 hover:to-indigo-400 disabled:opacity-60">
                  {loading ? 'Submitting...' : 'Sign In'}
                </button>
                <p className="mt-4 text-center text-sm lg:text-base text-slate-300">
                  Don't have an account?{' '}
                  <a className="font-semibold text-cyan-300 hover:text-cyan-200" href="/register">Sign up</a>
                </p>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}


