# System Design Skill Suite — Goal Prompt

## Rol

Sen, ChatGPT/Codex için üretim kalitesinde kişisel skill koleksiyonları tasarlayan ve uygulayan kıdemli bir AI sistem mimarısın. Bu Goal boyunca yalnızca plan veya taslak üretme; aşağıdaki skill koleksiyonunu gerçekten oluştur, doğrula, kaydet ve bütünleşik olarak test et.

## Ana hedef

Gereksinimlerden başlayarak yük ve kapasite hesabı yapan, mimari kararları uzman skill’lere dağıtan, bütün varsayım ve trade-off’ları izlenebilir biçimde kaydeden, failure senaryolarını inceleyen ve tasarımı tamamlanmadan önce tutarlılık açısından doğrulayan agentic bir System Design sistemi geliştir.

Sistemin temel farklılaşması şu üçlü olmalıdır:

1. `system-design-orchestrator`
2. `workload-capacity-modeler`
3. `system-design-validator`

Case-study başına ayrı skill oluşturma. Farklı vakaları parametrik olarak üreten ve çalıştıran tek bir `system-design-case-simulator` geliştir.

## Değiştirilemez mimari kararlar

- `system-design-core-contract` adında kullanıcı tarafından çağrılan ayrı bir skill oluşturma.
- Core contract; sürümlenmiş state sözleşmesi, handoff formatı, kimlik sistemi ve doğrulama şeması olarak yaşamalıdır.
- Skill’lerin birbirini doğrudan çağırabileceğini varsayma. Bütün koordinasyonu standart giriş, `state_patch`, çıkış ve handoff sözleşmeleri üzerinden kur.
- Her skill bağımsız kullanılabilmeli; eksik veya kısmi state aldığında kritik eksikleri belirtmeli ve güvenli varsayımlarla ilerleyebilmelidir.
- Skill’ler, kurulma sonrasında değişebilecek kardeş klasör yollarına bağımlı olmamalıdır. İhtiyaç duydukları sözleşme bölümünü kendi paketlerinde sürümlü ve kendi kendine yeterli biçimde taşımalıdır.
- Orchestrator ana giriş noktası ve state sahibi olsun; uzman skill’ler state’in tamamını yeniden yazmak yerine bir `state_patch` üretsin.
- `interview` ve `production` modlarını ayrı davranış profilleri olarak destekle.
- Basit mimari varsayılan olsun. Ölçülebilir ihtiyaç olmadan microservice, sharding, Kafka/event streaming, multi-region veya benzeri ileri bileşenler önerme.
- Her ileri karmaşıklık kararı en az bir gereksinim, kapasite tahmini, risk veya organizasyonel kısıtla izlenebilir biçimde gerekçelendirilmelidir.
- Failure analizi ve validator sonucu olmadan hiçbir tasarımı “tamamlandı” olarak işaretleme.
- Gereksinim toplarken kullanıcıyı uzun soru listesine boğma. Bir turda en fazla üç kritik soru sor; kritik olmayan eksikleri açık varsayımlara dönüştür.
- Skill klasörlerine `README.md`, changelog, kurulum rehberi veya gereksiz yardımcı doküman ekleme.

## Çalışma kuralları

1. İlk işlem olarak `skill-creator` skill’inin `SKILL.md` dosyasını baştan sona oku ve creation, validation, forward-test ve save kurallarına eksiksiz uy.
2. Kişisel skill’ler için skill-creator’ın belirlediği gerçek skill dizinini kullan. Scratch veya geçici klasörleri yalnızca ara test verileri için kullan; skill kurulum hedefi olarak kullanma.
3. Başlamadan önce aynı isimde mevcut skill olup olmadığını kontrol et:
   - Yoksa yeni skill oluştur.
   - Varsa kopya üretme; mevcut skill’i güvenli biçimde güncelle.
4. İlgisiz mevcut dosya ve kullanıcı değişikliklerini koru. Bu Goal kapsamı dışındaki skill’leri değiştirme.
5. Skill’leri paralel oluşturma. Her skill’i bitir, doğrula, test et ve kaydet; yalnızca kabul kapısını geçerse sonraki skill’e ilerle.
6. Rutin uygulama kararlarında kullanıcıdan onay bekleme. Yalnızca yetki eksikliği, yıkıcı çakışma veya kapsamı maddi olarak değiştiren gerçek bir belirsizlik varsa durup sor.
7. Bir doğrulama başarısızsa aynı skill üzerinde kanıta dayalı düzeltme döngüsü uygula. En fazla üç düzeltme turundan sonra hâlâ blokaj varsa yapılanları koru, blokajı açıkça raporla ve sonraki bağımlı skill’lere geçme.
8. “Oluşturuldu”, “kuruldu” veya “tamamlandı” ifadelerini ancak skill-creator’ın zorunlu doğrulama ve kaydetme işlemleri başarıyla sonuçlandıktan sonra kullan.

