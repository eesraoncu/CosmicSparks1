# Akıllı Pipeline Sistemi - Kullanım Kılavuzu

## 🎯 Genel Bakış

Bu sistem, Türkiye'nin **81 ili için otomatik olarak** en güncel veri kaynağını bulur ve eksik verileri akıllıca doldurur. Sistem:

1. ✅ Her il için **ayrı ayrı** en yakın gerçek veriyi bulur
2. ✅ Gerçek veri mevcutsa **pipeline'ı çalıştırır** (MODIS, CAMS, ERA5)
3. ✅ Gerçek veri yoksa **tahmin algoritması** ile 3 ay geriye giderek veri üretir
4. ✅ Tüm sonuçları **otomatik olarak veritabanına** kaydeder

## 🚀 Hızlı Başlangıç

### 1. Basit Kullanım (Önerilen)

Tüm illeri analiz et ve eksik verileri doldur:

```bash
python run_intelligent_pipeline.py
```

Bu komut:
- Son 90 gün içindeki verileri kontrol eder
- 7 günden eski verileri "güncel değil" olarak kabul eder
- Eksik tarihleri bulur ve doldurur
- Sonuçları veritabanına kaydeder

### 2. Sadece Analiz (Veri İşlemeden)

Mevcut veri durumunu kontrol et:

```bash
python run_intelligent_pipeline.py --analyze-only
```

Çıktı örneği:
```
================================================================================
DATA COVERAGE ANALYSIS
================================================================================
Total provinces: 81
Provinces with data: 65 (80.2%)
Provinces without data: 16
Provinces needing update: 32
Total missing records: 1,458
Oldest data: 2024-07-15
Newest data: 2024-10-03
================================================================================
```

### 3. Özelleştirilmiş Parametreler

```bash
# 30 gün geriye git (3 ay yerine)
python run_intelligent_pipeline.py --max-lookback 30

# 3 günden eski veriyi "eski" say (7 gün yerine)
python run_intelligent_pipeline.py --min-age 3

# Detaylı log kayıtları
python run_intelligent_pipeline.py --verbose

# Sonuçları JSON dosyasına kaydet
python run_intelligent_pipeline.py --export-report report.json
```

## 📊 API Kullanımı

### REST API Endpoint'leri

#### 1. Pipeline'ı Çalıştır

```http
POST /api/pipeline/run-intelligent?max_lookback_days=90&min_data_age_days=7
```

Yanıt:
```json
{
  "status": "success",
  "summary": {
    "initial_coverage_pct": 65.4,
    "final_coverage_pct": 98.8,
    "dates_processed_with_real_data": 12,
    "forecast_records_generated": 845,
    "total_records_added": 1817,
    "provinces_updated": 80
  }
}
```

#### 2. Sadece Analiz

```http
POST /api/pipeline/run-intelligent?analyze_only=true
```

#### 3. Detaylı Kapsama Analizi

```http
GET /api/pipeline/coverage-analysis?max_lookback_days=90
```

Yanıt:
```json
{
  "analysis": {
    "total_provinces": 81,
    "provinces_with_data": 65,
    "coverage_pct": 80.2
  },
  "provinces": {
    "1": {
      "name": "Adana",
      "latest_date": "2024-10-01",
      "days_old": 3,
      "has_recent_data": true
    },
    "6": {
      "name": "Ankara",
      "latest_date": "2024-09-15",
      "days_old": 19,
      "has_recent_data": false
    }
  }
}
```

## 🔧 Sistem Nasıl Çalışır?

### Adım 1: Veri Durumu Analizi

Sistem her il için ayrı ayrı kontrol yapar:

```
İl: Ankara
├─ Son gerçek veri: 2024-09-20 (14 gün önce)
├─ Durum: Güncel değil (>7 gün)
└─ Aksiyon: 2024-09-21'den bugüne kadar doldur
```

### Adım 2: Gerçek Veri Pipeline'ı

Eğer ham veri mevcutsa (MODIS, CAMS, ERA5):

