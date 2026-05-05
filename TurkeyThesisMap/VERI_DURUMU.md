# Veri Durumu

Bu eklenti koroplet harita üretmek için Excel/CSV içinde en az bir il veya ilçe adı sütunu ve sayısal değer sütunu bekler.

Mevcut `veri` klasöründeki bazı dosyalar yalnızca `Türkiye` toplamı içeriyor. Bu dosyalarla il/ilçe bazlı harita üretilemez; eklenti bu dosyaları veri ağacında pasif gösterir.

## Haritaya çevrilebilen dosyalar

- `Doğum Yerine Göre Nüfus.xlsx`
- `İller Arası Göç.xlsx`

## İl/ilçe bazlı satır içermediği için haritaya çevrilemeyen örnekler

- `Nüfus Artış Hızı.xlsx`
- `Nüfus Yoğunluğu.xlsx`
- `Eğitim Durumu.xlsx`
- `Ortanca Yaş.xlsx`
- `Yaş Bağımlılık Oranı.xlsx`
- `Canlı Doğum Sayısı.xlsx`

## Eğitim Durumu hatası nasıl düzeltilir?

`Eğitim Durumu.xlsx` dosyasındaki satırlar şu yapıda geliyor:

`Yıl | Düzey | Eğitim Durumu | Toplam | Erkek | Kadın | ...`

Burada `Düzey` alanı `TÜRKİYE` olduğu için dosyada `Adana`, `Ankara`, `İstanbul` gibi il adları yok. Koroplet harita için TÜİK'ten il bazlı eğitim tablosu indirilmeli veya manuel yükleme bölümünde şu tipte bir CSV/XLSX kullanılmalıdır:

`Yıl | İl | Eğitim Durumu | Değer`

Örnek:

`2024 | Ankara | Yüksekokul veya Fakülte | 123456`

## Online TÜİK kullanımı

TÜİK Online SDMX bölümünde hazır veri listesi yoktur. Arama kutusuna anahtar kelime yazılır veya boş aramayla tüm üretim TÜİK tabloları listelenir. Tablo seçildikten sonra `Tablo Seçeneklerini Göster` düğmesiyle il/ilçe ve gösterge seçenekleri kontrol edilir.

Harita üretmeden önce yıl alanı zorunludur. Tek yıl için başlangıç alanına `2020` yazılır. Aralık için başlangıç ve bitiş birlikte kullanılır: `2011` - `2020`.

Bir TÜİK tablosu birden fazla gösterge içeriyorsa filtre alanı doldurulmalıdır. Örnek:

`ADNKS_GOSTERGE=Population density`

Yıl aralığı girilirse her yıl için ayrı harita üretilir. Örnek:

`1960` - `2020`

## Beşeri coğrafya için önerilen online şablonlar

- Nüfus yoğunluğu: yerleşme, nüfus baskısı ve çevre-insan ilişkisi için temel harita.
- Nüfus artış hızı: büyüyen ve küçülen illeri karşılaştırır.
- İlçe nüfus artış hızı: tek ilde ilçe düzeyinde değişimi gösterir.
- Yabancı nüfus: göç, yabancı nüfus ve uluslararası hareketlilik çalışmaları için uygundur.
- Medeni durum: sosyal yapı ve demografik kompozisyon haritaları üretir.
- Hanehalkı: yaşam kalitesi, konut ve aile yapısı analizlerinde kullanılır.

Haritaya uygun olmayan tablolar genellikle yalnızca Türkiye toplamı veren veya il/ilçe alanı bulunmayan tablolardır.
