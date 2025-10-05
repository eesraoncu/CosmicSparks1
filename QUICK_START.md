# 🚀 Hızlı Başlangıç - Akıllı Pipeline Sistemi

## Sistem Nedir?

81 il için **otomatik olarak**:
1. ✅ En güncel gerçek veriyi bulur
2. ✅ Eksik verileri tahmin algoritması ile doldurur
3. ✅ Sonuçları veritabanına kaydeder

## 1 Dakikada Çalıştırma

### Adım 1: Test Et

```bash
# Testleri çalıştır (veritabanı bağlantısı kontrolü)
python test_intelligent_pipeline.py
```

Tüm testler başarılı olmalı (7/7 PASS).

### Adım 2: Durumu Kontrol Et

```bash
# Mevcut veri durumunu gör
python run_intelligent_pipeline.py --analyze-only
```

Çıktı:
```
Total provinces: 81
Provinces with data: 45 (55.6%)
Provinces needing update: 36
Total missing records: 2,156
```

### Adım 3: Sistemi Çalıştır

```bash
# Tüm eksik verileri doldur
python run_intelligent_pipeline.py
```

Bu komut:
- ✅ Son 90 günü kontrol eder
- ✅ Gerçek veri varsa pipeline çalıştırır
- ✅ Yoksa tahmin üretir
- ✅ Veritabanına kaydeder

İşlem **10-30 dakika** sürer (veri miktarına göre).

## API'den Çalıştırma

### Backend'i Başlat

```bash
python start_backend.py
```

### API Endpoint'ini Çağır

```bash
# Analiz
curl "http://localhost:8000/api/pipeline/coverage-analysis"

# Pipeline'ı Çalıştır
curl -X POST "http://localhost:8000/api/pipeline/run-intelligent"
```

## Frontend Entegrasyonu

```typescript
// Admin paneline buton ekle
const handleRunPipeline = async () => {
  const response = await fetch('/api/pipeline/run-intelligent', {
    method: 'POST'
  });
  
  const result = await response.json();
  alert(`Başarılı! Kapsama: ${result.summary.final_coverage_pct}%`);
};
```

## Günlük Otomatik Çalıştırma

### Windows (Task Scheduler)

```powershell
# Her gün 07:00'de çalıştır
schtasks /create /tn "DustPipeline" /tr "python C:\dust-mvp\run_intelligent_pipeline.py" /sc daily /st 07:00
```

### Linux/Mac (Cron)

```bash
# Crontab ekle
0 7 * * * cd /dust-mvp && python run_intelligent_pipeline.py >> pipeline.log 2>&1
```

## Sorun Giderme

### Problem: "Module not found"

```bash
# Python path'i kontrol et
python -c "import sys; print('\n'.join(sys.path))"

# src klasörünü path'e ekle
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Problem: "Database connection failed"

```bash
# PostgreSQL çalışıyor mu?
pg_isready -h localhost -p 5432

# Bağlantı string'i doğru mu?
echo $DATABASE_URL
```

### Problem: "No data found"

```bash
# Ham veri dizinlerini kontrol et
ls data/raw/modis/
ls data/raw/cams/
ls data/raw/era5/

# Eğer ham veri yoksa, tahmin üretilir (normal)
```

## Önemli Parametreler

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `--max-lookback` | 90 gün | Geriye ne kadar bakılacak |
| `--min-age` | 7 gün | Ne kadar eski veri "güncel değil" |
| `--analyze-only` | false | Sadece analiz yap |
| `--verbose` | false | Detaylı log |

## Örnek Kullanımlar

```bash
# Sadece son 30 günü kontrol et
python run_intelligent_pipeline.py --max-lookback 30

# 3 günden eski veriyi güncelle
python run_intelligent_pipeline.py --min-age 3

# Detaylı log kayıtları
python run_intelligent_pipeline.py --verbose

# Rapor oluştur
python run_intelligent_pipeline.py --export-report report.json
```

## Sonuç Kontrolü

```bash
# Veritabanını kontrol et
python -c "
from src.database import db_manager, DailyStats
with db_manager.get_session() as s:
    count = s.query(DailyStats).count()
    print(f'Toplam kayıt: {count}')
    print(f'Beklenen: {81 * 90} (81 il x 90 gün)')
"
```

## Yardım

```bash
# Tüm komut seçeneklerini gör
python run_intelligent_pipeline.py --help

# Detaylı dokümantasyon
cat INTELLIGENT_PIPELINE_GUIDE.md
```

---

**Soru/Sorun?** → `intelligent_pipeline.log` dosyasını kontrol edin