```python
# Otomatik olarak çalıştırılır:
orchestrate_day("2024-10-01")
```

Bu işlem şunları yapar:
1. ✅ MODIS AOD verilerini işler
2. ✅ CAMS toz verilerini işler
3. ✅ ERA5 meteorolojik verilerini işler
4. ✅ İl bazında istatistik hesaplar
5. ✅ PM2.5 tahmini yapar
6. ✅ Veritabanına kaydeder

### Adım 3: Tahmin Sistemi

Eğer gerçek veri yoksa:

```python
# Her il için tahmin üretir
prediction = forecast_system.predict_pm25(province_id, date)
```

Tahmin şunları içerir:
- PM2.5 konsantrasyonu (μg/m³)
- Güven aralıkları (alt/üst)
- AOD değerleri
- Toz olayı tespiti
- Hava kalitesi kategorisi
- Belirsizlik metrikleri

### Adım 4: Veritabanına Kayıt

Tüm veriler `daily_stats` tablosuna kaydedilir:

```sql
INSERT INTO daily_stats (
  date, province_id, pm25, aod_mean, dust_event_detected,
  air_quality_category, data_quality_score, ...
) VALUES (...);
```

## 📈 Veri Kalite Göstergeleri

Sistemde 2 tür veri vardır:

### 1. Gerçek Veri
```json
{
  "data_quality_score": 0.95,
  "source": "MODIS + CAMS + ERA5",
  "pm25": 35.2,
  "pm25_uncertainty": 5.1
}
```

### 2. Tahmin Verisi
```json
{
  "data_quality_score": 0.7,
  "source": "Forecast Model",
  "pm25": 28.5,
  "pm25_uncertainty": 12.3
}
```

`data_quality_score` değeri:
- **0.7**: Tahmin verisi
- **0.7 - 1.0**: Gerçek veri (kapsama oranına göre)

## 🎯 Kullanım Senaryoları

### Senaryo 1: Günlük Otomatik Çalıştırma

Scheduler'a ekle (örn: cron):

```bash
# Her gün sabah 07:00'de çalıştır
0 7 * * * cd /dust-mvp && python run_intelligent_pipeline.py
```

### Senaryo 2: İlk Veri Yükleme

Sistemde hiç veri yoksa:

```bash
# 3 aylık geçmişi doldur
python run_intelligent_pipeline.py --max-lookback 90
```

### Senaryo 3: Acil Güncelleme

Sadece son 7 günü kontrol et:

```bash
python run_intelligent_pipeline.py --max-lookback 7 --min-age 1
```

### Senaryo 4: Belirli Bir Tarihi İşle

Belirli bir gün için pipeline çalıştır:

```bash
python -m src.orchestrate_day --date 2024-10-01
```

## 🔍 Sorun Giderme

### Problem: "No real data available"

**Çözüm**: Ham veri dosyalarını kontrol edin:

```bash
# MODIS verileri
ls data/raw/modis/20241001/

# CAMS verileri
ls data/raw/cams/cams_dust_analysis_20241001.nc

# ERA5 verileri
ls data/raw/era5/era5_20241001.nc
```

### Problem: "Forecast records not being saved"

**Çözüm**: Veritabanı bağlantısını kontrol edin:

```python
# test_db_connection.py
from src.database import db_manager

with db_manager.get_session() as session:
    print(f"Connection OK: {session.is_active}")
```

### Problem: "Coverage not improving"

**Çözüm**: Verbose log ile çalıştırın:

```bash
python run_intelligent_pipeline.py --verbose
```

Log dosyasını inceleyin: `intelligent_pipeline.log`

## 📝 Log Dosyaları

Sistem 2 log dosyası üretir:

### 1. intelligent_pipeline.log

Pipeline çalışma kayıtları:
```
2024-10-04 14:23:15 - INFO - Finding latest real data for each province...
2024-10-04 14:23:16 - INFO - Province Ankara (6): Latest data on 2024-09-20
2024-10-04 14:23:17 - INFO - Generating forecasts for 2024-09-21...
```

