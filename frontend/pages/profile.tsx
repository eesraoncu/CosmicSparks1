import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useState, useMemo } from 'react';
import { apiClient } from '@/utils/api';
import { Province } from '@/types';

export default function ProfilePage() {
  const [email, setEmail] = useState<string | null>(null);
  const [provinceIds, setProvinceIds] = useState<number[]>([]);
  const [allProvinces, setAllProvinces] = useState<Province[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [me, provinces] = await Promise.all([
          apiClient.me(),
          apiClient.getProvinces(),
        ]);
        setEmail(me?.email || null);
        setProvinceIds(me?.province_ids || []);
        setAllProvinces(provinces || []);
      } catch (e) {
        setEmail(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const provinceNames = useMemo(() => {
    const map: Record<number, string> = {};
    allProvinces.forEach(p => { map[p.id] = p.name; });
    return provinceIds.map(id => map[id]).filter(Boolean);
  }, [provinceIds, allProvinces]);

  return (
    <>
      <Head>
        <title>Profile</title>
      </Head>
      <div className="min-h-screen space-bg">
        <div className="stars" />
        <div className="sticky top-0 z-50 backdrop-blur-md bg-white/5 border-b border-white/10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex justify-end">
            <Link href="/">
              <button className="bg-white/10 text-white px-4 py-2 rounded-lg border border-white/20 hover:bg-white/20">Home</button>
            </Link>
          </div>
        </div>
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-3xl font-bold text-white mb-6">Profile</h1>

          <div className="glass rounded-2xl p-6 mb-6 text-white">
            <h2 className="text-xl font-semibold mb-2">Account</h2>
            {loading ? (
              <p className="text-slate-300">Loading...</p>
            ) : (
              <p className="text-slate-300">Email: {email || 'guest@example.com'}</p>
            )}
          </div>

          <div className="glass rounded-2xl p-6 text-white">
            <h2 className="text-xl font-semibold mb-3">Preferences</h2>
            <ul className="text-slate-300 list-disc pl-5 space-y-1">
              <li>Alert level: Moderate and above</li>
              <li>Daily summary email: Enabled</li>
              <li>Units: μg/m³</li>
            </ul>
            <div className="mt-4">
              <h3 className="text-lg font-semibold">Selected Provinces</h3>
              {provinceNames.length > 0 ? (
                <ul className="list-disc pl-5 text-slate-300">
                  {provinceNames.map((name, idx) => (
                    <li key={idx}>{name}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-slate-400">No provinces selected.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