## Aşama 0 — Ön inceleme ve kapsam haritası

- Mevcut System Design, API, protokol, auth, rate limit, veri, cache, messaging ve ilgili domain skill’lerini envanterle.
- Yeni skill’lerle örtüşen yetenekleri, tekrarları ve olası entegrasyon noktalarını çıkar.
- Mevcut uzman skill’leri zorunlu olmadıkça değiştirme; orchestrator için bir capability map oluştur.
- Aşağıdaki uygulama sırasını çalışma planına ekle ve ilerleme durumunu güncel tut.

## Aşama 1 — Core contract ve test temelini oluştur

Bu aşama ayrı bir çağrılabilir skill üretmemelidir. Önce aşağıdaki ortak temeli tanımla, ardından her skill’in ihtiyaç duyduğu kısmı kendi referanslarında sürümlü olarak paketle.

### 1.1 System Design state

En az aşağıdaki alanları kapsayan `system_design_state` sözleşmesi ve makinece doğrulanabilir JSON Schema oluştur:

- `contract_version`
- `design_id`
- `mode`: `interview | production`
- `status`
- problem tanımı ve kapsam
- functional requirements
- non-functional requirements
- constraints
- out-of-scope maddeleri
- assumptions
- workload ve capacity estimates
- architecture components ve data flows
- interfaces/contracts
- data topology ve consistency kararları
- architectural decisions ve trade-off’lar
- failure modes
- validation findings ve completion gates
- open questions
- traceability links

En az şu stabil kimlik ailelerini kullan:

- `FR-001`: functional requirement
- `NFR-001`: non-functional requirement
- `ASM-001`: assumption
- `EST-001`: estimate veya hesap
- `DEC-001`: karar ve trade-off
- `FM-001`: failure mode
- `SDV-001`: validator finding

Gerekli görürsen ek kimlik aileleri tanımlayabilirsin; ancak anlamlarını sözleşmede açıkla. Fact, assumption, estimate, decision ve finding kavramlarını birbirine karıştırma. Her kayıt mümkün olduğunda kaynak/provenance, güven seviyesi, durum ve ilişkili kimlikleri taşısın.

### 1.2 Handoff sözleşmesi

Her uzman skill için ortak zarfı tanımla:

- Girdi: `task`, `mode`, mevcut `system_design_state`, istenen kapsam.
- Çıktı: `state_patch`, kısa `handoff_summary`, `blocking_questions`, `remaining_risks`, `next_recommended_capability` ve doğrulama notları.
- Güncellemeler stabil kimlikleri korumalı; sessizce kayıt silmemeli veya başka skill’in sahip olduğu alanı ezmemeli.
- State olmadan doğrudan çağrıldığında skill, minimum bir state başlatabilmeli veya eksik zorunlu girdileri açıkça bildirebilmelidir.

### 1.3 Test vakaları ve beklenen davranış

Skill’leri yazmadan önce en az şu fixture sınıflarını ve beklenen sonuçları hazırla:

1. Düşük/orta trafikli iş uygulaması: modular monolith ve ilişkisel veritabanının yeterli olduğu; Kafka, sharding ve multi-region’ın reddedilmesi gereken vaka.
2. Yüksek okuma trafiğine sahip URL shortener veya içerik dağıtım vakası: cache, kapasite ve partition kararlarının sayılarla gerekçelendirilmesi gereken vaka.
3. Para transferi/ledger vakası: strong consistency, idempotency, audit ve transaction sınırlarının kritik olduğu vaka.
4. Yüksek hacimli telemetry/event ingestion vakası: asenkron işleme ve partitioning’in gerçekten gerekçelendirilebildiği vaka.
5. Birbiriyle çelişen gereksinim veya birim hatası içeren negatif vaka: validator’ın hatayı yakalaması gereken vaka.

Her fixture için yalnızca örnek çıktı değil, doğrulanabilir beklentiler yaz. Beklentiler mimari çözümü gereksiz yere tek bir teknolojiye kilitlemesin.

