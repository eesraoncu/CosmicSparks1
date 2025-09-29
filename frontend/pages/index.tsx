import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { 
  CloudIcon, 
  ExclamationTriangleIcon, 
  MapPinIcon,
  ChartBarIcon,
  BellIcon,
  ArrowRightIcon 
} from '@heroicons/react/24/outline';
import { apiClient, dataUtils } from '@/utils/api';
import { Province, DailyStats } from '@/types';
import DustMap from '@/components/DustMap';
import ProvinceCard from '@/components/ProvinceCard';
import AlertsOverview from '@/components/AlertsOverview';
import StatsChart from '@/components/StatsChart';

export default function Home() {
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [currentStats, setCurrentStats] = useState<DailyStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [provincesData, statsData] = await Promise.all([
          apiClient.getProvinces(),
          apiClient.getCurrentStats()
        ]);
        
        setProvinces(provincesData);
        setCurrentStats(statsData);
      } catch (err) {
        setError('Veri yüklenirken bir hata oluştu');
        console.error('Error fetching data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Get featured provinces with highest PM2.5 or dust activity
  const getFeaturedProvinces = () => {
    return currentStats
      .filter(stat => stat.pm25 !== undefined)
      .sort((a, b) => (b.pm25 || 0) - (a.pm25 || 0))
      .slice(0, 6)
      .map(stat => {
        const province = provinces.find(p => p.id === stat.province_id);
        return province ? { ...province, stats: stat } : null;
      })
      .filter(Boolean) as Array<Province & { stats: DailyStats }>;
  };

  // Get overall system status
  const getSystemStatus = () => {
    if (!currentStats.length) return 'Veri bekleniyor';
    
    const highRiskCount = currentStats.filter(stat => 
      (stat.pm25 || 0) > 75 || stat.dust_event_detected
    ).length;
    
    if (highRiskCount > 0) return `${highRiskCount} ilde yüksek risk`;
    
    const moderateRiskCount = currentStats.filter(stat => 
      (stat.pm25 || 0) > 35
    ).length;
    
    if (moderateRiskCount > 0) return `${moderateRiskCount} ilde orta risk`;
    
    return 'Genel olarak iyi hava kalitesi';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-gray-600">Veriler yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Türkiye Toz İzleme ve Uyarı Sistemi</title>
        <meta name="description" content="Gerçek zamanlı toz izleme ve sağlık uyarıları" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div className="flex items-center">
                <CloudIcon className="h-8 w-8 text-primary-600 mr-3" />
                <div>
                  <h1 className="text-xl font-bold text-gray-900">
                    Türkiye Toz İzleme Sistemi
                  </h1>
                  <p className="text-sm text-gray-500">
                    Gerçek zamanlı hava kalitesi ve sağlık uyarıları
                  </p>
                </div>
              </div>
              
              <nav className="flex items-center space-x-4">
                <Link href="/map" className="text-gray-600 hover:text-primary-600 flex items-center">
                  <MapPinIcon className="h-5 w-5 mr-1" />
                  Harita
                </Link>
                <Link href="/stats" className="text-gray-600 hover:text-primary-600 flex items-center">
                  <ChartBarIcon className="h-5 w-5 mr-1" />
                  İstatistikler
                </Link>
                <Link href="/alerts" className="btn-primary">
                  <BellIcon className="h-5 w-5 mr-2" />
                  Uyarı Al
                </Link>
              </nav>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <section className="bg-gradient-to-r from-primary-600 to-primary-800 text-white py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div>
                <h2 className="text-4xl font-bold mb-6">
                  Sağlığınızı Koruyan Akıllı Uyarı Sistemi
                </h2>
                <p className="text-xl mb-8 text-primary-100">
                  NASA uydu verileri kullanarak Türkiye genelinde toz fırtınalarını takip ediyor, 
                  kişiselleştirilmiş sağlık uyarıları gönderiyoruz.
                </p>
                
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link href="/register" className="btn-secondary text-primary-600">
                    Ücretsiz Kaydol
                    <ArrowRightIcon className="h-5 w-5 ml-2" />
                  </Link>
                  <Link href="/map" className="text-white hover:text-primary-200 flex items-center">
                    <MapPinIcon className="h-5 w-5 mr-2" />
                    Canlı Haritayı Gör
                  </Link>
                </div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Bugünkü Durum</h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span>Sistem Durumu:</span>
                    <span className="font-medium">{getSystemStatus()}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>İzlenen İl Sayısı:</span>
                    <span className="font-medium">{provinces.length}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>Veri Güncelliği:</span>
                    <span className="font-medium">
                      {new Date().toLocaleDateString('tr-TR')}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Current Alerts */}
        {error ? (
          <section className="py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="alert alert-error">
                <ExclamationTriangleIcon className="h-6 w-6 mr-2" />
                {error}
              </div>
            </div>
          </section>
        ) : (
          <AlertsOverview stats={currentStats} provinces={provinces} />
        )}

        {/* Featured Provinces */}
        <section className="py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-2xl font-bold text-gray-900">
                Öne Çıkan İller
              </h2>
              <Link href="/provinces" className="text-primary-600 hover:text-primary-700 flex items-center">
                Tümünü Gör
                <ArrowRightIcon className="h-5 w-5 ml-1" />
              </Link>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {getFeaturedProvinces().map((province) => (
                <ProvinceCard 
                  key={province.id} 
                  province={province} 
                  stats={province.stats}
                />
              ))}
            </div>
          </div>
        </section>

        {/* Map Preview */}
        <section className="py-12 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center mb-8">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  Canlı Toz Haritası
                </h2>
                <p className="text-gray-600 mt-2">
                  Türkiye genelinde anlık hava kalitesi durumu
                </p>
              </div>
              <Link href="/map" className="btn-primary">
                Tam Ekran Harita
              </Link>
            </div>
            
            <div className="h-96 rounded-lg overflow-hidden shadow-lg">
              <DustMap 
                provinces={provinces}
                stats={currentStats}
                height="24rem"
                interactive={false}
              />
            </div>
          </div>
        </section>

        {/* Statistics Overview */}
        <section className="py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center mb-8">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  Haftalık Trend
                </h2>
                <p className="text-gray-600 mt-2">
                  Son 7 günün hava kalitesi değişimi
                </p>
              </div>
              <Link href="/stats" className="btn-secondary">
                Detaylı İstatistikler
              </Link>
            </div>
            
            <StatsChart 
              data={getFeaturedProvinces().slice(0, 5).map(p => ({
                province: p.name,
                pm25: p.stats?.pm25 || 0,
                aod: p.stats?.aod_mean || 0,
                dustDetected: p.stats?.dust_event_detected || false
              }))}
            />
          </div>
        </section>

        {/* Features */}
        <section className="py-16 bg-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Neden Bizim Sistemi Tercih Etmelisiniz?
              </h2>
              <p className="text-lg text-gray-600 max-w-3xl mx-auto">
                NASA uydu teknolojisi ve gelişmiş modelleme ile desteklenen 
                güvenilir hava kalitesi izleme sistemi
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
              <div className="text-center">
                <div className="bg-primary-100 rounded-full p-4 w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                  <CloudIcon className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Uydu Teknolojisi</h3>
                <p className="text-gray-600">
                  NASA MODIS ve ECMWF verilerini kullanarak gerçek zamanlı takip
                </p>
              </div>
              
              <div className="text-center">
                <div className="bg-primary-100 rounded-full p-4 w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                  <BellIcon className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Kişisel Uyarılar</h3>
                <p className="text-gray-600">
                  Sağlık durumunuza özel threshold'lar ve öneri mesajları
                </p>
              </div>
              
              <div className="text-center">
                <div className="bg-primary-100 rounded-full p-4 w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                  <MapPinIcon className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-lg font-semibold mb-2">İl Bazında Takip</h3>
                <p className="text-gray-600">
                  İstediğiniz illeri seçerek o bölgeler için özel uyarılar alın
                </p>
              </div>
              
              <div className="text-center">
                <div className="bg-primary-100 rounded-full p-4 w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                  <ChartBarIcon className="h-8 w-8 text-primary-600" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Detaylı Analiz</h3>
                <p className="text-gray-600">
                  PM2.5, AOD ve meteorolojik verilerin kapsamlı analizi
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16 bg-primary-600">
          <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold text-white mb-4">
              Sağlığınızı Korumak İçin Hemen Başlayın
            </h2>
            <p className="text-xl text-primary-100 mb-8">
              Ücretsiz kaydolun, il tercihlerinizi belirleyin ve kişiselleştirilmiş 
              toz uyarıları almaya başlayın.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/register" className="btn-secondary text-primary-600">
                Ücretsiz Kaydol
              </Link>
              <Link href="/about" className="text-white hover:text-primary-200 border border-white/30 px-6 py-3 rounded-md">
                Sistem Hakkında
              </Link>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="bg-gray-800 text-white py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
              <div className="col-span-2">
                <div className="flex items-center mb-4">
                  <CloudIcon className="h-8 w-8 text-primary-400 mr-3" />
                  <span className="text-xl font-bold">Toz İzleme Sistemi</span>
                </div>
                <p className="text-gray-300 mb-4">
                  NASA Space Apps Challenge 2024 kapsamında geliştirilen 
                  Türkiye toz izleme ve sağlık uyarı sistemi.
                </p>
                <p className="text-gray-400 text-sm">
                  Veri Kaynakları: NASA MODIS, ECMWF CAMS, ERA5
                </p>
              </div>
              
              <div>
                <h3 className="font-semibold mb-4">Sayfalar</h3>
                <ul className="space-y-2 text-gray-300">
                  <li><Link href="/map" className="hover:text-white">Canlı Harita</Link></li>
                  <li><Link href="/stats" className="hover:text-white">İstatistikler</Link></li>
                  <li><Link href="/alerts" className="hover:text-white">Uyarı Sistemi</Link></li>
                  <li><Link href="/about" className="hover:text-white">Hakkında</Link></li>
                </ul>
              </div>
              
              <div>
                <h3 className="font-semibold mb-4">Destek</h3>
                <ul className="space-y-2 text-gray-300">
                  <li><Link href="/help" className="hover:text-white">Yardım</Link></li>
                  <li><Link href="/privacy" className="hover:text-white">Gizlilik</Link></li>
                  <li><Link href="/terms" className="hover:text-white">Kullanım Şartları</Link></li>
                  <li><Link href="/contact" className="hover:text-white">İletişim</Link></li>
                </ul>
              </div>
            </div>
            
            <div className="border-t border-gray-700 pt-8 mt-8 text-center text-gray-400">
              <p>&copy; 2024 Türkiye Toz İzleme Sistemi. NASA Space Apps Challenge Projesi.</p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}
