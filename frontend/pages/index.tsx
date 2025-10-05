import Sidebar from "../components/Sidebar";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";

export default function Home() {
  const router = useRouter();
  const slides = useMemo(() => [
    { id: 1, img: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1920&auto=format&fit=crop" },
    { id: 2, img: "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?q=80&w=1920&auto=format&fit=crop" },
    { id: 3, img: "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?q=80&w=1920&auto=format&fit=crop" },
  ], []);

  const [current, setCurrent] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setCurrent((i) => (i + 1) % slides.length), 6000);
    return () => clearInterval(id);
  }, [slides.length]);

  const go = (i: number) => setCurrent((prev) => (i + 1) % slides.length);

  return (
    <div className="flex min-h-screen space-bg overflow-hidden">
      <div className="stars" />
      <Sidebar onChangeView={() => {}} />
      <div className="flex-1 p-4 sm:p-6 overflow-auto relative">
        {/* Floating auth buttons - no strip */}
        <div className="absolute right-6 top-4 z-40 flex gap-2">
          <Link href="/login">
            <button className="bg-white/10 text-white px-5 py-2 rounded-lg border border-white/20 hover:bg-white/20">Login</button>
          </Link>
          <Link href="/register">
            <button className="bg-white/10 text-white px-5 py-2 rounded-lg border border-white/20 hover:bg-white/20">Register</button>
          </Link>
        </div>

        {/* Full viewport center wrapper */}
        <div className="w-full" style={{minHeight: 'calc(100vh - 60px)'}}>
          <div className="mx-auto" style={{maxWidth: '95%'}}>
            <div className="relative w-full rounded-2xl overflow-hidden glass flex items-center justify-center" style={{height: '60vh', minHeight: 520}}>
              {slides.map((s, i) => (
                <div key={s.id} className={`absolute inset-0 transition-opacity duration-700 ease-in-out ${i === current ? 'opacity-100' : 'opacity-0'}`} style={{
                  backgroundImage: `linear-gradient(180deg, rgba(2,6,23,0.35) 0%, rgba(2,6,23,0.25) 50%, rgba(2,6,23,0.45) 100%), url('${s.img}')`,
                  backgroundSize: 'cover', backgroundPosition: 'center'
                }} />
              ))}

              <div className="relative text-center px-8">
                <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold drop-shadow-lg bg-gradient-to-r from-cyan-300 to-indigo-400 bg-clip-text text-transparent">
                  Smart Dust & Air Quality Monitoring
                </h1>
                <p className="mt-5 text-slate-200 max-w-4xl text-lg mx-auto">
                  Real-time dust storms and PM2.5 tracking across Turkey powered by NASA satellite data and advanced modeling.
                </p>
                <Link href="/map" className="mt-7 inline-block">
                  <button className="bg-gradient-to-r from-cyan-500 to-indigo-500 hover:from-cyan-400 hover:to-indigo-400 text-white px-7 py-3 rounded-lg shadow">
                    View Live Map
                  </button>
                </Link>
              </div>

              <div className="absolute bottom-5 left-1/2 -translate-x-1/2 flex items-center gap-2">
                <button onClick={() => go(current - 1)} className="px-2 py-1 rounded bg-black/30 text-white border border-white/20 hover:bg-black/40">‹</button>
                {slides.map((_, i) => (
                  <button key={i} onClick={() => setCurrent(i)} className={`w-2.5 h-2.5 rounded-full ${i === current ? 'bg-white' : 'bg-white/60'}`} />
                ))}
                <button onClick={() => go(current + 1)} className="px-2 py-1 rounded bg-black/30 text-white border border-white/20 hover:bg-black/40">›</button>
              </div>
            </div>

            {/* Feature cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
              <div className="glass rounded-xl p-6 text-white text-center">
                <div className="text-2xl mb-2">🛰️</div>
                <div className="font-semibold mb-1">Satellite Data</div>
                <p className="text-slate-300 text-sm">Powered by NASA MODIS & ECMWF for accurate real-time dust detection.</p>
              </div>
              <div className="glass rounded-xl p-6 text-white text-center">
                <div className="text-2xl mb-2">🔔</div>
                <div className="font-semibold mb-1">Personal Alerts</div>
                <p className="text-slate-300 text-sm">Customized alerts based on your location and health thresholds.</p>
              </div>
              <div className="glass rounded-xl p-6 text-white text-center">
                <div className="text-2xl mb-2">📊</div>
                <div className="font-semibold mb-1">Analytics</div>
                <p className="text-slate-300 text-sm">Detailed PM2.5, AOD, and meteorological trend analysis.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