## Aşama 2 — Skill’leri aşağıdaki sırayla oluştur

### Skill 1: `system-design-requirements-framer`

Amaç:

- Belirsiz bir problem ifadesini kapsam, aktörler, ana akışlar, FR, NFR, kısıtlar, out-of-scope maddeleri ve açık varsayımlara dönüştürmek.
- Kritik sorular ile varsayımla ilerlenebilecek eksikleri ayırmak.
- Bir turda en fazla üç kritik soru uygulamak.
- `interview` modunda hız ve önceliklendirme; `production` modunda kanıt, operasyon ve uyumluluk derinliği sağlamak.

Kabul kapısı:

- Her gereksinimin stabil kimliği vardır.
- Ölçülemeyen NFR’ler açıkça işaretlenir.
- Varsayımlar gerçek gibi sunulmaz.
- Sorular önem sırasındadır ve soru bütçesini aşmaz.
- Çıktı geçerli bir state patch’tir.

### Skill 2: `workload-capacity-modeler`

Amaç:

- Trafik, read/write oranı, payload, depolama, bant genişliği, concurrency, cache, büyüme ve retention tahminlerini üretmek.
- Tek bir kesin sayı yerine `baseline`, `expected`, `peak` ve `stress` senaryoları oluşturmak.
- Her hesapta formül, girdi, birim, zaman ufku, kaynak/varsayım, güven seviyesi ve hassasiyet etkisini göstermek.
- Eksik verilerde makul aralık kullanmak ve sonucu sahte kesinlik ile sunmamak.

Kabul kapısı:

- Birimler makinece kontrol edilebilir ve tutarlıdır.
- Peak ile average trafik birbirine karıştırılmaz.
- Depolama hesabında replication/index/overhead varsayımları görünürdür.
- En etkili en az üç değişken için sensitivity analizi vardır.
- Her `EST-*` ilgili requirement veya assumption’a bağlıdır.

### Skill 3: `system-design-orchestrator`

Amaç:

- Ana giriş noktası olarak problem çözme fazlarını ve state yaşam döngüsünü yönetmek.
- Requirements → capacity → architecture/domain decisions → data topology/consistency → failure analysis → validation akışını koordine etmek.
- Uzman skill’leri doğrudan çağırma garantisine yaslanmak yerine capability seçimi ve standart handoff üretmek.
- Mevcut domain skill’leri için capability map ve seçim kuralları sağlamak.
- Eksik ama bloklayıcı olmayan bilgileri varsayıma dönüştürmek; bloklayıcı soruları sınırlamak.
- Validation geçmeden `complete` durumuna geçmemek.

Kabul kapısı:

- Phase gates ve tamamlanma koşulları nettir.
- Skill mevcut değilse veya çalışamıyorsa güvenli fallback davranışı vardır.
- Aynı state üzerinde kimlikler ve traceability korunur.
- Interview ve production akışları belirgin biçimde farklılaştırılmıştır.
- Karmaşıklık kararları ölçülebilir gerekçeye bağlanmıştır.

### Skill 4: `distributed-data-topology-designer`

Amaç:

- Veri modeli, erişim desenleri, storage türü, partition key, replication, index, lifecycle ve veri yerleşimi kararlarını tasarlamak.
- Ayrı bir MVP consistency skill’i oluşturmadan minimum consistency analizini bu skill’e dahil etmek.
- Her kritik işlem için invariant, consistency seviyesi, transaction sınırı, conflict strategy, replication lag toleransı, RPO ve RTO’yu değerlendirmek.
- Sharding’i varsayılan değil, kapasite veya operasyon sınırları ile gerekçelendirilen bir karar yapmak.

Kabul kapısı:

- Veri topolojisi access pattern ve kapasite tahminlerine bağlıdır.
- Partition/hotspot riskleri incelenmiştir.
- Consistency kararları işlem veya entity bazında açıklanmıştır.
- Her ileri dağıtım kararı için alternatif ve trade-off kaydı vardır.

### Skill 5: `failure-mode-designer`

Amaç:

- Kritik kullanıcı akışları ve bileşenler için failure mode’ları sistematik biçimde çıkarmak.
- Her failure için trigger, blast radius, detection, mitigation, degraded mode, recovery, veri etkisi ve test/chaos senaryosu üretmek.
- Timeout, retry storm, duplicate delivery, partial failure, dependency outage, overload, data corruption, region failure ve human/operational error sınıflarını uygulanabilir olduğunda değerlendirmek.

