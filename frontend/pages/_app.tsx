import type { AppProps } from 'next/app';
import '../styles/globals.css';
import 'leaflet/dist/leaflet.css';
import { useEffect } from 'react';
import api from '@/utils/api';

export default function App({ Component, pageProps }: AppProps) {
  // Simple session check on app start (optional)
  useEffect(() => {
    // Touch /auth/me if token exists to validate
    try {
      if (typeof window !== 'undefined' && localStorage.getItem('auth_token')) {
        // fire and forget
        fetch((api as any).defaults.baseURL + '/api/auth/me', {
          headers: { Authorization: 'Bearer ' + localStorage.getItem('auth_token') },
        }).catch(() => {});
      }
    } catch {}
  }, []);
  return <Component {...pageProps} />;
}


