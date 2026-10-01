# fth-system Skill Kullanım Rehberi

## Kurulum

Tüm skill’leri kurmak için:

```bash
npx skills add fatih-developer/fth-system
```

Tek bir skill kurmak için:

```bash
npx skills add fatih-developer/fth-system --skill system-design-orchestrator
```

Kurulumdan sonra ajanına görevi doğal dille vermen yeterlidir. İstersen skill’i açıkça belirtebilirsin:

```text
$system-design-orchestrator kullanarak bu sistemi tasarla.
```

## Skill’ler

### 1. system-design-requirements-framer

Belirsiz bir problemi kapsam, aktörler, functional requirements, NFR’ler, kısıtlar ve varsayımlara dönüştürür.

```text
Bu ürün için FR, NFR, kısıtlar ve varsayımları çıkar. En fazla üç kritik soru sor.
```

### 2. workload-capacity-modeler

Trafik, read/write oranı, storage, bandwidth, concurrency, cache, retention ve büyüme tahminleri üretir.

```text
Bu sistem için baseline, expected, peak ve stress kapasite hesabı yap.
```

### 3. system-design-orchestrator

Requirements, capacity, architecture, data topology, failure analysis ve validation aşamalarını koordine eder.

```text
Bu sistemi requirements’tan validation’a kadar koordine et.
```

### 4. distributed-data-topology-designer

Veri modeli, erişim desenleri, storage seçimi, partition, replication ve consistency kararlarını tasarlar.

```text
Bu sistem için access pattern’lere dayalı data topology ve operation-level consistency tasarla.
```

### 5. failure-mode-designer

Timeout, dependency outage, retry storm, duplicate delivery, overload, data corruption ve recovery senaryolarını analiz eder.

```text
Kritik akışlar için failure mode, detection, degraded mode ve recovery planı oluştur.
```

### 6. system-design-validator

Gereksinim kapsamı, kapasite birimleri, traceability, gereksiz karmaşıklık, consistency, resilience ve completion gate’lerini doğrular.

```text
Bu system design’ı PASS, CONDITIONAL veya FAIL olarak doğrula. Bulguları SDV-* kimlikleriyle üret.
```

### 7. system-design-case-simulator

Domain, trafik, büyüme, consistency, availability ve compliance parametreleriyle tekrar kullanılabilir system-design vakaları üretir.

```text
100 bin events/s telemetry sistemi için production growth-shock case üret.
```

## Önerilen Akış

Genel bir sistem tasarımı için skill’leri şu sırada kullan:

```text
requirements-framer
  → workload-capacity-modeler
  → system-design-orchestrator
  → distributed-data-topology-designer
  → failure-mode-designer
  → system-design-validator
```

Case simulator eğitim veya regression senaryosu üretmek için akışın başında veya bağımsız kullanılabilir.

## Örnek Toplu İstek

```text
$system-design-orchestrator kullan.

Bir para transferi sistemi tasarla:
- 10 milyon kullanıcı
- Peak 1.000 transfer/s
- Strong consistency
- Audit zorunlu
- RPO 0
- RTO 15 dakika

Gereksinimlerden başlayıp capacity, data topology, failure analysis ve validation aşamalarını tamamla.
```

## Çalışma Modeli

Skill’ler ortak `system_design_state` ve handoff envelope v1.0 kullanır. Uzman skill’ler state’in tamamını yeniden yazmak yerine `state_patch` üretir. Stabil kimlik aileleri şunlardır:

- `FR-*`: Functional requirement
- `NFR-*`: Non-functional requirement
- `ASM-*`: Assumption
- `EST-*`: Estimate
- `DEC-*`: Architectural decision
- `FM-*`: Failure mode
- `SDV-*`: Validator finding

Tasarım, failure analizi ve validator sonucu olmadan `complete` kabul edilmez. Microservice, sharding, Kafka/event streaming, multi-region veya polyglot persistence kararları ölçülebilir gerekçe ve daha basit alternatif olmadan önerilmez.

Validator kataloğundaki tüm kuralları (SD-R000–SD-R009) uygular. `CONDITIONAL` yalnızca kalan her High bulgu için sahibi belli bir risk kabulü varsa verilir; herhangi bir Critical bulgu veya kabul edilmemiş High bulgu `FAIL` demektir. `EST-*` kayıtları birimli girdiler, formül, değer ve birim taşır; formüller boyutsal olarak hesaplanıp beyan edilen değerle karşılaştırılır. Formüldeki çıplak sayılar (`/ 60`, `* 8`) birim dönüşümü sayılmaz.

## Doğrulama

Aynı kontroller GitHub Actions'ta her push ve pull request'te çalışır. Suite’i yerel olarak doğrulamak için:

```bash
python scripts/validate_curated_skills.py
python scripts/validate_system_design_contract.py tests/system-design/fixtures/low-traffic.json
python scripts/test_system_design_suite.py
```