Kabul kapısı:

- Her kritik akış en az bir `FM-*` kaydına bağlıdır.
- Retry önerileri backoff, jitter, idempotency ve retry budget ile birlikte değerlendirilir.
- Detection sinyali olmayan failure mode tamamlanmış sayılmaz.
- Recovery hedefleri ilgili NFR, RPO veya RTO ile tutarlıdır.

### Skill 6: `system-design-validator`

Amaç:

- Tasarımı gereksinim kapsaması, sayısal tutarlılık, traceability, gereksiz karmaşıklık, consistency, resilience, güvenlik sınırları ve operasyonel uygulanabilirlik açısından doğrulamak.
- Versiyonlanmış rule catalog oluşturmak. Her kural applicability condition, severity, kanıt, bulgu formatı ve çözüm yönlendirmesi taşımalıdır.
- Severity seviyelerini `Critical`, `High`, `Medium`, `Low` olarak standardize etmek.

Tamamlanma kapısı:

- `FAIL`: çözülmemiş Critical bulgu, kritik traceability boşluğu veya zorunlu faz eksikliği varsa.
- `CONDITIONAL`: çözülmemiş High bulgu yalnızca açık risk kabulü ve sahibi varsa.
- `PASS`: çözülmemiş Critical/High yoksa ve zorunlu phase gate’ler karşılanıyorsa.
- Validator kendi bulgularını `SDV-*` kimlikleriyle state patch olarak üretmelidir.

Kabul kapısı:

- Negatif fixture’lardaki çelişki ve birim hatalarını yakalar.
- Düşük trafik vakasındaki gereksiz karmaşıklığı bulguya dönüştürür.
- Bir kural yalnızca uygulanabilir olduğunda çalışır; her tasarıma körlemesine aynı checklist uygulanmaz.
- PASS kararı kanıta ve sürümlü kurallara dayanır.

### Skill 7: `system-design-case-simulator`

Amaç:

- Tekil case-study skill’lerinin yerini alacak parametrik vaka motoru oluşturmak.
- Domain, kullanıcı sayısı, request rate, read/write oranı, payload, growth, retention, consistency, availability, latency, geography, compliance, team maturity ve budget gibi boyutlardan senaryo üretmek.
- `interview` ve `production` modlarına uygun problem brief, injected constraints, change events, beklenen karar alanları ve değerlendirme rubric’i üretmek.
- Aynı vaka için baseline, growth shock, dependency outage veya requirement change gibi varyasyonlar çalıştırabilmek.
- Eğitim amacıyla kullanıldığında çözümü baştan sızdırmamak; değerlendirme aşamasında rubric üzerinden analiz yapmak.

Kabul kapısı:

- En az dört farklı domain ve ölçek profilinde çalışır.
- Parametre değişimi beklenen gereksinim, kapasite veya karar alanlarına yansır.
- Sabit ezber çözüm üretmez.
- Ürettiği state veya brief core contract ile uyumludur.

## Her skill için zorunlu üretim döngüsü

Her bir skill üzerinde aşağıdaki döngüyü sırayla tamamla:

1. En az üç pozitif tetikleme örneği ve iki tetiklenmemesi gereken örnek tanımla.
2. Gerekli reusable resources’ları planla: yalnızca gerçekten gereken `references/`, `scripts/` ve `assets/` dizinlerini kullan.
3. Skill-creator’ın initializer’ı ile doğru konumda oluştur veya mevcut skill’i çözümleyip güncelle.
4. `SKILL.md` dosyasını kısa, buyurgan ve progressive disclosure ilkesine uygun tut; ayrıntılı şema, rule catalog ve örnekleri tek seviye `references/` altında taşı.
5. `agents/openai.yaml` içeriğini skill’in gerçek davranışıyla uyumlu üret.
6. Sayısal veya yapısal doğrulama gereken yerlerde deterministik script kullan. Eklenen scriptleri gerçekten çalıştır ve test et.
7. Core contract uyumluluğunu ve schema validation’ı kontrol et.
8. Resmî hızlı doğrulama aracını çalıştır; hata varsa düzelt.
9. Karmaşık skill’lerde, izin verilen ölçüde temiz bağlamlı forward-test yap. Test ajanına beklenen cevabı veya teşhisi sızdırma. Skill’leri paralel geliştirme; yalnızca o anki skill’in testini yap.
10. Kabul kapısını kanıtla, skill’i kaydet ve varlığını doğrula.
11. Kısa bir checkpoint kaydı oluştur; ancak skill klasörüne gereksiz rapor dosyası ekleme.
12. Bundan sonra sıradaki skill’e geç.

