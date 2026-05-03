# TurkeyThesisMap

TurkeyThesisMap, QGIS içinde TÜİK online verileriyle il/ilçe bazlı koroplet beşeri coğrafya haritaları üretmek için geliştirilmiş bağımsız bir QGIS eklentisidir. Nüfus, göç, eğitim, hanehalkı, doğum, evlenme, boşanma, ulaşım, çevre, altyapı, ekonomi, tarım ve sanayi başlıklarında hazır şablonlar sunar.

Eklenti, QGIS'in kendi Python ortamı ile çalışacak şekilde tasarlanmıştır. Harita üretimi, GADM Türkiye idari sınırları ve TÜİK SDMX REST servisinden çekilen güncel veriler üzerine kuruludur. Kullanıcı ister hazır şablon seçerek az eforla harita üretir, ister TÜİK tablosunu kendisi arayıp filtreleyerek özel harita oluşturur.

## İçindekiler

- [Öne çıkan özellikler](#öne-çıkan-özellikler)
- [Kimler için?](#kimler-için)
- [QGIS sürüm uyumluluğu](#qgis-sürüm-uyumluluğu)
- [Kurulum](#kurulum)
- [QGIS içinde eklentiye erişim](#qgis-içinde-eklentiye-erişim)
- [Hızlı kullanım akışı](#hızlı-kullanım-akışı)
- [Hazır şablon kategorileri](#hazır-şablon-kategorileri)
- [TÜİK online veri çekme mantığı](#tüik-online-veri-çekme-mantığı)
- [Manuel Excel/CSV veri yükleme](#manuel-excelcsv-veri-yükleme)
- [Harita ayarları ve layout çıktısı](#harita-ayarları-ve-layout-çıktısı)
- [Dışa aktarma ve rapor](#dışa-aktarma-ve-rapor)
- [Önbellek ve performans](#önbellek-ve-performans)
- [Sık karşılaşılan hatalar](#sık-karşılaşılan-hatalar)
- [Teknik yapı](#teknik-yapı)
- [Teşekkür ve üçüncü taraf ilham kaynakları](#teşekkür-ve-üçüncü-taraf-ilham-kaynakları)

## Öne çıkan özellikler

- TÜİK online SDMX REST servisinden veri arama, tablo seçeneklerini inceleme ve filtreli veri çekme.
- İl ve ilçe düzeyinde koroplet harita üretimi.
- 182 hazır harita şablonu.
- Kategorilere ayrılmış şablon seçimi.
- GADM 4.1 Türkiye idari sınırlarını otomatik indirme ve önbelleğe alma.
- Nüfus, göç, eğitim, çevre, ulaşım, tarım ve sanayi gibi akademik beşeri coğrafya konularına uygun haritalar.
- Manuel Excel/CSV veri yükleme.
- QGIS layer panelinde okunabilir kısa katman adları.
- Kullanıcı isteğine bağlı dışa aktarma; haritayı üretmek otomatik export yapmaz.
- Layout çıktısında başlık, açıklama, lejant, ölçek, kuzey oku, konum haritası ve çıktı ayarları.
- Hata durumlarında kullanıcıya neyi kontrol etmesi gerektiğini açıklayan Türkçe uyarılar.

## Kimler için?

Bu eklenti özellikle:

- Coğrafya bölümü öğrencileri,
- Beşeri coğrafya çalışan araştırmacılar,
- TÜİK verisiyle il/ilçe bazlı tematik harita üretmek isteyen QGIS kullanıcıları,
- Rapor, ödev, makale, sunum veya saha çalışması için hızlı koroplet harita üretmek isteyen kişiler

için hazırlanmıştır.

## QGIS sürüm uyumluluğu

Eklentinin metadata bilgisinde minimum QGIS sürümü `3.16` olarak tanımlıdır. Bununla birlikte eklenti; TÜİK online veri çekme, PyQt arayüzü, QGIS layout araçları, lejant, ölçek, kuzey oku, konum haritası ve dışa aktarma özelliklerini birlikte kullandığı için güncel bir QGIS 3.x LTR veya daha yeni QGIS 3.x sürümüyle kullanılması önerilir.

Eski QGIS sürümlerinde eklenti kurulsa bile bazı arayüz, layout veya dışa aktarma davranışları farklı çalışabilir. Hata alınırsa önce QGIS sürümünün güncel olup olmadığı kontrol edilmelidir.

Öneri: mümkünse QGIS'in güncel LTR sürümünü kullanın. Çok eski QGIS 3.x sürümlerinde alınan hatalar eklentiden değil, QGIS API veya layout davranışı farklarından kaynaklanabilir.

## Kurulum

QGIS'i İngilizce arayüzle kullanıyorsanız kurulum yolu:

1. QGIS'i açın.
2. Menüden `Plugins > Manage and Install Plugins` ekranına girin.
3. Sol taraftan `Install from ZIP` sekmesini açın.
4. `TurkeyThesisMap.zip` dosyasını seçin.
5. `Install Plugin` düğmesine basın.
6. QGIS eklentiyi etkinleştirdikten sonra TurkeyThesisMap kullanılabilir hale gelir.

Not: Eklenti dış Python paketi gerektirmez. `pandas`, `openpyxl`, `requests`, `httpx`, `R`, `MCP` veya benzeri ek kurulumlar zorunlu değildir.

## QGIS içinde eklentiye erişim

Kurulumdan sonra eklentiye QGIS içinde şu yollardan erişebilirsiniz:

- `Plugins > TurkeyThesisMap`
- QGIS toolbar üzerindeki TurkeyThesisMap düğmesi

Eklenti paneli sekmeli yapıdadır. Veri seçimi, manuel veri, harita ayarları, üretim ve dışa aktarma işlemleri ayrı bölümlerde tutulur.

## Hızlı kullanım akışı

1. `Plugins > TurkeyThesisMap` ile eklenti panelini açın.
2. `Çalışma Alanı` sekmesinde çıktı klasörünü kontrol edin.
3. `Veri Seçimi` sekmesinde hazır şablon kategorisi seçin.
4. İstediğiniz şablonu seçip `Şablonu Uygula` düğmesine basın.
5. Yıl aralığını girin. Tek yıl için bitiş yılını boş bırakabilirsiniz.
6. Gerekirse `Tablo Seçeneklerini Göster` ile TÜİK tablosundaki filtreleri kontrol edin.
7. `Harita Ayarları` sekmesinde başlık, açıklama, sınıflandırma, renk paleti, lejant ve layout ayarlarını düzenleyin.
8. `Haritayı Üret` düğmesine basın.
9. Dışa aktarmak isterseniz `Dışa Aktarma / Rapor` sekmesinden PNG, PDF veya rapor çıktısını alın.

## Hazır şablon kategorileri

Eklentideki hazır şablonlar tek uzun liste halinde verilmez; kategori seçimiyle ayrıştırılır. Böylece kullanıcı hangi veri grubunda çalıştığını daha kolay görür.

Başlıca kategoriler:

- Nüfus ve Demografi
- Göç, Doğum Yeri ve Kayıt
- Hanehalkı ve Sosyal Yapı
- Doğum, Evlenme ve Boşanma
- Eğitim
- Konut ve Kentleşme
- Ulaşım
- Çevre ve Altyapı
- Ekonomi
- Tarım
- Sanayi

Örnek şablonlar:

- Nüfus yoğunluğu
- Toplam nüfus
- İlçe toplam nüfus
- İlçe nüfus artış hızı
- Yabancı nüfus
- Doğum yerine göre nüfus
- Yurtdışında doğan nüfus oranı
- Ortalama hanehalkı büyüklüğü
- Medeni durum
- Ortanca yaş
- Yaş bağımlılık oranı
- Okul yaşam beklentisi
- Üniversite mezunu nüfus
- Kaba doğum hızı
- Kaba evlenme hızı
- Kaba boşanma hızı
- Motorlu taşıt sayısı
- Trafik kazası göstergeleri
- Belediye atığı
- İçme suyu ve atıksu göstergeleri
- Tarımsal girişimler
- Hayvancılık girişimleri
- İmalat sanayi girişimleri
- Madencilik, enerji ve inşaat girişimleri

## TÜİK online veri çekme mantığı

TurkeyThesisMap'in ana veri kaynağı TÜİK'in online SDMX REST servisidir.

Eklentinin veri çekme süreci şu mantıkla çalışır:

1. TÜİK dataflow listesi alınır.
2. Kullanıcının aradığı kelimelere göre uygun TÜİK tabloları listelenir.
3. Seçilen tablonun metadata yapısı okunur.
4. Tablodaki boyutlar incelenir: yıl, gösterge, il/ilçe alanı, cinsiyet, yaş grubu, eğitim durumu, faaliyet alanı vb.
5. Birden fazla gösterge içeren tablolarda kullanıcıdan doğru filtreyi seçmesi beklenir.
6. Şablon kullanılıyorsa filtreler otomatik doldurulur.
7. Yıl aralığına göre TÜİK gözlemleri çekilir.
8. Çekilen veride il/ilçe adı ve sayısal değer birlikte aranır.
9. Aynı il/ilçe için birden çok satır varsa değerler kontrollü şekilde toplanır.
10. Veri GADM sınırlarıyla eşleştirilir.
11. QGIS içinde koroplet katmanı ve layout hazırlanır.

Online veri çekme sırasında kullanılan ana fikir şudur: önce tabloyu bul, sonra tablonun seçeneklerini oku, sonra doğru filtreleri uygulayıp yalnızca haritaya dönüştürülebilen il/ilçe kayıtlarını kullan.

Bu yaklaşım sayesinde eklenti sabit hazır Excel dosyalarına bağımlı kalmaz. TÜİK servisinden gelen güncel tablolarla çalışabilir. Ancak her TÜİK tablosu harita üretmeye uygun değildir. Sadece il/ilçe veya haritaya bağlanabilecek mekansal kırılım içeren tablolar kullanılabilir.

## Manuel Excel/CSV veri yükleme

TÜİK online veri dışında kullanıcı kendi Excel veya CSV dosyasını da yükleyebilir.

Manuel veri için önerilen yapı:

- Bir sütunda il veya ilçe adı bulunmalıdır.
- Bir sütunda sayısal değer bulunmalıdır.
- Sayısal değerler mümkün olduğunca temiz olmalıdır.
- İl/ilçe adları Türkiye idari adlarıyla uyumlu yazılmalıdır.

Eklenti, manuel dosyada il/ilçe adı ve sayısal değer alanlarını eşleştirerek harita üretmeye çalışır.

## Harita ayarları ve layout çıktısı

`Harita Ayarları` sekmesinde haritanın akademik ve okunaklı görünmesi için gerekli ayarlar bulunur:

- Harita başlığı
- Açıklama metni
- Değer birimi
- Renk paleti
- Sınıf sayısı
- Sınıflandırma yöntemi
- Lejant ayarları
- Manuel lejant seçeneği
- QGIS'in kendi lejantını kullanma seçeneği
- Kuzey oku
- Ölçek
- Konum haritası
- Etiket ayarları
- Layout boyutu ve çıktı düzeni

Layout tasarımında okunabilirlik ön plandadır. Lejant, ölçek ve kuzey oku harita kompozisyonuna uygun konumlandırılır. Gereksiz arka plan kalabalığı azaltılmıştır.

## Dışa aktarma ve rapor

Harita üretmek otomatik dışa aktarma yapmaz. Kullanıcı isterse dışa aktarma sekmesinden çıktı alır.

Desteklenen çıktı mantığı:

- Harita katmanı QGIS projesine eklenir.
- Layout QGIS Layout Manager içinde oluşturulur.
- PNG/PDF gibi çıktı seçenekleri dışa aktarma sekmesinden yönetilir.
- Rapor çıktısı kullanıcı isteğine bağlıdır.

Bu ayrım özellikle toplu deneme yapan kullanıcılar için önemlidir. Kullanıcı önce haritayı üretip kontrol eder, sonra yalnızca istediği çıktıları dışa aktarır.

## Önbellek ve performans

Eklenti bazı işlemleri önbelleğe alır:

- TÜİK dataflow listesi
- TÜİK metadata cevapları
- Başarılı TÜİK veri cevapları
- GADM sınır verileri

Bu yapı tekrar eden sorgularda hız kazandırır. TÜİK servisi geç yanıt verdiğinde daha önce başarılı alınmış cevap varsa eklenti bu cevaptan yararlanabilir.

Önbellek temizliği geçici çıktı dosyalarını, eklenti katmanlarını ve `TTM_` layoutlarını temizlemek için kullanılabilir. GADM sınır dosyaları korunur.

## Sık karşılaşılan hatalar

### Veri çekilemedi veya haritaya çevrilecek il/ilçe kaydı bulunamadı

Bu hata genellikle seçilen TÜİK tablosunda haritaya bağlanabilecek il/ilçe alanı olmadığında görülür.

Kontrol edin:

- `Tablo Seçeneklerini Göster` ekranında il/ilçe veya yerleşim alanı var mı?
- Gösterge/indicator alanında tek bir gösterge seçili mi?
- Cinsiyet, yaş, eğitim, faaliyet gibi alanlarda gerekiyorsa `Total` seçildi mi?
- Seçilen tablo Türkiye geneli mi, yoksa il/ilçe kırılımı veriyor mu?

### TÜİK read operation timed out

TÜİK servisi bazen yavaş cevap verebilir.

Çözüm:

- Aynı şablonu tekrar deneyin.
- Daha dar yıl aralığı kullanın.
- Önce hazır şablonlardan başlayın.
- Tablo seçeneklerini kontrol edip gereksiz geniş filtrelerden kaçının.

### Harita boş geliyor

Muhtemel nedenler:

- İl/ilçe adları sınır verisiyle eşleşmemiştir.
- Veri sütunu sayısal değildir.
- Seçilen yıl için kayıt yoktur.
- TÜİK tablosu yalnızca Türkiye toplamı vermektedir.

### GADM sınırları indirilemiyor

İnternet bağlantısını kontrol edin. GADM dosyaları ilk kullanımda indirilir ve daha sonra önbellekten kullanılır.

## Teknik yapı

Eklenti QGIS'in kendi Python ortamına uyacak şekilde hazırlanmıştır.

Kullanılan ana bileşenler:

- PyQGIS
- PyQt
- QGIS layout ve vector layer API'leri
- Python standart kütüphanesi
- TÜİK SDMX REST servisi
- GADM 4.1 Türkiye idari sınırları

Harici veri işleme için zorunlu `pandas`, `openpyxl`, `requests` veya benzeri paket kullanılmaz. Excel okuma ihtiyacı standart Python araçlarıyla çözülür.

## Teşekkür ve üçüncü taraf ilham kaynakları

TurkeyThesisMap, `tuikr` veya `tuik-mcp` projelerini paketlemez, içe aktarmaz ve çalışma zamanında bu projelere bağımlı değildir.

Bununla birlikte TÜİK online veri iş akışını tasarlarken iki açık kaynak projeden fikir düzeyinde yararlanılmıştır. Bu projeleri geliştiren kişilere emekleri için özellikle teşekkür ederiz:

- `emraher/tuikr`: TÜİK Veri Portalı, SDMX dataflow ve katalog iş akışı açısından yol gösterici olmuştur.
- `orhoncan/tuik-mcp`: TÜİK SDMX REST mantığında tablo arama, metadata inceleme ve filtreli gözlem çekme yaklaşımı açısından yol gösterici olmuştur.

Bu eklentide uygulanan istemci bağımsız Python kodudur. Ama TÜİK verilerine programatik erişim konusunda bu iki projenin açtığı yol ve paylaştığı yaklaşım saygıyla anılmalıdır.

## Kısa GitHub açıklaması

TÜİK online verileriyle QGIS içinde il/ilçe bazlı beşeri coğrafya, tarım, sanayi, nüfus, göç, eğitim, çevre ve ulaşım koroplet haritaları üreten; hazır şablonlar, GADM sınırları, layout, lejant ve rapor desteği sunan bağımsız QGIS eklentisi.
