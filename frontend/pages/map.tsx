import dynamic from 'next/dynamic';
import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { apiClient } from '@/utils/api';
import { Province, DailyStats } from '@/types';
import { useRouter } from 'next/router';

const DustMap = dynamic(() => import('@/components/DustMap'), { ssr: false });

export default function MapPage() {
  const router = useRouter();
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [stats, setStats] = useState<DailyStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProvince, setSelectedProvince] = useState<number | undefined>();
  const openDropdown = router.query.open === 'dropdown';

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [p, s] = await Promise.all([
          apiClient.getProvinces(),
          apiClient.getCurrentStats(),
        ]);
        setProvinces(p);
        setStats(s);
      } catch (e) {
        setError('Failed to load map data');
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const options = useMemo(() => provinces.map(p => ({ value: p.id, label: p.name })), [provinces]);

  return (
    <>
      <Head>
        <title>Live Map</title>
      </Head>
      <div className="min-h-screen space-bg">
        <div className="stars" />
        {/* Top toolbar */}
        <div className="sticky top-0 z-50 backdrop-blur-md bg-white/5 border-b border-white/10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
            <Link href="/" className="text-lg font-semibold bg-gradient-to-r from-cyan-300 to-indigo-400 bg-clip-text text-transparent">Cosmic Sparks</Link>
            <div className="flex items-center gap-2">
              <Link href="/">
                <button className="bg-white/10 text-white px-3 py-1.5 rounded-lg border border-white/20 hover:bg-white/20">Home</button>
              </Link>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-2xl sm:text-3xl font-bold text-white mb-4">Live Map</h1>
          {error && (
            <div className="rounded-lg bg-red-500/10 text-red-100 border border-red-400/30 p-3 mb-4">{error}</div>
          )}
          <div className="mb-4 flex items-center gap-3 glass rounded-lg p-3 text-white">
            <label className="text-sm text-slate-300">Select Province</label>
            <select
              autoFocus={openDropdown}
              value={selectedProvince ?? ''}
              onChange={(e) => setSelectedProvince(Number(e.target.value))}
              className="bg-white/10 text-white border border-white/20 rounded px-3 py-2 outline-none hover:bg-white/15 [&>option]:text-slate-900 [&>option]:bg-white"
            >
              <option value="" disabled className="text-slate-500 bg-white">Select...</option>
              {options.map(o => (
                <option key={o.value} value={o.value} className="text-slate-900 bg-white">{o.label}</option>
              ))}
            </select>
          </div>
          <div className="glass rounded-2xl overflow-hidden">
            <div className="h-[70vh]">
              <DustMap 
                provinces={provinces}
                stats={stats}
                height="70vh"
                interactive={true}
                selectedProvince={selectedProvince}
                onProvinceSelect={(id) => setSelectedProvince(id)}
              />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}