### 2. scheduler.log

Otomatik çalışma kayıtları (eğer scheduler kullanılıyorsa):
```
2024-10-04 07:00:00 - INFO - Starting scheduled pipeline run
2024-10-04 07:35:12 - INFO - Pipeline completed successfully
```

## 🌐 Frontend Entegrasyonu

Frontend'den API kullanımı:

```typescript
// utils/api.ts

export async function runIntelligentPipeline() {
  const response = await fetch('/api/pipeline/run-intelligent', {
    method: 'POST'
  });
  
  return response.json();
}

export async function getCoverageAnalysis() {
  const response = await fetch('/api/pipeline/coverage-analysis');
  return response.json();
}
```

```typescript
// components/AdminPanel.tsx

const handleRunPipeline = async () => {
  setLoading(true);
  
  try {
    const result = await runIntelligentPipeline();
    
    alert(`Pipeline başarılı!
      İşlenen tarihler: ${result.summary.dates_processed_with_real_data}
      Üretilen tahminler: ${result.summary.forecast_records_generated}
      Kapsama: ${result.summary.final_coverage_pct.toFixed(1)}%
    `);
  } catch (error) {
    alert('Hata: ' + error.message);
  } finally {
    setLoading(false);
  }
};
```

## 📊 Performans ve Sınırlamalar

### Performans Metrikleri

- **Analiz süresi**: ~2-5 saniye (81 il)
- **Tahmin üretimi**: ~0.1 saniye/kayıt
- **Gerçek veri işleme**: ~30-60 saniye/gün
- **Toplam süre**: 10-30 dakika (3 aylık eksik veriler için)

### Sınırlamalar

- **Max lookback**: 365 gün (performans nedeniyle)
- **Max forecasts**: 81 il × 90 gün = 7,290 kayıt (bir çalıştırmada)
- **API timeout**: 60 dakika (uzun işlemler için)

### Optimizasyon İpuçları

1. **Paralel işlem**: Worker pool kullanarak tarihleri paralel işleyin
2. **Batch insert**: Veritabanı kayıtlarını toplu ekleyin
3. **Cache**: Son analiz sonuçlarını cache'leyin
4. **Incremental**: Sadece son 7 günü günlük olarak güncelleyin

## 🔐 Güvenlik

### API Güvenliği

Pipeline endpoint'leri için authentication ekleyin:

```python
@app.post("/api/pipeline/run-intelligent")
async def run_intelligent_pipeline(
    current_user: User = Depends(get_current_user)
):
    # Sadece admin kullanıcılar çalıştırabilir
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Pipeline çalıştır...
```

### Rate Limiting

Aynı anda birden fazla pipeline çalışmasını engelleyin:

```python
# Redis veya memory cache kullanarak
if pipeline_is_running():
    raise HTTPException(status_code=429, detail="Pipeline already running")
```

## 📞 Destek ve Katkı

### Sorun Bildirme

1. Log dosyalarını toplayın
2. Hata mesajını kopyalayın
3. Kullanılan komut ve parametreleri belirtin
4. GitHub issue oluşturun

### Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun
3. Test edin
4. Pull request gönderin

## 📚 İlgili Dosyalar

- `src/intelligent_pipeline_orchestrator.py` - Ana orchestrator sınıfı
- `src/forecast_system.py` - Tahmin algoritmaları
- `src/orchestrate_day.py` - Günlük pipeline
- `src/api.py` - REST API endpoints
- `run_intelligent_pipeline.py` - CLI arayüzü

## ✅ Kontrol Listesi

Pipeline çalıştırmadan önce:

- [ ] Veritabanı çalışıyor mu?
- [ ] `config/params.yaml` ayarları doğru mu?
- [ ] Ham veri dizinleri mevcut mu?
- [ ] Disk alanı yeterli mi? (en az 5GB)
- [ ] API anahtarları geçerli mi? (CAMS, MODIS)

---

**Version**: 1.0.0  
**Son Güncelleme**: 2024-10-04  
**Lisans**: MIT