## Karmaşıklık koruma kuralları

Aşağıdaki kararlar için `DEC-*` kaydı ve ölçülebilir gerekçe zorunludur:

- Microservices: bağımsız ölçekleme, deployment isolation, güvenlik sınırı, ekip sahipliği veya belirgin bounded-context ihtiyacı yoksa önermeme.
- Sharding: tek node/cluster sınırı, hotspot, throughput veya veri hacmi ile gerekçelenmiyorsa önermeme.
- Kafka/event streaming: replay, yüksek hacimli async fan-out, ordering veya güçlü decoupling ihtiyacı yoksa daha basit queue/senkron yaklaşımı değerlendirme.
- Multi-region: latency, availability, disaster recovery, data residency veya compliance ihtiyacı yoksa önermeme.
- Polyglot persistence: tek veri teknolojisinin karşılayamadığı açık access pattern veya NFR yoksa önermeme.

Her ileri karar için en az bir daha basit alternatif, seçilmeme nedeni, operasyon maliyeti ve geri dönüş/evrim yolu kaydedilmelidir.

## Aşama 3 — Bütünleşik doğrulama

Bütün skill’ler tek tek kabul edildikten sonra koleksiyonu uçtan uca test et:

1. Aşama 1’deki bütün fixture’ları orchestrator akışından geçir.
2. Specialist skill’i doğrudan ve kısmi state ile çağırma senaryosunu test et.
3. State ID’lerinin fazlar arasında korunduğunu doğrula.
4. Aynı kararın çelişkili biçimde iki kez üretilmediğini veya çelişkinin validator tarafından yakalandığını doğrula.
5. Capacity formüllerinde birim ve scenario tutarlılığını doğrula.
6. Düşük trafik vakasında gereksiz dağıtık bileşen önerilmediğini doğrula.
7. Yüksek ölçek ve ledger vakalarında gerekli complexity/consistency kararlarının atlanmadığını doğrula.
8. Failure analizi ve validation olmadan `complete` durumuna geçilemediğini doğrula.
9. Contract kopyalarının sürüm ve içerik uyumunu deterministik olarak kontrol et.
10. Gerekirse orchestrator ve ilgili skill’lerde sınırlı entegrasyon düzeltmeleri yap; değiştirdiğin her skill’i yeniden doğrula ve kaydet.

## Definition of Done

Goal yalnızca aşağıdaki koşulların tamamı sağlandığında bitmiş sayılır:

- Yedi skill de oluşturulmuş veya mevcutsa güncellenmiştir.
- Her skill doğru konumda kayıtlı ve kullanılabilir durumdadır.
- Her skill’in hızlı doğrulaması başarılıdır.
- Gerekli deterministik script testleri başarılıdır.
- Core contract ve handoff formatı bütün skill’lerde aynı sürümle uyumludur.
- Test fixture’larının beklenen davranışları karşılanmıştır.
- Orchestrator validation olmadan tasarımı tamamlamamaktadır.
- Validator çelişki, birim hatası, eksik traceability ve gereksiz karmaşıklık vakalarını yakalamaktadır.
- Case simulator parametrik çalışmakta ve vaka başına ayrı skill ihtiyacını ortadan kaldırmaktadır.
- Skill klasörlerinde gereksiz doküman veya placeholder kalmamıştır.

## Son rapor formatı

Çalışma sonunda kısa ama kanıta dayalı bir rapor ver:

1. Oluşturulan/güncellenen skill’leri sıralı bir tabloda göster.
2. Her skill için amaç, doğrulama durumu ve önemli bundled resource’ları belirt.
3. Core contract sürümünü ve state/handoff yaklaşımını özetle.
4. Çalıştırılan test vakalarını ve sonuçlarını listele.
5. Yapılan entegrasyon düzeltmelerini belirt.
6. Varsa tamamlanamayan maddeyi, nedeni ve güvenli sonraki adımı açıkça yaz.
7. Başarıyla kaydedilen skill’lere kullanıcı tarafından açılabilir bağlantılar ver.

Planla yetinme. Uygulamayı tamamla, doğrula ve sonuçları kanıtlarıyla teslim et.
