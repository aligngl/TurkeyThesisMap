import os
import shutil
from datetime import datetime

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    QgsCoordinateTransformContext,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsLayoutExporter,
    QgsPalLayerSettings,
    QgsProject,
    QgsRectangle,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

from .core.cache_manager import CacheManager
from .core.choropleth_engine import PALETLER, koroplet_uret
from .core.data_loader import DataLoader
from .core.excel_parser import IL_ESLESME, TR_IL_LISTESI, normalize_key, turkish_title
from .core.gadm_manager import GadmManager
from .core.layout_builder import LayoutBuilder
from .core.report_generator import ReportGenerator
from .core.tuik_sdmx_client import TuikSdmxClient, parse_filter_text


class TurkeyThesisMapDialog(QDialog):
    MAP_TEMPLATES = [
        {
            "label": "Nüfus yoğunluğu haritası (il)",
            "query": "population density provinces",
            "dataflow_id": "DF_ADNKS_T20",
            "version": "1.1",
            "filters": "",
            "title": "Nüfus Yoğunluğu",
            "level": "İl düzeyi",
            "years": "2007 sonrası; ADNKS yıllık seri",
            "unit": "kişi/km²",
            "palette": "Blues",
            "note": "Klasik beşeri coğrafya haritasıdır; değerler kişi/km2 yoğunluğu gösterir.",
        },
        {
            "label": "Nüfus artış hızı haritası (il)",
            "query": "annual growth rate population provinces",
            "dataflow_id": "DF_ADNKS_T29",
            "version": "1.1",
            "filters": "ADNKS_GOSTERGE=Annual population growth rate (‰)",
            "title": "Nüfus Artış Hızı",
            "level": "İl düzeyi",
            "years": "2008 sonrası; ADNKS yıllık seri",
            "unit": "‰",
            "palette": "RdYlGn",
            "note": "İllerin nüfus değişim hızını karşılaştırır.",
        },
        {
            "label": "Yabancı nüfus haritası (il)",
            "query": "foreign population provinces sex",
            "dataflow_id": "DF_ADNKS_T12",
            "version": "1.1",
            "filters": "SEX=Total",
            "title": "Yabancı Nüfus",
            "level": "İl düzeyi",
            "years": "2018 sonrası; yabancı nüfus yıllık seri",
            "unit": "kişi",
            "palette": "Purples",
            "note": "Göç ve uluslararası nüfus çalışmaları için uygundur.",
        },
        {
            "label": "Medeni durum haritası (il)",
            "query": "population province marital status sex",
            "dataflow_id": "DF_ADNKS_T10",
            "version": "1.1",
            "filters": "SEX=Total; CIVIL_STATUS=Total",
            "title": "Medeni Durum",
            "level": "İl düzeyi",
            "years": "2008 sonrası; kategori filtresi gerekir",
            "unit": "kişi",
            "palette": "Greens",
            "note": "Harita için ayrıca CIVIL_STATUS filtresinden evli, bekar vb. seçilmelidir.",
        },
        {
            "label": "Hanehalkı tipi haritası (il)",
            "query": "households type provinces",
            "dataflow_id": "DF_ADNKS_T06",
            "version": "1.1",
            "filters": "HANEHALKI_TIPI=Total",
            "title": "Hanehalkı",
            "level": "İl düzeyi",
            "years": "2014 sonrası; hanehalkı kategorisi seçilebilir",
            "unit": "hane",
            "palette": "Oranges",
            "note": "Konut, aile yapısı ve yaşam kalitesi çalışmalarında kullanılır.",
        },
        {
            "label": "Ortanca yaş haritası (il)",
            "query": "median age provinces",
            "dataflow_id": "DF_ADNKS_T23",
            "version": "1.1",
            "filters": "SEX=Total",
            "title": "Ortanca Yaş",
            "level": "İl düzeyi",
            "years": "2007 sonrası; yaşlanma analizi için",
            "unit": "yaş",
            "palette": "YlGnBu",
            "note": "Nüfusun yaş yapısını ve yaşlanma mekansal örüntüsünü gösterir.",
        },
        {
            "label": "Yaş bağımlılık oranı haritası (il)",
            "query": "age dependency ratio provinces",
            "dataflow_id": "DF_ADNKS_T24",
            "version": "1.1",
            "filters": "ADNKS_GOSTERGE=Total age dependency ratio (%)",
            "title": "Yaş Bağımlılık Oranı",
            "level": "İl düzeyi",
            "years": "2007 sonrası; bağımlı nüfus göstergesi",
            "unit": "%",
            "palette": "YlOrRd",
            "note": "Çocuk ve yaşlı nüfus baskısını karşılaştırmak için kullanılır.",
        },
        {
            "label": "Toplam nüfus haritası (il)",
            "query": "population of provinces by years",
            "dataflow_id": "DF_ADNKS_T30",
            "version": "1.1",
            "filters": "",
            "title": "Toplam Nüfus",
            "level": "İl düzeyi",
            "years": "2007 sonrası; il nüfusları yıllık seri",
            "unit": "kişi",
            "palette": "Blues",
            "note": "İllerin nüfus büyüklüğünü doğrudan karşılaştırır.",
        },
        {
            "label": "Yaş grubu nüfus haritası (il)",
            "query": "population province age group sex",
            "dataflow_id": "DF_ADNKS_T16",
            "version": "1.0",
            "filters": "SEX=Total; YAS_GRUBU=Total",
            "title": "Yaş Grubuna Göre Nüfus",
            "level": "İl düzeyi",
            "years": "2007 sonrası; yaş grubu filtresi seçilir",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Belirli yaş gruplarının mekansal dağılışını üretir; AGE/Yaş grubu filtresi seçilmelidir.",
        },
        {
            "label": "Geniş yaş grupları haritası (il)",
            "query": "population provinces broad age groups",
            "dataflow_id": "DF_ADNKS_T35",
            "version": "1.1",
            "filters": "YAS_GRUBU=Total",
            "title": "Geniş Yaş Grupları",
            "level": "İl düzeyi",
            "years": "2007 sonrası; 0-14, 15-64, 65+ gibi gruplar",
            "unit": "kişi",
            "palette": "YlOrRd",
            "note": "Çocuk, çalışma çağı ve yaşlı nüfus gibi geniş grupları haritalamak için uygundur.",
        },
        {
            "label": "İl/ilçe merkezi nüfusu haritası (il)",
            "query": "province district centers towns villages population province sex",
            "dataflow_id": "DF_ADNKS_T14",
            "version": "1.1",
            "filters": "SEX=Total; YERLESIM_YERI_TUR=Total",
            "title": "İl/İlçe Merkezi Nüfusu",
            "level": "İl düzeyi",
            "years": "2007 sonrası; merkez/köy-kasaba kırılımı seçilebilir",
            "unit": "kişi",
            "palette": "BuPu",
            "note": "Kentsel ve kırsal yerleşme ayrımı için kullanılabilir.",
        },
        {
            "label": "Ortalama hanehalkı büyüklüğü haritası (il)",
            "query": "average size households provinces",
            "dataflow_id": "DF_ADNKS_T25",
            "version": "1.1",
            "filters": "",
            "title": "Ortalama Hanehalkı Büyüklüğü",
            "level": "İl düzeyi",
            "years": "2014 sonrası; hanehalkı büyüklüğü",
            "unit": "kişi/hane",
            "palette": "Oranges",
            "note": "Aile yapısı, konut ve sosyal yapı analizleri için uygundur.",
        },
        {
            "label": "Tek aileli hanehalkı haritası (il)",
            "query": "one-family households type provinces",
            "dataflow_id": "DF_ADNKS_T08",
            "version": "1.1",
            "filters": "HANEHALKI_TIPI=One Family Households",
            "title": "Tek Aileli Hanehalkı",
            "level": "İl düzeyi",
            "years": "2014 sonrası; aile tipi filtresi seçilir",
            "unit": "hane",
            "palette": "Greens",
            "note": "Aile tiplerinin il düzeyindeki dağılışını üretir.",
        },
        {
            "label": "Kent-kır sınıflaması nüfus haritası (il)",
            "query": "urban rural classification sex provinces",
            "dataflow_id": "DF_ADNKS_T37",
            "version": "1.1",
            "filters": "SEX=Total; ADNKS_GOSTERGE=Concentrated urban population",
            "title": "Kent-Kır Nüfusu",
            "level": "İl düzeyi",
            "years": "2022 sonrası; kent-kır sınıflaması",
            "default_year": "2024",
            "unit": "kişi",
            "palette": "BrBG",
            "note": "Kent-kır nüfus ayrımını il düzeyinde göstermek için kullanılır.",
        },
        {
            "label": "Doğum yerine göre nüfus haritası (il)",
            "query": "population place of birth sex",
            "dataflow_id": "DF_ADNKS_T03",
            "version": "1.1",
            "filters": "SEX=Total",
            "title": "Doğum Yerine Göre Nüfus",
            "level": "İl düzeyi",
            "years": "2007 sonrası; doğum yeri filtresi seçilebilir",
            "unit": "kişi",
            "palette": "Purples",
            "note": "Doğum yeri ve göç kökeni analizleri için kullanılabilir.",
        },
        {
            "label": "İkamet iline göre doğum yeri haritası",
            "query": "province residence place of birth",
            "dataflow_id": "DF_ADNKS_T05",
            "version": "1.1",
            "filters": "DOGUM_YERI_IL=Total",
            "title": "İkamete Göre Doğum Yeri",
            "level": "İl düzeyi",
            "years": "2007 sonrası; doğum ili filtresi seçilebilir",
            "unit": "kişi",
            "palette": "Purples",
            "note": "Bir doğum ilinden gelen nüfusun ikamet illerine dağılışını üretir.",
        },
        {
            "label": "Kaba doğum hızı haritası (il)",
            "query": "crude birth rate provinces",
            "dataflow_id": "DF_DOGUM_KDH",
            "version": "1.0",
            "filters": "",
            "title": "Kaba Doğum Hızı",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; yıllık seri",
            "unit": "‰",
            "palette": "Reds",
            "note": "Doğurganlık ve nüfus yenilenmesi analizleri için kullanılır.",
        },
        {
            "label": "Toplam doğurganlık hızı haritası (il)",
            "query": "total fertility rate provinces",
            "dataflow_id": "DF_DOGUM_IL_TDH",
            "version": "1.0",
            "filters": "",
            "title": "Toplam Doğurganlık Hızı",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; yıllık seri",
            "unit": "çocuk",
            "palette": "Reds",
            "note": "İllerin doğurganlık düzeyini karşılaştırır.",
        },
        {
            "label": "Genel doğurganlık hızı haritası (il)",
            "query": "general fertility rate provinces",
            "dataflow_id": "DF_DOGUM_GDH",
            "version": "1.0",
            "filters": "",
            "title": "Genel Doğurganlık Hızı",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; yıllık seri",
            "unit": "‰",
            "palette": "Reds",
            "note": "15-49 yaş kadın nüfusa göre doğurganlık düzeyini gösterir.",
        },
        {
            "label": "Anne yaşı özel doğum hızı haritası (il)",
            "query": "age specific fertility rate provinces",
            "dataflow_id": "DF_DOGUM_IL_YASA_OZEL_DOGHIZ",
            "version": "1.0",
            "filters": "ANNE_YAS_GRUP=20-24",
            "title": "Yaşa Özel Doğum Hızı",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; yaş grubu filtresi seçilir",
            "unit": "‰",
            "palette": "Reds",
            "note": "Anne yaş gruplarına göre doğum hızını haritalar.",
        },
        {
            "label": "Doğumdaki ortalama anne yaşı haritası (il)",
            "query": "mean age of mother provinces",
            "dataflow_id": "DF_DOGUM_ANNE_ORTYAS",
            "version": "1.0",
            "filters": "",
            "title": "Ortalama Anne Yaşı",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; yıllık seri",
            "unit": "yaş",
            "palette": "YlOrRd",
            "note": "Doğum yapan annelerin ortalama yaşını illere göre gösterir.",
        },
        {
            "label": "İlk doğumdaki ortalama anne yaşı haritası (il)",
            "query": "mean age of mother first child provinces",
            "dataflow_id": "DF_DOGUM_ORTYAS_ILKDOG",
            "version": "1.0",
            "filters": "",
            "title": "İlk Doğumda Ortalama Anne Yaşı",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; yıllık seri",
            "unit": "yaş",
            "palette": "YlOrRd",
            "note": "İlk doğumdaki ortalama anne yaşını mekansal olarak karşılaştırır.",
        },
        {
            "label": "Kaba evlenme hızı haritası (il)",
            "query": "crude marriage rate provinces",
            "dataflow_id": "DF_EVLENME_KABA",
            "version": "1.1",
            "filters": "",
            "title": "Kaba Evlenme Hızı",
            "level": "İl düzeyi",
            "years": "Evlenme istatistikleri; yıllık seri",
            "unit": "‰",
            "palette": "Oranges",
            "note": "Evlenme hızının illere göre dağılışını gösterir.",
        },
        {
            "label": "Kaba boşanma hızı haritası (il)",
            "query": "crude divorce rate provinces",
            "dataflow_id": "DF_KABA_BOSANMA",
            "version": "1.0",
            "filters": "",
            "title": "Kaba Boşanma Hızı",
            "level": "İl düzeyi",
            "years": "Boşanma istatistikleri; yıllık seri",
            "unit": "‰",
            "palette": "OrRd",
            "note": "Boşanma hızının illere göre farklılaşmasını haritalar.",
        },
        {
            "label": "Kadın ortalama evlenme yaşı haritası (il)",
            "query": "mean age at marriage female provinces",
            "dataflow_id": "DF_EVLENME_ORT_YAS",
            "version": "1.0",
            "filters": "SEX=Female",
            "title": "Kadın Ortalama Evlenme Yaşı",
            "level": "İl düzeyi",
            "years": "Evlenme istatistikleri; yıllık seri",
            "unit": "yaş",
            "palette": "Oranges",
            "note": "Kadınların ortalama evlenme yaşını illere göre gösterir.",
        },
        {
            "label": "Kadın ilk evlenme yaşı haritası (il)",
            "query": "mean age at first marriage female provinces",
            "dataflow_id": "DF_EVLENME_ORT_ILK_YAS",
            "version": "1.0",
            "filters": "SEX=Female",
            "title": "Kadın İlk Evlenme Yaşı",
            "level": "İl düzeyi",
            "years": "Evlenme istatistikleri; yıllık seri",
            "unit": "yaş",
            "palette": "Oranges",
            "note": "İlk evlenme yaşındaki mekansal farklılıkları analiz eder.",
        },
        {
            "label": "Motorlu kara taşıtı sayısı haritası (il)",
            "query": "road motor vehicles by province",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_ILLER_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Total; UNIT_MEASURE=Pure number",
            "title": "Motorlu Kara Taşıtı Sayısı",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; yıllık aralık için Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Araç sahipliği ve ulaşım coğrafyası analizleri için uygundur.",
        },
        {
            "label": "Trafik kazası sayısı haritası (il)",
            "query": "traffic accidents number of accidents province",
            "dataflow_id": "DF_TRAFIK_KAZA_OLU_YARALI_V2",
            "version": "1.0",
            "filters": "KAZA_OLUM_DURUM=-; TRAFIK_KAZA_GOSTERGE=Number of Accidents; UNIT_MEASURE=Pure number",
            "title": "Trafik Kazası Sayısı",
            "level": "İl düzeyi",
            "years": "Trafik istatistikleri; yıllık seri",
            "unit": "adet",
            "palette": "Reds",
            "note": "Ulaşım güvenliği ve yoğunluk analizleri için kaza sayılarını haritalar.",
        },
        {
            "label": "Konut satış sayısı haritası (il)",
            "query": "house sales by provinces annual total",
            "dataflow_id": "DF_SATIS_SEKLI_DURUMU_ILILCE_V3",
            "version": "1.0",
            "filters": "FREQ=Annual; SATIS_TURU=Total; KONUT_ISYERI_GSTERGE=Sales by Type; INDICATOR=Number of House Sales",
            "title": "Konut Satış Sayısı",
            "level": "İl düzeyi",
            "years": "Konut istatistikleri; yıllık toplam",
            "unit": "adet",
            "palette": "BuPu",
            "note": "Konut piyasası, kentleşme ve bölgesel çekicilik analizleri için kullanılır.",
        },
        {
            "label": "Ortalama eğitim süresi haritası (il)",
            "query": "mean years of schooling provinces",
            "dataflow_id": "DF_ORTALAMA_EGITIM_SURE",
            "version": "1.0",
            "filters": "CINSIYET=Total; DUZEY_SEVIYE=IBBS-3 (Provinces)",
            "title": "Ortalama Eğitim Süresi",
            "level": "İl düzeyi",
            "years": "Eğitim istatistikleri; yıllık seri",
            "unit": "yıl",
            "palette": "Greens",
            "note": "Beşeri sermaye ve eğitim coğrafyası analizleri için temel göstergedir.",
        },
        {
            "label": "Okul yaşam beklentisi haritası (il)",
            "query": "school life expectancy provinces sex total",
            "dataflow_id": "DF_MUHTEMEL_EGITIM_SURE_ISCED_1_8",
            "version": "1.0",
            "filters": "DUZEY_SEVIYE=IBBS-3 (Provinces); CINSIYET=Total",
            "title": "Okul Yaşam Beklentisi",
            "level": "İl düzeyi",
            "years": "Eğitim istatistikleri; ISCED 1-8",
            "unit": "yıl",
            "palette": "Greens",
            "note": "İllerin beklenen eğitim süresini karşılaştırır.",
        },
        {
            "label": "Üniversite mezunu nüfus haritası (il)",
            "query": "population attained education college faculty provinces",
            "dataflow_id": "DF_ULUSAL_EGITIM_ISTATISTIK_",
            "version": "1.0",
            "filters": "CINSIYET=Total; EGITIM_SEVIYESI=College or faculty; DUZEY_SEVIYE=IBBS-3 (Provinces); YAS_GRUP=15+",
            "title": "Üniversite Mezunu Nüfus",
            "level": "İl düzeyi",
            "years": "Ulusal eğitim istatistikleri; 15+ nüfus",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Nitelikli nüfus ve eğitim düzeyi dağılışını haritalar.",
        },
        {
            "label": "Eğitim cinsiyet eşitliği haritası (il)",
            "query": "gender parity index school life expectancy province",
            "dataflow_id": "DF_MUHTEMEL_EGITIM_SURE_CINSIYET_ESITSIZLIK_ENDEKS",
            "version": "1.0",
            "filters": "DUZEY_SEVIYE=IBBS-3 (Provinces); EGITIM_SEVIYESI=Primary to tertiary",
            "title": "Eğitim Cinsiyet Eşitliği",
            "level": "İl düzeyi",
            "years": "Eğitim istatistikleri; cinsiyet eşitliği endeksi",
            "unit": "endeks",
            "palette": "PRGn",
            "note": "Eğitimde toplumsal cinsiyet farklılıklarını mekansal olarak gösterir.",
        },
        {
            "label": "Boşanma dava süresi haritası (il)",
            "query": "divorces duration of divorce case provinces",
            "dataflow_id": "DF_BOSANMA_DAVASURE",
            "version": "1.0",
            "filters": "DAVA_SURE=Total",
            "title": "Boşanma Dava Süresi",
            "level": "İl düzeyi",
            "years": "Boşanma istatistikleri; toplam dava süresi",
            "unit": "adet",
            "palette": "OrRd",
            "note": "Boşanma süreçlerinin illere göre yoğunluğunu gösterir.",
        },
        {
            "label": "Boşanmada eş yaş farkı haritası (il)",
            "query": "divorces age difference of spouses provinces male older",
            "dataflow_id": "DF_BOSANMA_ESYASFARK",
            "version": "1.0",
            "filters": "YAS_FARK_TUR=Male Older; YAS_FARK=Total",
            "title": "Boşanmada Eş Yaş Farkı",
            "level": "İl düzeyi",
            "years": "Boşanma istatistikleri; erkek büyük toplamı",
            "unit": "adet",
            "palette": "OrRd",
            "note": "Eş yaş farkına göre boşanma örüntülerini analiz eder.",
        },
        {
            "label": "Evlenmede eş yaş farkı haritası (il)",
            "query": "marriages age difference of spouses provinces male older",
            "dataflow_id": "DF_EVLENME_YASFARK",
            "version": "1.0",
            "filters": "YAS_FARK_TUR=Male Older; YAS_FARK=Total",
            "title": "Evlenmede Eş Yaş Farkı",
            "level": "İl düzeyi",
            "years": "Evlenme istatistikleri; erkek büyük toplamı",
            "unit": "adet",
            "palette": "Oranges",
            "note": "Evliliklerde eş yaş farkının mekansal dağılışını gösterir.",
        },
        {
            "label": "Evli annelerden doğum haritası (il)",
            "query": "births legal marital status mother married provinces",
            "dataflow_id": "DF_DOGUM_ANNEMEDENI",
            "version": "1.0",
            "filters": "ANNE_MEDENI_DURUM=Married",
            "title": "Evli Annelerden Doğum",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; annenin medeni durumu",
            "unit": "adet",
            "palette": "Reds",
            "note": "Doğumların aile yapısı ve medeni durum boyutunu haritalar.",
        },
        {
            "label": "Toplam doğum sayısı haritası (il)",
            "query": "births by months total provinces",
            "dataflow_id": "DF_DOGUM_AY",
            "version": "1.0",
            "filters": "AY=Total",
            "title": "Toplam Doğum Sayısı",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; yıllık toplam",
            "unit": "adet",
            "palette": "Reds",
            "note": "Doğum sayılarının illere göre dağılışını gösterir.",
        },
        {
            "label": "Çocuk bağımlılık oranı haritası (il)",
            "query": "child dependency ratio provinces",
            "dataflow_id": "DF_ADNKS_T24",
            "version": "1.1",
            "filters": "ADNKS_GOSTERGE=Child dependency ratio % (0-14 years)",
            "title": "Çocuk Bağımlılık Oranı",
            "level": "İl düzeyi",
            "years": "ADNKS; çocuk bağımlılık oranı",
            "unit": "%",
            "palette": "YlOrRd",
            "note": "0-14 yaş nüfusun çalışma çağındaki nüfusa baskısını gösterir.",
        },
        {
            "label": "Yaşlı bağımlılık oranı haritası (il)",
            "query": "elderly dependency ratio provinces",
            "dataflow_id": "DF_ADNKS_T24",
            "version": "1.1",
            "filters": "ADNKS_GOSTERGE=Elderly dependency ratio % (65+ years)",
            "title": "Yaşlı Bağımlılık Oranı",
            "level": "İl düzeyi",
            "years": "ADNKS; yaşlı bağımlılık oranı",
            "unit": "%",
            "palette": "YlOrRd",
            "note": "65+ nüfusun çalışma çağındaki nüfusa oranını haritalar.",
        },
        {
            "label": "0-4 yaş nüfusu haritası (il)",
            "query": "population age group 0-4 provinces",
            "dataflow_id": "DF_ADNKS_T16",
            "version": "1.0",
            "filters": "SEX=Total; YAS_GRUBU=0-4",
            "title": "0-4 Yaş Nüfusu",
            "level": "İl düzeyi",
            "years": "ADNKS; yaş grubu ve cinsiyet",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Çocuk nüfus ve okul öncesi hizmet ihtiyacı analizlerinde kullanılabilir.",
        },
        {
            "label": "65+ yaş nüfusu haritası (il)",
            "query": "population age group 65 plus provinces",
            "dataflow_id": "DF_ADNKS_T35",
            "version": "1.1",
            "filters": "YAS_GRUBU=65+",
            "title": "65+ Yaş Nüfusu",
            "level": "İl düzeyi",
            "years": "ADNKS; geniş yaş grupları",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Yaşlanma, bakım ve sağlık hizmeti analizleri için kullanılır.",
        },
        {
            "label": "Kırsal nüfus haritası (il)",
            "query": "rural population urban rural classification provinces",
            "dataflow_id": "DF_ADNKS_T37",
            "version": "1.1",
            "filters": "SEX=Total; ADNKS_GOSTERGE=Rural population",
            "title": "Kırsal Nüfus",
            "level": "İl düzeyi",
            "years": "2022 sonrası; kent-kır sınıflaması",
            "default_year": "2024",
            "unit": "kişi",
            "palette": "BrBG",
            "note": "Kırsal nüfusun illere göre dağılışını gösterir.",
        },
        {
            "label": "Orta yoğun kent nüfusu haritası (il)",
            "query": "medium urban population provinces",
            "dataflow_id": "DF_ADNKS_T37",
            "version": "1.1",
            "filters": "SEX=Total; ADNKS_GOSTERGE=Medium urban population",
            "title": "Orta Yoğun Kent Nüfusu",
            "level": "İl düzeyi",
            "years": "2022 sonrası; kent-kır sınıflaması",
            "default_year": "2024",
            "unit": "kişi",
            "palette": "BrBG",
            "note": "Kentleşme kademelerini karşılaştırmak için kullanılır.",
        },
        {
            "label": "Trafik yaralı sayısı haritası (il)",
            "query": "traffic accidents persons injured province",
            "dataflow_id": "DF_TRAFIK_KAZA_OLU_YARALI_V2",
            "version": "1.0",
            "filters": "KAZA_OLUM_DURUM=-; TRAFIK_KAZA_GOSTERGE=Number of Persons Injured; UNIT_MEASURE=Pure number",
            "title": "Trafik Yaralı Sayısı",
            "level": "İl düzeyi",
            "years": "Trafik istatistikleri; yıllık seri",
            "unit": "kişi",
            "palette": "Reds",
            "note": "Ulaşım güvenliği ve risk yoğunluğu analizlerinde kullanılır.",
        },
        {
            "label": "Trafikte ölen kişi sayısı haritası (il)",
            "query": "traffic accidents persons killed province",
            "dataflow_id": "DF_TRAFIK_KAZA_OLU_YARALI_V2",
            "version": "1.0",
            "filters": "KAZA_OLUM_DURUM=Total; TRAFIK_KAZA_GOSTERGE=Number of Persons Killed; UNIT_MEASURE=Pure number",
            "title": "Trafikte Ölen Kişi Sayısı",
            "level": "İl düzeyi",
            "years": "Trafik istatistikleri; yıllık seri",
            "unit": "kişi",
            "palette": "Reds",
            "note": "Trafik kaynaklı ölüm örüntülerini illere göre gösterir.",
        },
        {
            "label": "Yabancılara konut satışı haritası (ilçe)",
            "query": "house sales to foreigners provinces districts",
            "dataflow_id": "DF_YABANCILARA_SATILAR_ILILCE_V3",
            "version": "1.0",
            "filters": "FREQ=Annual; INDICATOR=Number of House Sales",
            "title": "Yabancılara Konut Satışı",
            "level": "İlçe düzeyi",
            "years": "Konut istatistikleri; yıllık toplam",
            "unit": "adet",
            "palette": "PiYG",
            "note": "Yabancılara konut satışının ilçe düzeyindeki mekansal yoğunlaşmasını gösterir.",
        },
        {
            "label": "Kadınlara konut satış payı haritası (il)",
            "query": "annual sales by gender female house sales province",
            "dataflow_id": "DF_CINSIYETE_GORE_SATISLAR_V3",
            "version": "1.0",
            "filters": "KONUT_ISYERI_SAHP=Female; INDICATOR=Number of House Sales",
            "title": "Kadınlara Konut Satış Payı",
            "level": "İl düzeyi",
            "years": "Konut istatistikleri; cinsiyete göre satış payı",
            "unit": "%",
            "palette": "PiYG",
            "note": "Konut sahipliği ve toplumsal cinsiyet temalı mekansal analizler için uygundur.",
        },
        {
            "label": "Girişim sayısı haritası (il)",
            "query": "number of enterprises by province size group total",
            "dataflow_id": "DF_BR_BUYUKLUK_GIRISIM",
            "version": "1.0",
            "filters": "BUYUKLUK_GRUP=Total",
            "title": "Girişim Sayısı",
            "level": "İl düzeyi",
            "years": "Bölgesel iş kayıtları; toplam girişim",
            "unit": "adet",
            "palette": "Greys",
            "note": "Ekonomik coğrafya, kent ekonomisi ve bölgesel gelişmişlik analizleri için kullanılır.",
        },
        {
            "label": "Doğumda bekar anne haritası (il)",
            "query": "births mother never married provinces",
            "dataflow_id": "DF_DOGUM_ANNEMEDENI",
            "version": "1.0",
            "filters": "ANNE_MEDENI_DURUM=Never married",
            "title": "Doğumda Bekar Anne",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; annenin medeni durumu",
            "unit": "adet",
            "palette": "Reds",
            "note": "Aile yapısı ve sosyal yapı çalışmalarında kullanılabilecek özel göstergedir.",
        },
        {
            "label": "Evlenmede kadın 20-24 yaş haritası (il)",
            "query": "marriages province age group sex female 20-24",
            "dataflow_id": "DF_EVLENME_YASGR_CINS",
            "version": "1.0",
            "filters": "SEX=Female; YAS_GRUP=20-24",
            "title": "Evlenmede Kadın 20-24 Yaş",
            "level": "İl düzeyi",
            "years": "Evlenme istatistikleri; yaş ve cinsiyet",
            "unit": "adet",
            "palette": "Oranges",
            "note": "Genç kadın evliliklerinin illere göre dağılışını analiz eder.",
        },
        {
            "label": "Boşanmada kadın 25-29 yaş haritası (il)",
            "query": "divorces province sex female age group 25-29",
            "dataflow_id": "DF_BOSANMA_CINSIYET_YASGR",
            "version": "1.0",
            "filters": "SEX=Female; YAS_GRUP=25-29",
            "title": "Boşanmada Kadın 25-29 Yaş",
            "level": "İl düzeyi",
            "years": "Boşanma istatistikleri; yaş ve cinsiyet",
            "unit": "adet",
            "palette": "OrRd",
            "note": "Yaş grubu ve cinsiyet temelli boşanma örüntülerini haritalar.",
        },
        {
            "label": "Okuma yazma bilmeyen nüfus haritası (il)",
            "query": "illiterate population provinces education sex total",
            "dataflow_id": "DF_ULUSAL_EGITIM_ISTATISTIK_",
            "version": "1.0",
            "filters": "CINSIYET=Total; EGITIM_SEVIYESI=Illiterate; DUZEY_SEVIYE=IBBS-3 (Provinces); YAS_GRUP=15+",
            "title": "Okuma Yazma Bilmeyen Nüfus",
            "level": "İl düzeyi",
            "years": "Ulusal eğitim istatistikleri; 15+ nüfus",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Eğitim yoksunluğu ve beşeri gelişmişlik analizlerinde kullanılır.",
        },
        {
            "label": "Lise mezunu nüfus haritası (il)",
            "query": "upper secondary school population provinces",
            "dataflow_id": "DF_ULUSAL_EGITIM_ISTATISTIK_",
            "version": "1.0",
            "filters": "CINSIYET=Total; EGITIM_SEVIYESI=Upper secondary school; DUZEY_SEVIYE=IBBS-3 (Provinces); YAS_GRUP=15+",
            "title": "Lise Mezunu Nüfus",
            "level": "İl düzeyi",
            "years": "Ulusal eğitim istatistikleri; 15+ nüfus",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Eğitim düzeyi ve beşeri sermaye çalışmalarında kullanılır.",
        },
        {
            "label": "İpotekli konut satışı haritası (il)",
            "query": "mortgaged house sales provinces annual",
            "dataflow_id": "DF_SATIS_SEKLI_DURUMU_ILILCE_V3",
            "version": "1.0",
            "filters": "FREQ=Annual; SATIS_TURU=Mortgaged Sale; KONUT_ISYERI_GSTERGE=Sales by Type; INDICATOR=Number of House Sales",
            "title": "İpotekli Konut Satışı",
            "level": "İl düzeyi",
            "years": "Konut istatistikleri; yıllık toplam",
            "unit": "adet",
            "palette": "BuPu",
            "note": "Konut finansmanı, kentleşme ve piyasa hareketliliği analizlerinde kullanılır.",
        },
        {
            "label": "Erkeklere konut satış payı haritası (il)",
            "query": "annual sales by gender male house sales province",
            "dataflow_id": "DF_CINSIYETE_GORE_SATISLAR_V3",
            "version": "1.0",
            "filters": "KONUT_ISYERI_SAHP=Male; INDICATOR=Number of House Sales",
            "title": "Erkeklere Konut Satış Payı",
            "level": "İl düzeyi",
            "years": "Konut istatistikleri; cinsiyete göre satış payı",
            "unit": "%",
            "palette": "PiYG",
            "note": "Konut sahipliği ve cinsiyet temelli mekansal farklılıkları gösterir.",
        },
        {
            "label": "İstanbul doğumlu nüfusun dağılışı haritası (il)",
            "query": "population by province of residence place of birth Istanbul",
            "dataflow_id": "DF_ADNKS_T05",
            "version": "1.1",
            "filters": "DOGUM_YERI_IL=Istanbul",
            "title": "İstanbul Doğumlu Nüfusun Dağılışı",
            "level": "İl düzeyi",
            "years": "ADNKS; doğum yeri ve ikamet ili",
            "unit": "kişi",
            "palette": "Purples",
            "note": "İstanbul doğumluların Türkiye içindeki ikamet dağılışını gösterir.",
        },
        {
            "label": "Ankara doğumlu nüfusun dağılışı haritası (il)",
            "query": "population by province of residence place of birth Ankara",
            "dataflow_id": "DF_ADNKS_T05",
            "version": "1.1",
            "filters": "DOGUM_YERI_IL=Ankara",
            "title": "Ankara Doğumlu Nüfusun Dağılışı",
            "level": "İl düzeyi",
            "years": "ADNKS; doğum yeri ve ikamet ili",
            "unit": "kişi",
            "palette": "Purples",
            "note": "Ankara doğumluların illere göre ikamet dağılışını haritalar.",
        },
        {
            "label": "İstanbul nüfusuna kayıtlıların dağılışı haritası (il)",
            "query": "civil registration province Istanbul residence distribution",
            "dataflow_id": "DF_ADNKS_T09",
            "version": "1.1",
            "filters": "NUFUS_KAYIT_IL=Istanbul",
            "title": "İstanbul Nüfusuna Kayıtlıların Dağılışı",
            "level": "İl düzeyi",
            "years": "ADNKS; nüfusa kayıtlı olunan il ve ikamet ili",
            "unit": "kişi",
            "palette": "Purples",
            "note": "Nüfusa kayıt ili üzerinden iç göç ve hemşehrilik örüntülerini gösterir.",
        },
        {
            "label": "Ankara nüfusuna kayıtlıların dağılışı haritası (il)",
            "query": "civil registration province Ankara residence distribution",
            "dataflow_id": "DF_ADNKS_T09",
            "version": "1.1",
            "filters": "NUFUS_KAYIT_IL=Ankara",
            "title": "Ankara Nüfusuna Kayıtlıların Dağılışı",
            "level": "İl düzeyi",
            "years": "ADNKS; nüfusa kayıtlı olunan il ve ikamet ili",
            "unit": "kişi",
            "palette": "Purples",
            "note": "Ankara nüfusuna kayıtlı kişilerin ikamet illerine dağılışını gösterir.",
        },
        {
            "label": "Kadın nüfus haritası (il)",
            "query": "female population provinces",
            "dataflow_id": "DF_ADNKS_T16",
            "version": "1.0",
            "filters": "SEX=Female; YAS_GRUBU=Total",
            "title": "Kadın Nüfus",
            "level": "İl düzeyi",
            "years": "ADNKS; cinsiyet ve yaş grubu",
            "unit": "kişi",
            "palette": "PiYG",
            "note": "Cinsiyet yapısı ve nüfus kompozisyonu analizlerinde kullanılır.",
        },
        {
            "label": "Erkek nüfus haritası (il)",
            "query": "male population provinces",
            "dataflow_id": "DF_ADNKS_T16",
            "version": "1.0",
            "filters": "SEX=Male; YAS_GRUBU=Total",
            "title": "Erkek Nüfus",
            "level": "İl düzeyi",
            "years": "ADNKS; cinsiyet ve yaş grubu",
            "unit": "kişi",
            "palette": "PiYG",
            "note": "Cinsiyet yapısı ve nüfus kompozisyonu analizlerinde kullanılır.",
        },
        {
            "label": "Evlenmede erkek 25-29 yaş haritası (il)",
            "query": "marriages province sex male age group 25-29",
            "dataflow_id": "DF_EVLENME_YASGR_CINS",
            "version": "1.0",
            "filters": "SEX=Male; YAS_GRUP=25-29",
            "title": "Evlenmede Erkek 25-29 Yaş",
            "level": "İl düzeyi",
            "years": "Evlenme istatistikleri; yaş ve cinsiyet",
            "unit": "adet",
            "palette": "Oranges",
            "note": "Genç erkek evliliklerinin illere göre dağılışını analiz eder.",
        },
        {
            "label": "Boşanmada erkek 30-34 yaş haritası (il)",
            "query": "divorces province sex male age group 30-34",
            "dataflow_id": "DF_BOSANMA_CINSIYET_YASGR",
            "version": "1.0",
            "filters": "SEX=Male; YAS_GRUP=30-34",
            "title": "Boşanmada Erkek 30-34 Yaş",
            "level": "İl düzeyi",
            "years": "Boşanma istatistikleri; yaş ve cinsiyet",
            "unit": "adet",
            "palette": "OrRd",
            "note": "Yaş grubu ve cinsiyet temelli boşanma örüntülerini haritalar.",
        },
        {
            "label": "Trafiğe kaydı yapılan otomobil haritası (il)",
            "query": "cars registered to traffic by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_KAYDI_YAPILAN_IL_V2",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Car; UNIT_MEASURE=Pure number",
            "title": "Trafiğe Kaydı Yapılan Otomobil",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Yeni otomobil kayıtları üzerinden motorlaşma ve ulaşım talebini gösterir.",
        },
        {
            "label": "Devri yapılan otomobil haritası (il)",
            "query": "cars handed over by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_DEVRI_YAPILAN_IL_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Car",
            "title": "Devri Yapılan Otomobil",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "İkinci el otomobil hareketliliğini ve bölgesel araç piyasasını haritalar.",
        },
        {
            "label": "Belediye atık hizmeti verilen nüfus oranı haritası (il)",
            "query": "municipal population served by waste services rate provinces",
            "dataflow_id": "DF_ATIK_BELEDIYE_HIZMET_V1",
            "version": "1.0",
            "filters": "BELEDIYE_ATIK_GOSTERGE=Rate of Municipal Population Served by Waste Services in Total Municipal Population; UNIT_MEASURE=Percent",
            "title": "Belediye Atık Hizmeti Verilen Nüfus Oranı",
            "level": "İl düzeyi",
            "years": "Çevre istatistikleri; belediye atık hizmeti",
            "unit": "%",
            "palette": "Greens",
            "note": "Kentsel çevre hizmetleri ve altyapı erişimi analizlerinde kullanılır.",
        },
        {
            "label": "Tek kişilik hanehalkı haritası (il)",
            "query": "one person households provinces",
            "dataflow_id": "DF_ADNKS_T06",
            "version": "1.1",
            "filters": "HANEHALKI_TIPI=One Person Households",
            "title": "Tek Kişilik Hanehalkı",
            "level": "İl düzeyi",
            "years": "ADNKS; hanehalkı tipi",
            "unit": "hane",
            "palette": "Oranges",
            "note": "Yalnız yaşama, kentleşme ve hane yapısı analizleri için kullanılır.",
        },
        {
            "label": "Geniş aile hanehalkı haritası (il)",
            "query": "extended family households provinces",
            "dataflow_id": "DF_ADNKS_T06",
            "version": "1.1",
            "filters": "HANEHALKI_TIPI=Extended Family Households",
            "title": "Geniş Aile Hanehalkı",
            "level": "İl düzeyi",
            "years": "ADNKS; hanehalkı tipi",
            "unit": "hane",
            "palette": "Oranges",
            "note": "Aile yapısı ve geleneksel hane örüntülerini mekansal olarak gösterir.",
        },
        {
            "label": "Evli nüfus haritası (il)",
            "query": "married population provinces sex total",
            "dataflow_id": "DF_ADNKS_T10",
            "version": "1.1",
            "filters": "SEX=Total; CIVIL_STATUS=Married",
            "title": "Evli Nüfus",
            "level": "İl düzeyi",
            "years": "ADNKS; medeni durum ve cinsiyet",
            "unit": "kişi",
            "palette": "OrRd",
            "note": "Medeni durum ve sosyal yapı çalışmalarında kullanılır.",
        },
        {
            "label": "Boşanmış nüfus haritası (il)",
            "query": "divorced population provinces sex total",
            "dataflow_id": "DF_ADNKS_T10",
            "version": "1.1",
            "filters": "SEX=Total; CIVIL_STATUS=Divorced",
            "title": "Boşanmış Nüfus",
            "level": "İl düzeyi",
            "years": "ADNKS; medeni durum ve cinsiyet",
            "unit": "kişi",
            "palette": "OrRd",
            "note": "Boşanmış nüfusun mekansal dağılışını gösterir.",
        },
        {
            "label": "Hiç evlenmemiş nüfus haritası (il)",
            "query": "never married population provinces sex total",
            "dataflow_id": "DF_ADNKS_T10",
            "version": "1.1",
            "filters": "SEX=Total; CIVIL_STATUS=Never married",
            "title": "Hiç Evlenmemiş Nüfus",
            "level": "İl düzeyi",
            "years": "ADNKS; medeni durum ve cinsiyet",
            "unit": "kişi",
            "palette": "OrRd",
            "note": "Evlilik davranışları ve yaş-sosyal yapı araştırmaları için kullanılabilir.",
        },
        {
            "label": "15-64 yaş nüfusu haritası (il)",
            "query": "working age population 15-64 provinces",
            "dataflow_id": "DF_ADNKS_T35",
            "version": "1.1",
            "filters": "YAS_GRUBU=15-64",
            "title": "15-64 Yaş Nüfusu",
            "level": "İl düzeyi",
            "years": "ADNKS; geniş yaş grupları",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Çalışma çağındaki nüfusun illere göre dağılışını haritalar.",
        },
        {
            "label": "Motosiklet sayısı haritası (il)",
            "query": "motorcycle count by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_ILLER_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Motorcycle; UNIT_MEASURE=Pure number",
            "title": "Motosiklet Sayısı",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Motorlaşma, kıyı/turizm bölgeleri ve ulaşım davranışı analizlerinde kullanılır.",
        },
        {
            "label": "Kamyon sayısı haritası (il)",
            "query": "truck count by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_ILLER_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Truck; UNIT_MEASURE=Pure number",
            "title": "Kamyon Sayısı",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Lojistik, sanayi ve yük taşımacılığı coğrafyası için kullanılır.",
        },
        {
            "label": "Minibüs sayısı haritası (il)",
            "query": "minibus count by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_ILLER_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Minibus; UNIT_MEASURE=Pure number",
            "title": "Minibüs Sayısı",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Toplu taşıma ve bölgesel ulaşım yapısı analizlerinde kullanılabilir.",
        },
        {
            "label": "Trafiğe kaydı yapılan motosiklet haritası (il)",
            "query": "motorcycles registered to traffic province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_KAYDI_YAPILAN_IL_V2",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Motorcycle; UNIT_MEASURE=Pure number",
            "title": "Trafiğe Kaydı Yapılan Motosiklet",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Yeni motosiklet kayıtları üzerinden ulaşım talebi ve motorlaşmayı gösterir.",
        },
        {
            "label": "Devri yapılan motosiklet haritası (il)",
            "query": "motorcycles handed over by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_DEVRI_YAPILAN_IL_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Motorcycle",
            "title": "Devri Yapılan Motosiklet",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "İkinci el motosiklet piyasası ve bölgesel hareketliliği gösterir.",
        },
        {
            "label": "Atık hizmeti verilen nüfus haritası (il)",
            "query": "population served by municipal waste services provinces",
            "dataflow_id": "DF_ATIK_BELEDIYE_HIZMET_V1",
            "version": "1.0",
            "filters": "BELEDIYE_ATIK_GOSTERGE=Population of Municipalities Served by Waste Services; UNIT_MEASURE=Persons",
            "title": "Atık Hizmeti Verilen Nüfus",
            "level": "İl düzeyi",
            "years": "Çevre istatistikleri; belediye atık hizmeti",
            "unit": "kişi",
            "palette": "Greens",
            "note": "Kentsel altyapı ve çevre hizmeti erişimini nüfus üzerinden gösterir.",
        },
        {
            "label": "Kişi başı belediye atığı haritası (il)",
            "query": "municipal waste per capita provinces",
            "dataflow_id": "DF_ATIK_BELEDIYE_HIZMET_V1",
            "version": "1.0",
            "filters": "BELEDIYE_ATIK_GOSTERGE=Amount of Waste Per Capita; UNIT_MEASURE=Daily Waste Per Capita (Kg/Capita-Day)",
            "title": "Kişi Başı Belediye Atığı",
            "level": "İl düzeyi",
            "years": "Çevre istatistikleri; kişi başı günlük atık",
            "unit": "kg/kişi-gün",
            "palette": "Greens",
            "note": "Tüketim, kent yaşamı ve çevresel baskı analizlerinde güçlü bir göstergedir.",
        },
        {
            "label": "Toplanan belediye atığı haritası (il)",
            "query": "amount of municipal waste collected provinces tonnes",
            "dataflow_id": "DF_ATIK_BELEDIYE_HIZMET_V1",
            "version": "1.0",
            "filters": "BELEDIYE_ATIK_GOSTERGE=Amount of Waste Collected; UNIT_MEASURE=Tonnes",
            "title": "Toplanan Belediye Atığı",
            "level": "İl düzeyi",
            "years": "Çevre istatistikleri; yıllık toplanan atık",
            "unit": "ton",
            "palette": "Greens",
            "note": "Kentsel nüfus, tüketim ve çevre yönetimi ilişkisini analiz eder.",
        },
        {
            "label": "Mikro girişim sayısı haritası (il)",
            "query": "number of enterprises size class 1-9 province",
            "dataflow_id": "DF_BR_BUYUKLUK_GIRISIM",
            "version": "1.0",
            "filters": "BUYUKLUK_GRUP=1-9",
            "title": "Mikro Girişim Sayısı",
            "level": "İl düzeyi",
            "years": "Bölgesel iş kayıtları; 1-9 çalışan",
            "unit": "adet",
            "palette": "Greys",
            "note": "Yerel ekonomi, küçük işletme yoğunluğu ve bölgesel girişimcilik için kullanılır.",
        },
        {
            "label": "Küçük girişim sayısı haritası (il)",
            "query": "number of enterprises size class 10-49 province",
            "dataflow_id": "DF_BR_BUYUKLUK_GIRISIM",
            "version": "1.0",
            "filters": "BUYUKLUK_GRUP=10-49",
            "title": "Küçük Girişim Sayısı",
            "level": "İl düzeyi",
            "years": "Bölgesel iş kayıtları; 10-49 çalışan",
            "unit": "adet",
            "palette": "Greys",
            "note": "KOBİ yoğunluğu ve bölgesel ekonomik yapı analizleri için kullanılır.",
        },
        {
            "label": "Kadın yabancı nüfus haritası (il)",
            "query": "foreign female population provinces",
            "dataflow_id": "DF_ADNKS_T12",
            "version": "1.1",
            "filters": "SEX=Female",
            "title": "Kadın Yabancı Nüfus",
            "level": "İl düzeyi",
            "years": "ADNKS; yabancı nüfus ve cinsiyet",
            "unit": "kişi",
            "palette": "PiYG",
            "note": "Göç, yabancı nüfus ve cinsiyet temelli mekansal analizlerde kullanılır.",
        },
        {
            "label": "Erkek yabancı nüfus haritası (il)",
            "query": "foreign male population provinces",
            "dataflow_id": "DF_ADNKS_T12",
            "version": "1.1",
            "filters": "SEX=Male",
            "title": "Erkek Yabancı Nüfus",
            "level": "İl düzeyi",
            "years": "ADNKS; yabancı nüfus ve cinsiyet",
            "unit": "kişi",
            "palette": "PiYG",
            "note": "Göç, yabancı nüfus ve cinsiyet temelli mekansal analizlerde kullanılır.",
        },
        {
            "label": "Dul nüfus haritası (il)",
            "query": "widowed population provinces sex total",
            "dataflow_id": "DF_ADNKS_T10",
            "version": "1.1",
            "filters": "SEX=Total; CIVIL_STATUS=Widowed",
            "title": "Dul Nüfus",
            "level": "İl düzeyi",
            "years": "ADNKS; medeni durum ve cinsiyet",
            "unit": "kişi",
            "palette": "OrRd",
            "note": "Yaşlanma, aile yapısı ve sosyal destek ihtiyacı analizlerinde kullanılabilir.",
        },
        {
            "label": "Erkek ortanca yaş haritası (il)",
            "query": "median age male provinces",
            "dataflow_id": "DF_ADNKS_T23",
            "version": "1.1",
            "filters": "SEX=Male",
            "title": "Erkek Ortanca Yaş",
            "level": "İl düzeyi",
            "years": "ADNKS; ortanca yaş ve cinsiyet",
            "unit": "yaş",
            "palette": "YlGnBu",
            "note": "Erkek nüfusun yaşlanma düzeyini illere göre gösterir.",
        },
        {
            "label": "Kadın ortanca yaş haritası (il)",
            "query": "median age female provinces",
            "dataflow_id": "DF_ADNKS_T23",
            "version": "1.1",
            "filters": "SEX=Female",
            "title": "Kadın Ortanca Yaş",
            "level": "İl düzeyi",
            "years": "ADNKS; ortanca yaş ve cinsiyet",
            "unit": "yaş",
            "palette": "YlGnBu",
            "note": "Kadın nüfusun yaşlanma düzeyini illere göre gösterir.",
        },
        {
            "label": "15-19 yaş nüfusu haritası (il)",
            "query": "population age group 15-19 provinces",
            "dataflow_id": "DF_ADNKS_T16",
            "version": "1.0",
            "filters": "SEX=Total; YAS_GRUBU=15-19",
            "title": "15-19 Yaş Nüfusu",
            "level": "İl düzeyi",
            "years": "ADNKS; yaş grubu ve cinsiyet",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Genç nüfus, ortaöğretim ve işgücüne geçiş analizlerinde kullanılabilir.",
        },
        {
            "label": "20-24 yaş nüfusu haritası (il)",
            "query": "population age group 20-24 provinces",
            "dataflow_id": "DF_ADNKS_T16",
            "version": "1.0",
            "filters": "SEX=Total; YAS_GRUBU=20-24",
            "title": "20-24 Yaş Nüfusu",
            "level": "İl düzeyi",
            "years": "ADNKS; yaş grubu ve cinsiyet",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Üniversite çağı, genç yetişkin nüfus ve göç çekim analizleri için uygundur.",
        },
        {
            "label": "Kadın üniversite mezunu nüfus haritası (il)",
            "query": "female college faculty graduates provinces",
            "dataflow_id": "DF_ULUSAL_EGITIM_ISTATISTIK_",
            "version": "1.0",
            "filters": "CINSIYET=Female; EGITIM_SEVIYESI=College or faculty; DUZEY_SEVIYE=IBBS-3 (Provinces); YAS_GRUP=15+",
            "title": "Kadın Üniversite Mezunu Nüfus",
            "level": "İl düzeyi",
            "years": "Ulusal eğitim istatistikleri; 15+ nüfus",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Kadın beşeri sermayesi ve eğitim eşitsizliği çalışmalarında kullanılır.",
        },
        {
            "label": "Erkek üniversite mezunu nüfus haritası (il)",
            "query": "male college faculty graduates provinces",
            "dataflow_id": "DF_ULUSAL_EGITIM_ISTATISTIK_",
            "version": "1.0",
            "filters": "CINSIYET=Male; EGITIM_SEVIYESI=College or faculty; DUZEY_SEVIYE=IBBS-3 (Provinces); YAS_GRUP=15+",
            "title": "Erkek Üniversite Mezunu Nüfus",
            "level": "İl düzeyi",
            "years": "Ulusal eğitim istatistikleri; 15+ nüfus",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Erkek beşeri sermayesi ve eğitim dağılışı çalışmalarında kullanılır.",
        },
        {
            "label": "Otobüs sayısı haritası (il)",
            "query": "bus count by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_ILLER_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Bus; UNIT_MEASURE=Pure number",
            "title": "Otobüs Sayısı",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Toplu taşıma kapasitesi ve ulaşım altyapısı analizleri için kullanılır.",
        },
        {
            "label": "Kamyonet sayısı haritası (il)",
            "query": "small truck count by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_ILLER_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Small Truck; UNIT_MEASURE=Pure number",
            "title": "Kamyonet Sayısı",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Kentsel dağıtım, ticaret ve küçük ölçekli lojistik hareketliliği gösterir.",
        },
        {
            "label": "Trafiğe kaydı yapılan kamyonet haritası (il)",
            "query": "small trucks registered to traffic province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_KAYDI_YAPILAN_IL_V2",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Small Truck; UNIT_MEASURE=Pure number",
            "title": "Trafiğe Kaydı Yapılan Kamyonet",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Yeni ticari araç talebi ve ekonomik hareketlilik için kullanılabilir.",
        },
        {
            "label": "Devri yapılan kamyonet haritası (il)",
            "query": "small trucks handed over by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_DEVRI_YAPILAN_IL_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Small Truck",
            "title": "Devri Yapılan Kamyonet",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "İkinci el ticari araç piyasası ve bölgesel ekonomik canlılığı gösterir.",
        },
        {
            "label": "Boşanmış annelerden doğum haritası (il)",
            "query": "births mother divorced provinces",
            "dataflow_id": "DF_DOGUM_ANNEMEDENI",
            "version": "1.0",
            "filters": "ANNE_MEDENI_DURUM=Divorced",
            "title": "Boşanmış Annelerden Doğum",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; annenin medeni durumu",
            "unit": "adet",
            "palette": "Reds",
            "note": "Aile yapısı ve doğum örüntülerinin sosyal boyutunu gösterir.",
        },
        {
            "label": "Dul annelerden doğum haritası (il)",
            "query": "births mother widowed provinces",
            "dataflow_id": "DF_DOGUM_ANNEMEDENI",
            "version": "1.0",
            "filters": "ANNE_MEDENI_DURUM=Widowed",
            "title": "Dul Annelerden Doğum",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; annenin medeni durumu",
            "unit": "adet",
            "palette": "Reds",
            "note": "Daha dar ama sosyal yapı ve kırılganlık analizleri için kullanılabilir.",
        },
        {
            "label": "Okul öncesi okul yaşam beklentisi haritası (il)",
            "query": "pre-primary school life expectancy provinces",
            "dataflow_id": "DF_MUHTEMEL_EGITIM_SURE_ISCED_0",
            "version": "1.0",
            "filters": "DUZEY_SEVIYE=IBBS-3 (Provinces); CINSIYET=Total",
            "title": "Okul Öncesi Okul Yaşam Beklentisi",
            "level": "İl düzeyi",
            "years": "Eğitim istatistikleri; ISCED 0",
            "unit": "yıl",
            "palette": "YlGnBu",
            "note": "Okul öncesi eğitime katılım ve eğitim erişimi farklılıklarını illere göre analiz eder.",
        },
        {
            "label": "İlk-orta-lise okul yaşam beklentisi haritası (il)",
            "query": "primary upper secondary school life expectancy provinces",
            "dataflow_id": "DF_MUHTEMEL_EGITIM_SURE_ISCED1_3",
            "version": "1.0",
            "filters": "DUZEY_SEVIYE=IBBS-3 (Provinces); CINSIYET=Total",
            "title": "İlk-Orta-Lise Okul Yaşam Beklentisi",
            "level": "İl düzeyi",
            "years": "Eğitim istatistikleri; ISCED 1-3",
            "unit": "yıl",
            "palette": "YlGnBu",
            "note": "Temel ve ortaöğretim düzeyindeki beklenen eğitim süresini karşılaştırır.",
        },
        {
            "label": "Erkek okul öncesi okul yaşam beklentisi haritası (il)",
            "query": "male pre-primary school life expectancy provinces",
            "dataflow_id": "DF_MUHTEMEL_EGITIM_SURE_ISCED_0",
            "version": "1.0",
            "filters": "DUZEY_SEVIYE=IBBS-3 (Provinces); CINSIYET=Male",
            "title": "Erkek Okul Öncesi Okul Yaşam Beklentisi",
            "level": "İl düzeyi",
            "years": "Eğitim istatistikleri; ISCED 0 ve cinsiyet",
            "unit": "yıl",
            "palette": "YlGnBu",
            "note": "Okul öncesi eğitimde erkek çocuklara ait mekansal farklılıkları gösterir.",
        },
        {
            "label": "Kadın okul öncesi okul yaşam beklentisi haritası (il)",
            "query": "female pre-primary school life expectancy provinces",
            "dataflow_id": "DF_MUHTEMEL_EGITIM_SURE_ISCED_0",
            "version": "1.0",
            "filters": "DUZEY_SEVIYE=IBBS-3 (Provinces); CINSIYET=Female",
            "title": "Kadın Okul Öncesi Okul Yaşam Beklentisi",
            "level": "İl düzeyi",
            "years": "Eğitim istatistikleri; ISCED 0 ve cinsiyet",
            "unit": "yıl",
            "palette": "YlGnBu",
            "note": "Okul öncesi eğitimde kız çocuklarına ait mekansal farklılıkları gösterir.",
        },
        {
            "label": "15-17 yaş anne doğumları haritası (il)",
            "query": "births mother age 15-17 provinces",
            "dataflow_id": "DF_DOGUM_ANNEYASGR_BOLGE",
            "version": "1.0",
            "filters": "ANNE_YAS_GRUP=15-17",
            "title": "15-17 Yaş Anne Doğumları",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; anne yaş grubu",
            "unit": "adet",
            "palette": "Reds",
            "note": "Erken yaş doğurganlığı ve sosyal kırılganlık analizlerinde kullanılabilir.",
        },
        {
            "label": "18-19 yaş anne doğumları haritası (il)",
            "query": "births mother age 18-19 provinces",
            "dataflow_id": "DF_DOGUM_ANNEYASGR_BOLGE",
            "version": "1.0",
            "filters": "ANNE_YAS_GRUP=18-19",
            "title": "18-19 Yaş Anne Doğumları",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; anne yaş grubu",
            "unit": "adet",
            "palette": "Reds",
            "note": "Genç annelik örüntüsünü illere göre karşılaştırır.",
        },
        {
            "label": "35-39 yaş anne doğumları haritası (il)",
            "query": "births mother age 35-39 provinces",
            "dataflow_id": "DF_DOGUM_ANNEYASGR_BOLGE",
            "version": "1.0",
            "filters": "ANNE_YAS_GRUP=35-39",
            "title": "35-39 Yaş Anne Doğumları",
            "level": "İl düzeyi",
            "years": "Doğum istatistikleri; anne yaş grubu",
            "unit": "adet",
            "palette": "Reds",
            "note": "İleri yaş doğurganlığının mekansal dağılışını gösterir.",
        },
        {
            "label": "Kadın ilk evlenme 20-24 yaş haritası (il)",
            "query": "first marriage female age 20-24 provinces",
            "dataflow_id": "DF_EVLENME_ILK",
            "version": "1.0",
            "filters": "SEX=Female; YAS_GRUP=20-24",
            "title": "Kadın İlk Evlenme 20-24 Yaş",
            "level": "İl düzeyi",
            "years": "Evlenme istatistikleri; ilk evlenme yaş grubu",
            "unit": "adet",
            "palette": "Oranges",
            "note": "Kadınlarda ilk evlenmenin genç yetişkin yaş grubundaki dağılışını haritalar.",
        },
        {
            "label": "Erkek ilk evlenme 25-29 yaş haritası (il)",
            "query": "first marriage male age 25-29 provinces",
            "dataflow_id": "DF_EVLENME_ILK",
            "version": "1.0",
            "filters": "SEX=Male; YAS_GRUP=25-29",
            "title": "Erkek İlk Evlenme 25-29 Yaş",
            "level": "İl düzeyi",
            "years": "Evlenme istatistikleri; ilk evlenme yaş grubu",
            "unit": "adet",
            "palette": "Oranges",
            "note": "Erkeklerde ilk evlenmenin genç yetişkin yaş grubundaki dağılışını haritalar.",
        },
        {
            "label": "Boşanma ilk yıl haritası (il)",
            "query": "divorces duration less than 1 year provinces",
            "dataflow_id": "DF_BOSANMA_EVL_SURE",
            "version": "1.0",
            "filters": "EVLILIK_SURE=Less than 1 year",
            "title": "İlk Yılda Boşanma",
            "level": "İl düzeyi",
            "years": "Boşanma istatistikleri; evlilik süresi",
            "unit": "adet",
            "palette": "OrRd",
            "note": "Evliliğin ilk yılında gerçekleşen boşanmaların illere göre dağılışını gösterir.",
        },
        {
            "label": "Boşanma 16 yıl ve üzeri haritası (il)",
            "query": "divorces duration 16 years and over provinces",
            "dataflow_id": "DF_BOSANMA_EVL_SURE",
            "version": "1.0",
            "filters": "EVLILIK_SURE=16+",
            "title": "16 Yıl ve Üzeri Boşanma",
            "level": "İl düzeyi",
            "years": "Boşanma istatistikleri; evlilik süresi",
            "unit": "adet",
            "palette": "OrRd",
            "note": "Uzun süreli evliliklerden sonra gerçekleşen boşanmaları mekansal olarak analiz eder.",
        },
        {
            "label": "İkamet ilinde doğan nüfus oranı haritası (il)",
            "query": "born in province of residence percentage provinces",
            "dataflow_id": "DF_ADNKS_T4",
            "version": "1.2",
            "filters": "DOGUM_YERI_DURUM=Born in the province of residence (%)",
            "title": "İkamet İlinde Doğan Nüfus Oranı",
            "level": "İl düzeyi",
            "years": "ADNKS; doğum yeri durum oranı",
            "unit": "%",
            "palette": "Purples",
            "note": "Yerellik, göç almama ve nüfus kökeni analizlerinde güçlü bir göstergedir.",
        },
        {
            "label": "Başka ilde doğan nüfus oranı haritası (il)",
            "query": "born in different province percentage provinces",
            "dataflow_id": "DF_ADNKS_T4",
            "version": "1.2",
            "filters": "DOGUM_YERI_DURUM=Born in a different province (%)",
            "title": "Başka İlde Doğan Nüfus Oranı",
            "level": "İl düzeyi",
            "years": "ADNKS; doğum yeri durum oranı",
            "unit": "%",
            "palette": "Purples",
            "note": "İllerin iç göçle gelen nüfus payını karşılaştırmak için kullanılır.",
        },
        {
            "label": "Yurtdışında doğan nüfus oranı haritası (il)",
            "query": "born abroad percentage provinces",
            "dataflow_id": "DF_ADNKS_T4",
            "version": "1.2",
            "filters": "DOGUM_YERI_DURUM=Born abroad (%)",
            "title": "Yurtdışında Doğan Nüfus Oranı",
            "level": "İl düzeyi",
            "years": "ADNKS; doğum yeri durum oranı",
            "unit": "%",
            "palette": "Purples",
            "note": "Uluslararası göç kökenli nüfusun illere göre yoğunlaşmasını gösterir.",
        },
        {
            "label": "İlçe nüfus artış hızı haritası (ilçe)",
            "query": "district annual population growth rate",
            "dataflow_id": "DF_ADNKS_T38",
            "version": "1.1",
            "filters": "ADNKS_GOSTERGE=Annual population growth rate (‰)",
            "title": "İlçe Nüfus Artış Hızı",
            "level": "İlçe düzeyi",
            "years": "ADNKS; son yıl ilçe serisi",
            "unit": "‰",
            "palette": "RdYlGn",
            "note": "İlçe düzeyinde büyüme, küçülme ve mekansal nüfus değişimini gösterir.",
        },
        {
            "label": "İlçe toplam nüfus haritası (ilçe)",
            "query": "district total population provinces districts",
            "dataflow_id": "DF_ADNKS_T22",
            "version": "1.1",
            "filters": "YERLESIM_YERI_TUR=Total",
            "title": "İlçe Toplam Nüfus",
            "level": "İlçe düzeyi",
            "years": "ADNKS; yıllık ilçe nüfusu",
            "unit": "kişi",
            "palette": "Blues",
            "note": "İlçe sınırıyla çalışıldığında yerel nüfus büyüklüklerini üretir.",
        },
        {
            "label": "Belediye çöplüğüne gönderilen atık haritası (il)",
            "query": "municipality dumping sites waste tonnes provinces",
            "dataflow_id": "DF_ATIK_BELEDIYE_ATIKYONETIMI_V1",
            "version": "1.0",
            "filters": "BELEDIYE_ATIK_GOSTERGE=Municipality's Dumping Sites; ATIK_TUR=Amount of Waste; UNIT_MEASURE=Tonnes",
            "title": "Belediye Çöplüğüne Gönderilen Atık",
            "level": "İl düzeyi",
            "years": "Çevre istatistikleri; belediye atık yönetimi",
            "unit": "ton",
            "palette": "Greens",
            "note": "Atık bertaraf biçimi ve çevresel baskı analizlerinde kullanılır.",
        },
        {
            "label": "Atık işleme tesislerine gönderilen atık haritası (il)",
            "query": "waste treatment facilities waste tonnes provinces",
            "dataflow_id": "DF_ATIK_BELEDIYE_ATIKYONETIMI_V1",
            "version": "1.0",
            "filters": "BELEDIYE_ATIK_GOSTERGE=Waste Treatment Facilities; ATIK_TUR=Amount of Waste; UNIT_MEASURE=Tonnes",
            "title": "Atık İşleme Tesislerine Gönderilen Atık",
            "level": "İl düzeyi",
            "years": "Çevre istatistikleri; belediye atık yönetimi",
            "unit": "ton",
            "palette": "Greens",
            "note": "Atık yönetimi altyapısının illere göre kullanımını analiz eder.",
        },
        {
            "label": "Diğer bertaraf yöntemleri atık haritası (il)",
            "query": "other disposal methods municipal waste provinces",
            "dataflow_id": "DF_ATIK_BELEDIYE_ATIKYONETIMI_V1",
            "version": "1.0",
            "filters": "BELEDIYE_ATIK_GOSTERGE=Other Disposal Methods; ATIK_TUR=Amount of Waste; UNIT_MEASURE=Tonnes",
            "title": "Diğer Bertaraf Yöntemleri Atık",
            "level": "İl düzeyi",
            "years": "Çevre istatistikleri; belediye atık yönetimi",
            "unit": "ton",
            "palette": "Greens",
            "note": "Standart dışı veya diğer atık bertaraf yollarının mekansal dağılışını gösterir.",
        },
        {
            "label": "Çekilen içme suyu miktarı haritası (il)",
            "query": "abstracted water municipal water sources provinces",
            "dataflow_id": "DF_SU_ATIKSU_BELEDIYE_CEKILEN_DAGITILAN_V1",
            "version": "1.0",
            "filters": "SU_MIKTAR=Amount of Water Abstracted by Water Sources; SU_KAYNAK_TUR=Total; ALICI_ORTAM=-; BELEDIYE_NITELIK_SU=-",
            "title": "Çekilen İçme Suyu Miktarı",
            "level": "İl düzeyi",
            "years": "Su ve atıksu istatistikleri; belediye suyu",
            "unit": "bin m³",
            "palette": "YlGnBu",
            "note": "Belediyelerin içme ve kullanma suyu çekim miktarını illere göre gösterir.",
        },
        {
            "label": "Deşarj edilen atıksu miktarı haritası (il)",
            "query": "wastewater discharged municipal sewerage provinces",
            "dataflow_id": "DF_SU_ATIKSU_BELEDIYE_CEKILEN_DAGITILAN_V1",
            "version": "1.0",
            "filters": "SU_MIKTAR=Amount of Wastewater Discharged from Municipal Sewerage by Receiving Bodies; SU_KAYNAK_TUR=-; ALICI_ORTAM=Total; BELEDIYE_NITELIK_SU=-",
            "title": "Deşarj Edilen Atıksu Miktarı",
            "level": "İl düzeyi",
            "years": "Su ve atıksu istatistikleri; belediye kanalizasyonu",
            "unit": "bin m³",
            "palette": "YlGnBu",
            "note": "Kentsel altyapı baskısı ve atıksu yönetimi için temel göstergedir.",
        },
        {
            "label": "Atıksu arıtma tesisi sayısı haritası (il)",
            "query": "municipal wastewater treatment plant number provinces",
            "dataflow_id": "DF_SU_ATIKSU_BELEDIYE_ARITMA_TESIS_V1",
            "version": "1.0",
            "filters": "TESIS_NITELIK=Number; ARITMA_TESIS_TIP=Total Treatment Plant; UNIT_MEASURE=Pure number",
            "title": "Atıksu Arıtma Tesisi Sayısı",
            "level": "İl düzeyi",
            "years": "Su ve atıksu istatistikleri; arıtma tesisi",
            "unit": "adet",
            "palette": "YlGnBu",
            "note": "Belediye atıksu arıtma altyapısının illere göre dağılışını gösterir.",
        },
        {
            "label": "Atıksu arıtma tesisi kapasitesi haritası (il)",
            "query": "municipal wastewater treatment plant capacity provinces",
            "dataflow_id": "DF_SU_ATIKSU_BELEDIYE_ARITMA_TESIS_V1",
            "version": "1.0",
            "filters": "TESIS_NITELIK=Capacity; ARITMA_TESIS_TIP=Total Treatment Plant; UNIT_MEASURE=Thousand Cubic Metre",
            "title": "Atıksu Arıtma Tesisi Kapasitesi",
            "level": "İl düzeyi",
            "years": "Su ve atıksu istatistikleri; arıtma tesisi",
            "unit": "bin m³/yıl",
            "palette": "YlGnBu",
            "note": "Atıksu arıtma kapasitesinin bölgesel farklılaşmasını gösterir.",
        },
        {
            "label": "Arıtılan atıksu miktarı haritası (il)",
            "query": "amount of water treated municipal wastewater provinces",
            "dataflow_id": "DF_SU_ATIKSU_BELEDIYE_ARITMA_TESIS_V1",
            "version": "1.0",
            "filters": "TESIS_NITELIK=Amount of Water Treated; ARITMA_TESIS_TIP=Total Treatment Plant; UNIT_MEASURE=Thousand Cubic Metre",
            "title": "Arıtılan Atıksu Miktarı",
            "level": "İl düzeyi",
            "years": "Su ve atıksu istatistikleri; arıtma tesisi",
            "unit": "bin m³",
            "palette": "YlGnBu",
            "note": "Arıtılan atıksu hacmini illere göre karşılaştırır.",
        },
        {
            "label": "Trafik kazasında ölen kişi sayısı haritası (il)",
            "query": "persons killed road traffic accidents provinces",
            "dataflow_id": "DF_TRAFIK_KAZA_OLU_YARALI_V2",
            "version": "1.0",
            "filters": "KAZA_OLUM_DURUM=Total; TRAFIK_KAZA_GOSTERGE=Number of Persons Killed; UNIT_MEASURE=Pure number",
            "title": "Trafik Kazasında Ölen Kişi Sayısı",
            "level": "İl düzeyi",
            "years": "Trafik istatistikleri; yıllık seri",
            "unit": "kişi",
            "palette": "Reds",
            "note": "Ulaşım güvenliği ve risk coğrafyası analizleri için kullanılır.",
        },
        {
            "label": "Trafik kazasında yaralanan kişi sayısı haritası (il)",
            "query": "persons injured road traffic accidents provinces",
            "dataflow_id": "DF_TRAFIK_KAZA_OLU_YARALI_V2",
            "version": "1.0",
            "filters": "KAZA_OLUM_DURUM=-; TRAFIK_KAZA_GOSTERGE=Number of Persons Injured; UNIT_MEASURE=Pure number",
            "title": "Trafik Kazasında Yaralanan Kişi Sayısı",
            "level": "İl düzeyi",
            "years": "Trafik istatistikleri; yıllık seri",
            "unit": "kişi",
            "palette": "Reds",
            "note": "Trafik güvenliği, ulaşım yoğunluğu ve kentsel risk çalışmalarında kullanılabilir.",
        },
        {
            "label": "Ölümlü-yaralanmalı trafik kazası haritası (il)",
            "query": "accidents involving death or injury provinces",
            "dataflow_id": "DF_TRAFIK_KAZA_OLU_YARALI_V2",
            "version": "1.0",
            "filters": "KAZA_OLUM_DURUM=-; TRAFIK_KAZA_GOSTERGE=Number of Accidents Involving Death or Injury; UNIT_MEASURE=Pure number",
            "title": "Ölümlü-Yaralanmalı Trafik Kazası",
            "level": "İl düzeyi",
            "years": "Trafik istatistikleri; yıllık seri",
            "unit": "adet",
            "palette": "Reds",
            "note": "Kaza şiddeti ve ulaşım güvenliği örüntülerini il düzeyinde gösterir.",
        },
        {
            "label": "Traktör sayısı haritası (il)",
            "query": "tractor count by province December",
            "dataflow_id": "DF_MOTORLU_KARA_TASIT_ILLER_V3",
            "version": "1.0",
            "filters": "AY=December; ARAC_TUR=Tractor; UNIT_MEASURE=Pure number",
            "title": "Traktör Sayısı",
            "level": "İl düzeyi",
            "years": "Ulaşım istatistikleri; Aralık ayı",
            "unit": "adet",
            "palette": "Greys",
            "note": "Tarım coğrafyası, kırsal mekan ve tarımsal makineleşme için kullanılabilir.",
        },
        {
            "label": "0-14 yaş nüfusu haritası (il)",
            "query": "child population 0-14 provinces",
            "dataflow_id": "DF_ADNKS_T35",
            "version": "1.1",
            "filters": "YAS_GRUBU=<14",
            "title": "0-14 Yaş Nüfusu",
            "level": "İl düzeyi",
            "years": "ADNKS; geniş yaş grupları",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Çocuk nüfus, okul çağı talebi ve demografik canlılık analizlerinde kullanılır.",
        },
        {
            "label": "25-29 yaş nüfusu haritası (il)",
            "query": "population age group 25-29 provinces",
            "dataflow_id": "DF_ADNKS_T16",
            "version": "1.0",
            "filters": "SEX=Total; YAS_GRUBU=25-29",
            "title": "25-29 Yaş Nüfusu",
            "level": "İl düzeyi",
            "years": "ADNKS; yaş grubu ve cinsiyet",
            "unit": "kişi",
            "palette": "YlGnBu",
            "note": "Genç yetişkin nüfus, istihdam ve göç çekim analizlerinde kullanılabilir.",
        },
        {
            "label": "65-69 yaş nüfusu haritası (il)",
            "query": "population age group 65-69 provinces",
            "dataflow_id": "DF_ADNKS_T16",
            "version": "1.0",
            "filters": "SEX=Total; YAS_GRUBU=65-69",
            "title": "65-69 Yaş Nüfusu",
            "level": "İl düzeyi",
            "years": "ADNKS; yaş grubu ve cinsiyet",
            "unit": "kişi",
            "palette": "YlOrRd",
            "note": "Yaşlı nüfusa geçiş eşiğini ve erken yaşlılık dağılışını haritalar.",
        },
        {
            "label": "İlk evlenme / evlilik sosyal yapı haritası",
            "query": "spouses province marital status before marriage",
            "dataflow_id": "DF_EVLENME_KARSILIKLI_MEDENI",
            "version": "1.0",
            "filters": "ERKEK_ONCEKI_MEDENI_DURUMU=Total; KADIN_ONCEKI_MEDENI_DURUMU=Total",
            "title": "Evlenme Sosyal Yapı",
            "level": "İl düzeyi",
            "years": "Evlenme istatistikleri; medeni durum filtresi seçilir",
            "unit": "kişi",
            "palette": "OrRd",
            "note": "Evlenme öncesi medeni durumun illere göre dağılışını analiz eder.",
        },
    ]

    ADDITIONAL_TUIK_TEMPLATE_ROWS = [
        ("Tarım ormancılık balıkçılık girişim sayısı haritası", "agriculture forestry fishing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Agriculture, forestry and fishing", "Tarım Ormancılık Balıkçılık Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greens", "Tarım, ormancılık ve balıkçılık girişimlerinin mekansal dağılışını gösterir."),
        ("Tahıl baklagil yağlı tohum girişimleri haritası", "cereals legumes oil seeds enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Growing of cereals (except rice), leguminous crops and oil seeds", "Tahıl Baklagil Yağlı Tohum Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlGn", "Tarımsal üretim deseninde tahıl, baklagil ve yağlı tohum girişimlerini analiz eder."),
        ("Sebze kavun kök yumru girişimleri haritası", "vegetables melons roots tubers enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Growing of vegetables and melons, roots and tubers", "Sebze Kavun Kök Yumru Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlGn", "Sebzecilik ve yoğun tarımsal üretim alanlarını girişim sayısı üzerinden gösterir."),
        ("Yumuşak-sert çekirdekli meyve girişimleri haritası", "pome stone fruits enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Growing of pome fruits and stone fruits", "Yumuşak ve Sert Çekirdekli Meyve Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlGn", "Meyvecilik girişimlerinin mekansal yoğunlaşmasını haritalar."),
        ("Süt sığırı yetiştiriciliği girişimleri haritası", "dairy cattle enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Raising of dairy cattle", "Süt Sığırı Yetiştiriciliği Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greens", "Süt hayvancılığı girişimlerinin bölgesel dağılışını gösterir."),
        ("Koyun keçi yetiştiriciliği girişimleri haritası", "sheep goats enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Raising of sheep and goats", "Koyun Keçi Yetiştiriciliği Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greens", "Küçükbaş hayvancılığın girişim yoğunluğunu mekansal olarak karşılaştırır."),
        ("Kümes hayvancılığı girişimleri haritası", "poultry enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Raising of poultry", "Kümes Hayvancılığı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greens", "Kümes hayvancılığı faaliyetlerinin illere göre yoğunlaşmasını gösterir."),
        ("Karma çiftçilik girişimleri haritası", "mixed farming enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Mixed farming", "Karma Çiftçilik Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greens", "Bitkisel ve hayvansal üretimi birlikte yürüten girişimlerin dağılışını haritalar."),
        ("Bitkisel üretimi destekleyici faaliyet girişimleri haritası", "support activities crop production enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Support activities for crop production", "Bitkisel Üretim Destek Faaliyetleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlGn", "Tarım hizmetleri ve bitkisel üretim destek altyapısını gösterir."),
        ("Hayvancılığı destekleyici faaliyet girişimleri haritası", "support activities animal production enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Support activities for animal production", "Hayvancılık Destek Faaliyetleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlGn", "Hayvancılık hizmetlerinin ve destek girişimlerinin mekansal dağılışını gösterir."),
        ("Ormancılık girişimleri haritası", "silviculture forestry enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Silviculture and other forestry activities", "Ormancılık Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greens", "Ormancılık faaliyetlerinin bölgesel yoğunluğunu haritalar."),
        ("Tatlı su balıkçılığı girişimleri haritası", "freshwater fishing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Freshwater fishing", "Tatlı Su Balıkçılığı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlGnBu", "İç su balıkçılığı girişimlerinin dağılışını gösterir."),
        ("Madencilik girişim sayısı haritası", "mining quarrying enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Mining and quarrying", "Madencilik Girişim Sayısı", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Madencilik ve taş ocakçılığı girişimlerinin mekansal dağılışını gösterir."),
        ("İmalat sanayi girişim sayısı haritası", "manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacturing", "İmalat Sanayi Girişim Sayısı", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "İmalat sanayi girişimlerinin bölgesel yoğunlaşmasını haritalar."),
        ("Elektrik gaz buhar iklimlendirme girişimleri haritası", "electricity gas steam air conditioning enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Electricity, gas, steam and air conditioning supply", "Elektrik Gaz Buhar İklimlendirme Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Enerji üretim ve dağıtım faaliyetlerinin girişim dağılışını gösterir."),
        ("İnşaat girişim sayısı haritası", "construction enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Construction", "İnşaat Girişim Sayısı", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "İnşaat sektöründeki girişimlerin mekansal yoğunluğunu gösterir."),
        ("Yeni doğan girişim sayısı haritası", "birth of enterprises number by province", "DF_BD_DOGUM_OLUM", "1.1", "INDICATOR=Birth Of Enterprises; GIRISIM_EKO_GOSTERGE=Number Of Enterprises", "Yeni Doğan Girişim Sayısı", "İl/bölge düzeyi", "Girişim demografisi; 2022-2024 test edildi", "adet", "Greys", "Yeni kurulan girişimlerin bölgesel girişimcilik örüntüsünü gösterir."),
        ("Kapanan girişim sayısı haritası", "death of enterprises number by province", "DF_BD_DOGUM_OLUM", "1.1", "INDICATOR=Death Of Enterprises; GIRISIM_EKO_GOSTERGE=Number Of Enterprises", "Kapanan Girişim Sayısı", "İl/bölge düzeyi", "Girişim demografisi; son çalışan yıl test edildi", "adet", "Greys", "Kapanan girişimlerin bölgesel ekonomik kırılganlık örüntüsünü gösterir."),
        ("Gıda imalatı unlu mamuller girişimleri haritası", "bread fresh pastry manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of bread; manufacture of fresh pastry goods and cakes", "Gıda İmalatı Unlu Mamuller Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Oranges", "Unlu mamuller imalatı girişimlerinin mekansal dağılışını gösterir."),
        ("Gıda imalatı değirmencilik girişimleri haritası", "grain mill products manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of grain mill products", "Gıda İmalatı Değirmencilik Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Oranges", "Değirmencilik ve tahıl işleme girişimlerini haritalar."),
        ("Gıda imalatı hazır yem girişimleri haritası", "prepared feeds farm animals manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of prepared feeds for farm animals", "Gıda İmalatı Hazır Yem Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Oranges", "Hayvancılıkla ilişkili yem sanayi girişimlerini gösterir."),
        ("Alkolsüz içecek imalatı girişimleri haritası", "soft drinks mineral waters manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of soft drinks; production of mineral waters and other bottled waters", "Alkolsüz İçecek İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Oranges", "İçecek sanayisinin mekansal yoğunluğunu gösterir."),
        ("Tekstil halı kilim imalatı girişimleri haritası", "carpets rugs manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of carpets and rugs", "Tekstil Halı Kilim İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "PuBu", "Halı ve kilim imalatı girişimlerinin bölgesel dağılışını gösterir."),
        ("Diğer tekstil imalatı girişimleri haritası", "other textiles manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of other textiles n.e.c.", "Diğer Tekstil İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "PuBu", "Tekstil sanayisinin farklı alt faaliyetlerini mekansal olarak gösterir."),
        ("Giyim dış giyim imalatı girişimleri haritası", "outerwear manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of other outerwear", "Giyim Dış Giyim İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "PuBu", "Dış giyim üretimi girişimlerinin illere göre dağılışını haritalar."),
        ("Giyim iş kıyafeti imalatı girişimleri haritası", "workwear manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of workwear", "Giyim İş Kıyafeti İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "PuBu", "İş kıyafeti üretimindeki sanayi yoğunluğunu gösterir."),
        ("Ayakkabı imalatı girişimleri haritası", "footwear manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of footwear", "Ayakkabı İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "PuBu", "Ayakkabı imalatı girişimlerinin bölgesel kümelenmesini gösterir."),
        ("Ağaç ürünleri doğrama girişimleri haritası", "builders carpentry joinery manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of other builders' carpentry and joinery", "Ağaç Ürünleri Doğrama Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrBr", "İnşaatla bağlantılı ağaç doğrama sanayisini haritalar."),
        ("Diğer ağaç ürünleri imalatı girişimleri haritası", "other wood products manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of other products of wood; manufacture of articles of cork, straw and plaiting materials", "Diğer Ağaç Ürünleri İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrBr", "Ağaç ürünleri sanayisinin mekansal dağılışını gösterir."),
        ("Kağıt karton imalatı girişimleri haritası", "paper paperboard manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of paper and paperboard", "Kağıt Karton İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrBr", "Kağıt ve karton üretimi girişimlerini haritalar."),
        ("Kimya deterjan temizlik imalatı girişimleri haritası", "soap detergents cleaning manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of soap and detergents, cleaning and polishing preparations", "Kimya Deterjan Temizlik İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrRd", "Temizlik kimyasalları imalatının bölgesel dağılışını gösterir."),
        ("Kimya plastik hammaddesi imalatı girişimleri haritası", "plastics primary forms manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of plastics in primary forms", "Kimya Plastik Hammaddesi İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrRd", "Plastik hammadde üretimi girişimlerini mekansal olarak gösterir."),
        ("Kauçuk lastik imalatı girişimleri haritası", "rubber tyres manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of rubber tyres and tubes; retreading and rebuilding of rubber tyres", "Kauçuk Lastik İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrRd", "Lastik ve kauçuk sanayi girişimlerinin dağılışını gösterir."),
        ("Plastik ambalaj imalatı girişimleri haritası", "plastic packing goods manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of plastic packing goods", "Plastik Ambalaj İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrRd", "Plastik ambalaj üretimi girişimlerini haritalar."),
        ("Plastik inşaat malzemesi imalatı girişimleri haritası", "builders ware plastic manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of builders' ware of plastic", "Plastik İnşaat Malzemesi İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrRd", "Plastik yapı malzemesi üretiminin mekansal dağılışını gösterir."),
        ("Hazır beton imalatı girişimleri haritası", "ready mixed concrete manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of ready-mixed concrete", "Hazır Beton İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "İnşaat ve sanayi ilişkisini hazır beton üretimi üzerinden gösterir."),
        ("Metal yapı parçaları imalatı girişimleri haritası", "metal structures manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of metal structures and parts of structures", "Metal Yapı Parçaları İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Metal yapı parçaları sanayisinin bölgesel dağılışını gösterir."),
        ("Metal kapı pencere imalatı girişimleri haritası", "metal doors windows manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of doors and windows of metal", "Metal Kapı Pencere İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Metal doğrama üretimi girişimlerini haritalar."),
        ("Takım aletleri imalatı girişimleri haritası", "tools manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of tools", "Takım Aletleri İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Takım aleti imalatı girişimlerinin mekansal dağılışını gösterir."),
        ("Elektrik motoru jeneratör imalatı girişimleri haritası", "electric motors generators manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of electric motors, generators and transformers", "Elektrik Motoru Jeneratör İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Elektrikli ekipman imalatının bölgesel yoğunlaşmasını gösterir."),
        ("Pompa kompresör imalatı girişimleri haritası", "pumps compressors manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of other pumps and compressors", "Pompa Kompresör İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Makine imalatı içinde pompa ve kompresör üretimini haritalar."),
        ("Kaldırma taşıma ekipmanı imalatı girişimleri haritası", "lifting handling equipment manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of lifting and handling equipment", "Kaldırma Taşıma Ekipmanı İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Lojistik ve sanayi altyapısı ile ilişkili makine imalatını gösterir."),
        ("Tarım ormancılık makinesi imalatı girişimleri haritası", "agricultural forestry machinery manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of agricultural and forestry machinery", "Tarım Ormancılık Makinesi İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Tarımsal makine sanayisinin mekansal dağılışını gösterir."),
        ("Gıda içecek makineleri imalatı girişimleri haritası", "food beverage tobacco processing machinery manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of machinery for food, beverage and tobacco processing", "Gıda İçecek Makineleri İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Gıda sanayisiyle ilişkili makine üretimini haritalar."),
        ("Motorlu taşıt parça imalatı girişimleri haritası", "motor vehicle parts manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of other parts and accessories for motor vehicles", "Motorlu Taşıt Parça İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Otomotiv yan sanayi girişimlerinin bölgesel dağılışını gösterir."),
        ("Ofis mağaza mobilyası imalatı girişimleri haritası", "office shop furniture manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of office and shop furniture", "Ofis Mağaza Mobilyası İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrBr", "Ofis ve mağaza mobilyası imalatı girişimlerini haritalar."),
        ("Mutfak mobilyası imalatı girişimleri haritası", "kitchen furniture manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of kitchen furniture", "Mutfak Mobilyası İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrBr", "Mutfak mobilyası üretimindeki mekansal yoğunluğu gösterir."),
        ("Diğer mobilya imalatı girişimleri haritası", "other furniture manufacturing enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Manufacture of other furniture", "Diğer Mobilya İmalatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "YlOrBr", "Mobilya sanayisinin geniş bölgesel dağılışını haritalar."),
        ("Elektrik üretimi girişimleri haritası", "production of electricity enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Production of electricity", "Elektrik Üretimi Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Elektrik üretim faaliyetlerinin mekansal dağılışını gösterir."),
        ("Elektrik dağıtımı girişimleri haritası", "distribution of electricity enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Distribution of electricity", "Elektrik Dağıtımı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Elektrik dağıtımı alanındaki girişimlerin bölgesel dağılışını gösterir."),
        ("Konut-dışı bina inşaatı girişimleri haritası", "residential non-residential buildings construction enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Construction of residential and non-residential buildings", "Konut-Dışı Bina İnşaatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Bina inşaatı girişimlerinin mekansal dağılışını gösterir."),
        ("Yol otoyol inşaatı girişimleri haritası", "roads motorways construction enterprises", "DF_BR_FAALIYET_GIRISIM", "1.0", "ACTIVITY_NACE_REV2=Construction of roads and motorways", "Yol Otoyol İnşaatı Girişimleri", "İl/bölge düzeyi", "Bölgesel iş kayıtları; 2022-2024 test edildi", "adet", "Greys", "Ulaşım altyapısı inşaat girişimlerini bölgesel olarak gösterir."),
    ]

    def _map_templates(self):
        templates = list(self.MAP_TEMPLATES)
        for row in self.ADDITIONAL_TUIK_TEMPLATE_ROWS:
            label, query, dataflow_id, version, filters, title, level, years, unit, palette, note = row
            templates.append({
                "label": label,
                "query": query,
                "dataflow_id": dataflow_id,
                "version": version,
                "filters": filters,
                "title": title,
                "level": level,
                "years": years,
                "unit": unit,
                "palette": palette,
                "note": note,
            })
        return templates

    def __init__(self, iface, plugin_dir, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.loader = DataLoader(plugin_dir)
        self.gadm = GadmManager(plugin_dir)
        self.cache = CacheManager(plugin_dir)
        self.reports = ReportGenerator()
        self.tuik = TuikSdmxClient(os.path.join(plugin_dir, "data", "cache", "tuik"))
        self.manual_path = None
        self.manual_headers = []
        self.online_results = []
        self.online_data = None
        self.online_meta = None
        self.generated_exports = []
        self.setWindowTitle("TurkeyThesisMap - Türkiye beşeri coğrafya haritası üreticisi")
        self.resize(960, 680)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self._tab_workspace()
        self._tab_data()
        self._tab_manual_data()
        self._tab_style()
        self._tab_generate()
        self._tab_export()

    def _style_button(self, button, kind="primary"):
        colors = {
            "primary": ("#1769aa", "#ffffff"),
            "success": ("#1f7a3f", "#ffffff"),
            "warning": ("#b35c00", "#ffffff"),
            "danger": ("#b3261e", "#ffffff"),
            "neutral": ("#4f5b62", "#ffffff"),
        }
        bg, fg = colors.get(kind, colors["primary"])
        button.setStyleSheet(
            "QPushButton { background:%s; color:%s; border:0; border-radius:4px; padding:6px 10px; font-weight:600; } "
            "QPushButton:hover { background:%s; } "
            "QPushButton:disabled { background:#b0b0b0; color:#f2f2f2; }" % (bg, fg, bg)
        )

    def _add_scroll_tab(self, widget, title):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        self.tabs.addTab(scroll, title)

    def _tab_workspace(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        intro = QLabel("Bu sekmede haritanın neresi için üretileceğini, hangi ölçekte çalışacağını ve çıktıların nereye kaydedileceğini belirlersiniz. Yeni başlayanlar için önerilen akış: İl düzeyi + Türkiye, EPSG:3857, masaüstü çıktı klasörü.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        area_box = QGroupBox("1. Harita Kapsamı")
        area_form = QFormLayout(area_box)
        self.province_combo = QComboBox()
        self.province_combo.setEditable(True)
        self.province_combo.addItems(["Türkiye"] + TR_IL_LISTESI)
        self.level_combo = QComboBox()
        self.level_combo.addItems(["İl düzeyi", "İlçe düzeyi"])
        self.district_combo = QComboBox()
        self.district_combo.setEnabled(False)
        self.level_combo.currentTextChanged.connect(self._on_level_changed)
        self.province_combo.currentTextChanged.connect(self._refresh_districts)
        area_help = QLabel("İl düzeyi Türkiye seçiliyken 81 ili karşılaştırır. İlçe düzeyi için önce belirli bir il seçin; eklenti o ilin ilçelerini yükler.")
        area_help.setWordWrap(True)
        area_form.addRow(area_help)
        area_form.addRow("Kapsam", self.province_combo)
        area_form.addRow("Harita ölçeği", self.level_combo)
        area_form.addRow("İlçe seçimi", self.district_combo)
        layout.addWidget(area_box)

        output_box = QGroupBox("2. Çıktı ve Proje")
        output_form = QFormLayout(output_box)
        self.output_edit = QLineEdit(os.path.join(os.path.expanduser("~"), "Desktop", "TurkeyThesisMap_Output"))
        browse = QPushButton("Klasör Seç")
        self._style_button(browse, "neutral")
        browse.clicked.connect(self._choose_output)
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_edit)
        out_row.addWidget(browse)
        self.project_edit = QLineEdit("turkiye_beseri_cografya_haritasi")
        output_help = QLabel("Her üretimde PDF, proje, veri ve rapor dosyaları bu klasörün içinde proje adına göre düzenlenir. Proje adında Türkçe karakter kullanabilirsiniz.")
        output_help.setWordWrap(True)
        output_form.addRow(output_help)
        output_form.addRow("Çıktı klasörü", out_row)
        output_form.addRow("Proje adı", self.project_edit)
        layout.addWidget(output_box)

        crs_box = QGroupBox("3. Koordinat Sistemi ve Sınır Verisi")
        crs_form = QFormLayout(crs_box)
        self.crs_combo = QComboBox()
        self.crs_combo.addItems([
            "EPSG:3857 - Web Mercator (altlık haritalarla uyumlu)",
            "EPSG:5254 - Türkiye Ulusal Grid",
            "EPSG:4326 - WGS84",
            "EPSG:3457 - özel CRS (Web Mercator değil)",
        ])
        self.crs_help = QLabel("Varsayılan koordinat sistemi EPSG:3857 Web Mercator olarak ayarlandı. Google/OSM/XYZ altlık haritalarla en uyumlu seçim budur.")
        self.crs_help.setWordWrap(True)
        refresh = QPushButton("GADM İl/İlçe Listesini Yükle")
        self._style_button(refresh, "primary")
        refresh.clicked.connect(self._load_gadm_places)
        crs_form.addRow("Koordinat sistemi", self.crs_combo)
        crs_form.addRow("", self.crs_help)
        crs_form.addRow(refresh)
        layout.addWidget(crs_box)
        self._add_scroll_tab(tab, "1. Çalışma Alanı")

    def _tab_data(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.data_note = QLabel("Bu sekmede önce TÜİK tablosunu bulup haritaya hazır hale getirirsiniz. Basit akış: konu ara, tablo seç, seçenekleri yükle, yıl gir, gerekiyorsa göstergeyi filtreye ekle, veriyi hazırla.")
        self.data_note.setWordWrap(True)
        layout.addWidget(self.data_note)

        template_box = QGroupBox("1. Beşeri Coğrafya Hazır Şablonları")
        template_form = QFormLayout(template_box)
        template_help = QLabel("Hiçbir ayarla uğraşmadan buradan başlayın. Şablonlar arama, tablo ve temel filtreleri otomatik doldurur; yalnızca yılı seçmeniz gerekir.")
        template_help.setWordWrap(True)
        template_form.addRow(template_help)
        template_row = QHBoxLayout()
        self.template_category_combo = QComboBox()
        self.template_category_combo.addItems([
            "Tümü",
            "Nüfus ve Demografi",
            "Göç, Doğum Yeri ve Kayıt",
            "Hanehalkı ve Sosyal Yapı",
            "Doğum, Evlenme ve Boşanma",
            "Eğitim",
            "Konut ve Kentleşme",
            "Ulaşım",
            "Çevre ve Altyapı",
            "Ekonomi",
            "Tarım",
            "Sanayi",
        ])
        self.template_category_combo.currentIndexChanged.connect(self._refresh_template_combo)
        self.template_combo = QComboBox()
        self._refresh_template_combo()
        self.template_apply_btn = QPushButton("Şablonu Uygula")
        self._style_button(self.template_apply_btn, "success")
        self.template_apply_btn.clicked.connect(self._apply_template)
        self.template_help_btn = QPushButton("?")
        self.template_help_btn.setFixedWidth(32)
        self.template_help_btn.clicked.connect(self._show_template_help)
        template_row.addWidget(self.template_combo)
        template_row.addWidget(self.template_apply_btn)
        template_row.addWidget(self.template_help_btn)
        template_form.addRow("Kategori", self.template_category_combo)
        template_form.addRow("Şablon", template_row)
        layout.addWidget(template_box)

        search_box = QGroupBox("2. TÜİK Tablosu Bul")
        search_form = QFormLayout(search_box)
        search_help = QLabel("Arama için Türkçe veya İngilizce anahtar kelime yazabilirsiniz. Örnek: nüfus yoğunluğu, population density, göç, migration, eğitim, education. Boş arama tüm TÜİK tablolarını listeler.")
        search_help.setWordWrap(True)
        search_form.addRow(search_help)
        search_row = QHBoxLayout()
        self.online_query_edit = QLineEdit()
        self.online_query_edit.setPlaceholderText("Örn: nüfus yoğunluğu, population density, göç, migration")
        self.online_search_btn = QPushButton("Ara / Tümünü Listele")
        self._style_button(self.online_search_btn, "primary")
        self.online_search_btn.clicked.connect(self._tuik_search)
        search_row.addWidget(self.online_query_edit)
        search_row.addWidget(self.online_search_btn)
        search_form.addRow("Konu", search_row)
        layout.addWidget(search_box)

        table_box = QGroupBox("3. Tabloyu Kontrol Et")
        table_form = QFormLayout(table_box)
        self.online_result_combo = QComboBox()
        self.online_result_combo.setMinimumWidth(720)
        self.online_result_combo.setMaxVisibleItems(24)
        self.online_result_combo.currentIndexChanged.connect(self._online_selection_changed)
        self.online_description_label = QLabel("TÜİK tablosu seçildiğinde açıklaması burada gösterilir.")
        self.online_description_label.setWordWrap(True)
        self.online_meta_btn = QPushButton("Tablo Seçeneklerini Göster")
        self._style_button(self.online_meta_btn, "neutral")
        self.online_meta_btn.clicked.connect(self._tuik_meta)
        table_form.addRow("Tablo", self.online_result_combo)
        table_form.addRow("Açıklama", self.online_description_label)
        table_form.addRow(self.online_meta_btn)
        layout.addWidget(table_box)

        option_box = QGroupBox("4. Filtre Seç")
        option_form = QFormLayout(option_box)
        filter_intro = QLabel("Aynı TÜİK tablosunda birden fazla gösterge/cinsiyet/yaş varsa burada tek seri seçilir. En iyi koroplet harita için tek gösterge ve toplam cinsiyet/yaş tercih edin.")
        filter_intro.setWordWrap(True)
        option_form.addRow(filter_intro)
        option_row = QHBoxLayout()
        self.online_dimension_combo = QComboBox()
        self.online_value_combo = QComboBox()
        self.online_add_filter_btn = QPushButton("Seçimi Filtreye Ekle")
        self._style_button(self.online_add_filter_btn, "warning")
        self.online_add_filter_btn.clicked.connect(self._tuik_add_filter)
        self.online_filter_help_btn = QPushButton("?")
        self.online_filter_help_btn.setFixedWidth(32)
        self.online_filter_help_btn.clicked.connect(self._show_filter_help)
        option_row.addWidget(self.online_dimension_combo)
        option_row.addWidget(self.online_value_combo)
        option_row.addWidget(self.online_add_filter_btn)
        option_row.addWidget(self.online_filter_help_btn)
        self.online_dimension_combo.currentIndexChanged.connect(self._online_dimension_changed)
        option_form.addRow("Filtre seç", option_row)
        self.online_filter_edit = QLineEdit()
        self.online_filter_edit.setPlaceholderText("Örn: ADNKS_GOSTERGE=Population density; SEX=Total")
        self.online_filter_help = QLabel("Bir tabloda birden fazla gösterge varsa en iyi harita için tek gösterge seçin. Genellikle 'Indicator/Gösterge' alanı seçilir; cinsiyet, yaş veya kır-kent gibi alanlarda 'Total/Toplam' tercih edilir.")
        self.online_filter_help.setWordWrap(True)
        option_form.addRow("Aktif filtre", self.online_filter_edit)
        option_form.addRow("", self.online_filter_help)
        layout.addWidget(option_box)

        year_box = QGroupBox("5. Yıl Seç ve Veriyi Hazırla")
        year_form = QFormLayout(year_box)
        year_help = QLabel("Tek yıl için yalnızca başlangıç yılı yazın. Örnek: 2021. Aralık için başlangıç ve bitiş yılı yazın. Örnek: 2011 - 2020.")
        year_help.setWordWrap(True)
        year_form.addRow(year_help)
        self.online_start_edit = QLineEdit()
        self.online_start_edit.setPlaceholderText("Örn: 2021")
        self.online_end_edit = QLineEdit()
        self.online_end_edit.setPlaceholderText("Örn: 2020")
        period_row = QHBoxLayout()
        start_label = QLabel("Başlangıç yılı:")
        end_label = QLabel("Bitiş yılı:")
        period_row.addWidget(start_label)
        period_row.addWidget(self.online_start_edit)
        period_row.addWidget(end_label)
        period_row.addWidget(self.online_end_edit)
        year_form.addRow(period_row)
        self.online_fetch_btn = QPushButton("Online Veriyi Haritaya Hazırla")
        self._style_button(self.online_fetch_btn, "success")
        self.online_fetch_btn.clicked.connect(self._tuik_fetch)
        self.online_info_label = QLabel("Önce bir tablo seçin, sonra 'Tablo Seçeneklerini Göster' düğmesine basın.")
        self.online_info_label.setWordWrap(True)
        year_form.addRow(self.online_fetch_btn)
        year_form.addRow(self.online_info_label)
        layout.addWidget(year_box)

        self._add_scroll_tab(tab, "2. Veri Seçimi")

    def _tab_manual_data(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(self._build_manual_data_box())
        self._add_scroll_tab(tab, "3. Manuel Veri")

    def _build_manual_data_box(self):
        manual = QGroupBox("Manuel TÜİK Excel/CSV")
        form = QFormLayout(manual)
        manual_help = QLabel("TÜİK'ten indirilen veya sizin hazırladığınız Excel/CSV dosyaları için kullanılır. En sağlıklı yapı: Yıl | İl/İlçe | Gösterge/Kategori | Değer. Eklenti sütunları otomatik tahmin eder; yanlış tahmin varsa buradan düzeltebilirsiniz.")
        manual_help.setWordWrap(True)
        form.addRow(manual_help)
        pick = QPushButton("TÜİK Excel/CSV Yükle")
        self._style_button(pick, "primary")
        pick.clicked.connect(self._pick_manual)
        self.manual_loc_combo = QComboBox()
        self.manual_val_combo = QComboBox()
        self.manual_year_col_combo = QComboBox()
        self.manual_year_combo = QComboBox()
        self.manual_start_year_edit = QLineEdit()
        self.manual_start_year_edit.setPlaceholderText("Örn: 1960")
        self.manual_end_year_edit = QLineEdit()
        self.manual_end_year_edit.setPlaceholderText("Örn: 2020")
        self.manual_filter_col_combo = QComboBox()
        self.manual_filter_value_combo = QComboBox()
        self.preview = QTableWidget(0, 0)
        form.addRow(pick)
        form.addRow("İl/İlçe sütunu", self.manual_loc_combo)
        form.addRow("Değer sütunu", self.manual_val_combo)
        form.addRow("Yıl sütunu", self.manual_year_col_combo)
        form.addRow("Tek yıl", self.manual_year_combo)
        manual_range = QHBoxLayout()
        manual_range.addWidget(self.manual_start_year_edit)
        manual_range.addWidget(self.manual_end_year_edit)
        form.addRow("Yıl aralığı", manual_range)
        form.addRow("Gösterge/kategori sütunu", self.manual_filter_col_combo)
        form.addRow("Gösterge/kategori değeri", self.manual_filter_value_combo)
        form.addRow("Ön izleme", self.preview)
        return manual

    def _tab_style(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        style_intro = QLabel("Bu sekme haritanın görünümünü belirler. Akademik çıktı için dengeli renk paleti, 5 sınıf ve açık sınır çizgisi genellikle iyi sonuç verir.")
        style_intro.setWordWrap(True)
        layout.addRow(style_intro)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Profesyonel", "Akademik", "Dark", "Minimal", "Yüksek Kontrast"])
        self.palette_combo = QComboBox()
        self.palette_options = [
            ("Blues - düşükten yükseğe mavi tonları", "Blues"),
            ("Reds - düşükten yükseğe kırmızı tonları", "Reds"),
            ("Greens - düşükten yükseğe yeşil tonları", "Greens"),
            ("Oranges - düşükten yükseğe turuncu tonları", "Oranges"),
            ("Purples - düşükten yükseğe mor tonları", "Purples"),
            ("Greys - siyah beyaz akademik çıktı", "Greys"),
            ("YlOrRd - sarıdan kırmızıya güçlü vurgu", "YlOrRd"),
            ("YlGnBu - sarı/yeşilden maviye", "YlGnBu"),
            ("BuPu - maviden mora", "BuPu"),
            ("OrRd - turuncudan kırmızıya", "OrRd"),
            ("RdBu - düşük/yüksek karşılaştırma", "RdBu"),
            ("RdYlGn - kırmızı/sarı/yeşil karşılaştırma", "RdYlGn"),
            ("BrBG - kahverengi/yeşil karşılaştırma", "BrBG"),
            ("PiYG - pembe/yeşil karşılaştırma", "PiYG"),
            ("PRGn - mor/yeşil karşılaştırma", "PRGn"),
        ]
        for label, _ in self.palette_options:
            self.palette_combo.addItem(label)
        self.reverse_check = QCheckBox("Renkleri ters çevir")
        self.border_color = "#666666"
        border_btn = QPushButton("Sınır Rengi")
        self._style_button(border_btn, "neutral")
        border_btn.clicked.connect(self._choose_border)
        self.border_width = QLineEdit("0.35")
        self.labels_check = QCheckBox("Etiket göster")
        self.label_mode_combo = QComboBox()
        self.label_mode_combo.addItems(["İl/ilçe adı", "İl/ilçe adı + değer", "Sadece değer"])
        self.label_size = QSpinBox()
        self.label_size.setRange(6, 24)
        self.label_size.setValue(9)
        self.value_unit_edit = QLineEdit()
        self.value_unit_edit.setPlaceholderText("Örn: kişi/km², %, ‰, kişi")
        self.legend_title_edit = QLineEdit()
        self.legend_title_edit.setPlaceholderText("Boşsa veri adından otomatik üretilir")
        self.class_combo = QComboBox()
        self.class_combo.addItems(["Doğal Aralar (Jenks)", "Kantil", "Eşit Aralık", "Standart Sapma", "Manuel"])
        self.class_count = QComboBox()
        self.class_count.addItems(["3", "4", "5", "6", "7", "8", "9", "10"])
        self.class_count.setCurrentText("5")
        self.manual_breaks = QLineEdit()
        self.neighbor_check = QCheckBox("QGIS'teki görünür altlık/bağlam katmanlarını göster")
        self.neighbor_check.setChecked(True)
        self.location_map_check = QCheckBox("Konum haritası")
        self.page_combo = QComboBox()
        self.page_combo.addItems(["A4", "A3", "A2"])
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Yatay", "Dikey"])
        self.title_edit = QLineEdit()
        self.north_check = QCheckBox("Kuzey oku")
        self.north_check.setChecked(True)
        self.scale_check = QCheckBox("Ölçek çubuğu")
        self.scale_check.setChecked(True)
        self.legend_check = QCheckBox("Dinamik lejant")
        self.legend_check.setChecked(True)
        self.manual_legend_check = QCheckBox("Manuel lejant")
        self.manual_legend_check.setChecked(False)
        self._add_section_header(layout, "Görsel Tema ve Renk", "Önce genel harita dili seçilir. Tek yönlü değerlerde mavi/yeşil/turuncu, iki uçlu karşılaştırmalarda RdBu veya RdYlGn daha okunaklıdır.")
        self._add_explained_row(layout, "Tema", self.theme_combo, "Genel görsel yoğunluğu belirler. Profesyonel ve akademik rapor çıktıları için önerilir.")
        self._add_explained_row(layout, "Renk paleti", self.palette_combo, "Değerler küçükten büyüğe bu renk dizisine boyanır. Sequential paletler tek yönlü veriler, diverging paletler iki uçlu karşılaştırmalar içindir.")
        self._add_explained_row(layout, "", self.reverse_check, "Yüksek değerlerin açık, düşük değerlerin koyu görünmesini istiyorsanız renkleri ters çevirin.")
        self._add_section_header(layout, "Sınırlar ve Etiketler", "Poligon sınırı ve harita üzerindeki yazılar burada ayarlanır. İlçe haritalarında çok kalabalık olacağı için etiketleri kapalı tutmak genelde daha iyi sonuç verir.")
        self._add_explained_row(layout, "Sınır", border_btn, "İl/ilçe poligonlarının çizgi rengidir.")
        self._add_explained_row(layout, "Sınır kalınlığı", self.border_width, "Poligon sınır çizgisi kalınlığıdır. 0.2-0.5 arası akademik haritalar için uygundur.")
        self._add_explained_row(layout, "", self.labels_check, "Açılırsa il/ilçe adları harita üzerinde gösterilir. Yoğun ilçe haritalarında kapalı tutmak daha okunaklı olabilir.")
        self._add_explained_row(layout, "Etiket içeriği", self.label_mode_combo, "Harita üzerinde yalnız ad, yalnız değer veya ad+değer gösterebilirsiniz.")
        self._add_explained_row(layout, "Etiket font", self.label_size, "Harita üzerindeki il/ilçe adı yazılarının punto büyüklüğüdür.")
        self._add_section_header(layout, "Lejant ve Sınıflandırma", "Lejantın doğru okunması için birim, sınıf sayısı ve sınıflandırma yöntemi birlikte düşünülmelidir. 5 sınıf çoğu akademik haritada dengeli görünür.")
        self._add_explained_row(layout, "Değer birimi", self.value_unit_edit, "Lejant ve etiketlerde görünen ölçü birimidir. Örn: kişi/km², %, ‰, kişi.")
        self._add_explained_row(layout, "Lejant başlığı", self.legend_title_edit, "Boş bırakılırsa harita adı ve birime göre otomatik başlık üretilir.")
        self._add_explained_row(layout, "Sınıflandırma", self.class_combo, "Sayısal değerleri renk sınıflarına ayırma yöntemidir. Jenks doğal kümeleri, kantil eşit sayıda alanı, eşit aralık sabit değer aralıklarını kullanır.")
        self._add_explained_row(layout, "Sınıf sayısı", self.class_count, "Lejantta kaç değer aralığı olacağını belirler. 5 sınıf çoğu akademik harita için dengelidir.")
        self._add_explained_row(layout, "Manuel sınırlar", self.manual_breaks, "Sınıflandırma 'Manuel' ise sınıf eşiklerini virgülle yazın. Örn: 10,25,50,100")
        self._add_section_header(layout, "Layout Bileşenleri", "Sayfa, başlık, kuzey oku, ölçek çubuğu, lejant ve konum haritası bu bölümde açılıp kapatılır. Çıktı okunaklı değilse önce sayfa boyutunu A3 yapın.")
        self._add_explained_row(layout, "", self.neighbor_check, "Açıkken QGIS Layers panelinde görünür olan altlık/uydu/bağlam katmanları layout haritasına dahil edilir. Kapalıysa yalnızca üretilen tematik katman çizilir.")
        self._add_explained_row(layout, "", self.location_map_check, "Layout içinde küçük Türkiye konum haritası kullanmak içindir.")
        self._add_explained_row(layout, "Sayfa", self.page_combo, "PDF/layout kağıt boyutudur.")
        self._add_explained_row(layout, "Yön", self.orientation_combo, "Yatay geniş alanlarda, dikey dar alanlarda daha iyi sonuç verir.")
        self._add_explained_row(layout, "Başlık", self.title_edit, "Boş bırakılırsa veri adı, kapsam ve yıl ile otomatik başlık üretilir.")
        self._add_explained_row(layout, "", self.north_check, "Layout'a kuzey oku ekler.")
        self._add_explained_row(layout, "", self.scale_check, "Layout'a kilometre ölçek çubuğu ekler.")
        self._add_explained_row(layout, "", self.legend_check, "Renk sınıflarını açıklayan dinamik lejant ekler.")
        self._add_explained_row(layout, "", self.manual_legend_check, "Açılırsa QGIS lejantı yerine sade manuel lejant kullanılır.")
        self._add_scroll_tab(tab, "4. Harita Ayarları")

    def _tab_generate(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.generate_btn = QPushButton("Seçili Haritaları Üret")
        self._style_button(self.generate_btn, "success")
        self.generate_btn.setMinimumHeight(42)
        self.generate_btn.clicked.connect(self.generate_maps)
        self.stop_btn = QPushButton("Üretimi Durdur")
        self._style_button(self.stop_btn, "danger")
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("Önbelleği Temizle")
        self._style_button(self.clear_btn, "warning")
        self.clear_btn.clicked.connect(self.clear_cache)
        buttons = QHBoxLayout()
        buttons.addWidget(self.generate_btn)
        buttons.addWidget(self.stop_btn)
        buttons.addWidget(self.clear_btn)
        self.progress = QProgressBar()
        self.status = QLabel("Hazır")
        self.cache_label = QLabel()
        self.generated_list = QListWidget()
        layout.addLayout(buttons)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(self.cache_label)
        layout.addWidget(self.generated_list)
        self._add_scroll_tab(tab, "5. Üretim & Temizlik")

    def _tab_export(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        intro = QLabel("Bu sekmede üretilecek teslim dosyalarını seçersiniz. Basit kullanım için PDF + QGIS Projesi + ZIP açık kalsın. PNG, GeoPackage ve rapor çıktıları sunum, düzenleme veya veri teslimi gerektiğinde eklenir.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        map_box = QGroupBox("1. Harita Çıktıları")
        map_form = QFormLayout(map_box)
        self.pdf_check = QCheckBox("PDF")
        self.pdf_check.setChecked(True)
        self.png_check = QCheckBox("PNG")
        self.svg_check = QCheckBox("SVG")
        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["150", "300", "600"])
        self.dpi_combo.setCurrentText("300")
        map_form.addRow(self.pdf_check)
        map_form.addRow(self.png_check)
        map_form.addRow(self.svg_check)
        map_form.addRow("PNG DPI", self.dpi_combo)
        dpi_help = QLabel("150 DPI hızlı önizleme, 300 DPI rapor, 600 DPI baskı için uygundur.")
        dpi_help.setWordWrap(True)
        map_form.addRow("", dpi_help)
        layout.addWidget(map_box)

        project_box = QGroupBox("2. Düzenlenebilir Proje ve Veri")
        project_form = QFormLayout(project_box)
        self.qgz_check = QCheckBox("QGIS Projesi .qgz")
        self.qgz_check.setChecked(True)
        self.gpkg_check = QCheckBox("Vektör verileri GeoPackage")
        project_form.addRow(self.qgz_check)
        project_form.addRow(self.gpkg_check)
        project_help = QLabel("QGIS projesi haritayı sonradan düzenlemek için, GeoPackage ise boyanan il/ilçe katmanını başka projelerde kullanmak için verilir.")
        project_help.setWordWrap(True)
        project_form.addRow("", project_help)
        layout.addWidget(project_box)

        report_box = QGroupBox("3. Rapor ve İstatistik")
        report_form = QFormLayout(report_box)
        self.csv_check = QCheckBox("CSV istatistik tablosu")
        self.html_check = QCheckBox("HTML rapor")
        self.txt_check = QCheckBox("TXT yorum metni")
        report_form.addRow(self.csv_check)
        report_form.addRow(self.html_check)
        report_form.addRow(self.txt_check)
        report_help = QLabel("CSV sayısal kontrol için, HTML hızlı rapor için, TXT ise harita yorum metnini ayrı teslim etmek için kullanılır.")
        report_help.setWordWrap(True)
        report_form.addRow("", report_help)
        layout.addWidget(report_box)

        package_box = QGroupBox("4. Teslim Paketi")
        package_form = QFormLayout(package_box)
        self.zip_check = QCheckBox("ZIP teslim paketi")
        self.zip_check.setChecked(True)
        export_btn = QPushButton("Seçili Çıktıları Dışa Aktar")
        self._style_button(export_btn, "primary")
        export_btn.clicked.connect(self._export_outputs)
        package_form.addRow(self.zip_check)
        package_form.addRow(export_btn)
        package_help = QLabel("ZIP seçiliyse üretilen PDF, proje, rapor ve veri klasörleri tek teslim paketinde toplanır.")
        package_help.setWordWrap(True)
        package_form.addRow("", package_help)
        layout.addWidget(package_box)
        self._add_scroll_tab(tab, "6. Dışa Aktarma & Rapor")

    def _add_explained_row(self, layout, label, widget, help_text):
        layout.addRow(label, widget)
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color:#555; font-size:10px;")
        layout.addRow("", help_label)

    def _add_section_header(self, layout, title, help_text):
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight:700; color:#1f2933; margin-top:10px;")
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color:#555; font-size:10px;")
        layout.addRow(title_label)
        layout.addRow(help_label)

    def _choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Çıktı klasörü seç", self.output_edit.text())
        if folder:
            self.output_edit.setText(folder)

    def _choose_border(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.border_color = color.name()

    def _show_error(self, title, summary, exc=None, steps=None):
        message = summary
        if exc:
            message += "\n\nTeknik ayrıntı: %s" % exc
        if steps:
            message += "\n\nNe yapmalısınız?\n" + "\n".join("%d. %s" % (i + 1, step) for i, step in enumerate(steps))
        QMessageBox.critical(self, title, message)

    def _load_gadm_places(self):
        try:
            self.status.setText("GADM sınırları hazırlanıyor...")
            provinces = self.gadm.provinces()
            self.province_combo.clear()
            self.province_combo.addItem("Türkiye")
            self.province_combo.addItems(provinces)
            self._refresh_districts()
            QMessageBox.information(self, "TurkeyThesisMap", "GADM il listesi yüklendi.")
        except Exception as exc:
            self._show_error(
                "GADM Hatası",
                "İl/ilçe sınır listesi hazırlanamadı.",
                exc,
                ["İnternet bağlantınızı kontrol edin.", "Eklenti klasöründe data/gadm yazma izni olduğundan emin olun.", "Tekrar 'GADM İl/İlçe Listesini Yükle' düğmesine basın."]
            )
        finally:
            self.status.setText("Hazır")

    def _pick_manual(self):
        path, _ = QFileDialog.getOpenFileName(self, "TÜİK Excel/CSV seç", "", "Veri dosyaları (*.xlsx *.csv)")
        if not path:
            return
        try:
            headers, rows = self.loader.load_manual_preview(path)
            all_rows = self.loader.parser.read_table(path)
            header_index = self.loader.parser._find_header_row(all_rows) if all_rows else 0
            data_rows = all_rows[header_index + 1:]
        except Exception as exc:
            self._show_error(
                "Excel/CSV Okuma Hatası",
                "Dosya okunamadı veya tablo başlığı bulunamadı.",
                exc,
                ["Dosyanın .xlsx veya .csv olduğundan emin olun.", "Tabloda il/ilçe ve sayısal değer sütunu bulunduğunu kontrol edin.", "TÜİK dosyasında birden fazla sayfa varsa haritalanacak tabloyu ilk sayfaya taşıyın."]
            )
            return
        self.manual_path = path
        self.manual_headers = headers
        for combo in (self.manual_loc_combo, self.manual_val_combo, self.manual_year_col_combo, self.manual_filter_col_combo):
            combo.clear()
            combo.addItem("")
            combo.addItems(headers)
        self._auto_select_manual_columns(headers)
        self._refresh_manual_filter_values(data_rows)
        self.manual_filter_col_combo.currentTextChanged.connect(lambda _: self._refresh_manual_filter_values(data_rows))
        self.manual_year_col_combo.currentTextChanged.connect(lambda _: self._refresh_manual_filter_values(data_rows))
        self.preview.setColumnCount(len(headers))
        self.preview.setHorizontalHeaderLabels(headers)
        self.preview.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row[:len(headers)]):
                self.preview.setItem(r, c, QTableWidgetItem(str(value)))

    def _auto_select_manual_columns(self, headers):
        def choose(combo, candidates):
            for wanted in candidates:
                for idx, header in enumerate(headers, 1):
                    hkey = normalize_key(header)
                    if normalize_key(wanted) == hkey or normalize_key(wanted) in hkey:
                        combo.setCurrentIndex(idx)
                        return
        choose(self.manual_loc_combo, ["ilce", "ilçe", "il adı", "il adi", "göç alan il adı", "ikamet yeri", "düzey", "duzey", "province"])
        choose(self.manual_val_combo, ["değer", "deger", "toplam", "nüfus", "nufus", "oran", "hız", "hiz", "sayı", "sayi"])
        choose(self.manual_year_col_combo, ["yıl", "yil", "year"])
        choose(self.manual_filter_col_combo, ["gösterge", "gosterge", "eğitim durumu", "indicator", "kategori"])

    def _refresh_manual_filter_values(self, rows):
        self.manual_filter_value_combo.clear()
        self.manual_filter_value_combo.addItem("")
        self.manual_year_combo.clear()
        self.manual_year_combo.addItem("")
        filter_col = self.manual_filter_col_combo.currentText() if hasattr(self, "manual_filter_col_combo") else ""
        year_col = self.manual_year_col_combo.currentText() if hasattr(self, "manual_year_col_combo") else ""
        if not self.manual_headers:
            return
        filter_idx = self.manual_headers.index(filter_col) if filter_col in self.manual_headers else None
        year_idx = self.manual_headers.index(year_col) if year_col in self.manual_headers else None
        filter_values = set()
        years = set()
        for row in rows:
            if filter_idx is not None and filter_idx < len(row) and str(row[filter_idx]).strip():
                filter_values.add(str(row[filter_idx]).strip())
            if year_idx is not None and year_idx < len(row) and str(row[year_idx]).strip():
                value = str(row[year_idx]).strip()
                if value[:4].isdigit():
                    years.add(value[:4])
        self.manual_filter_value_combo.addItems(sorted(filter_values)[:500])
        self.manual_year_combo.addItems(sorted(years, reverse=True))

    def _tuik_search(self):
        query = self.online_query_edit.text().strip()
        try:
            self.status.setText("TÜİK tablo listesi aranıyor...")
            self.online_results = self.tuik.search(query, limit=200) if query else self.tuik.all_production_flows()
            self.online_result_combo.clear()
            for flow in self.online_results:
                desc = self._short_text(self._turkish_flow_description(flow), 150)
                label = "%s | %s | v%s | %s" % (flow["id"], flow["name"], flow["version"], desc)
                self.online_result_combo.addItem(label)
            self.online_info_label.setText("%d tablo bulundu. Bir tablo seçin, sonra 'Tablo Seçeneklerini Göster' düğmesine basın." % len(self.online_results))
            self._online_selection_changed()
            if not self.online_results:
                QMessageBox.information(self, "TÜİK Online", "Sonuç bulunamadı. İngilizce terimler de deneyin: population, migration, education, age.")
        except Exception as exc:
            self._show_error(
                "TÜİK Online Hatası",
                "TÜİK tablo araması yapılamadı.",
                exc,
                ["İnternet bağlantınızı kontrol edin.", "Konu aramasında İngilizce kelimeler de deneyin: population, migration, education.", "Acil üretim gerekiyorsa Manuel Veri sekmesinden kendi Excel/CSV dosyanızı yükleyin."]
            )
        finally:
            self.status.setText("Hazır")

    def _online_selection_changed(self):
        flow = self._selected_online_flow()
        if not flow:
            self.online_description_label.setText("TÜİK tablosu seçildiğinde açıklaması burada gösterilir.")
            return
        text = "%s\n\n%s" % (flow.get("name", ""), self._turkish_flow_description(flow))
        self.online_description_label.setText(text)
        self.online_meta = None
        self.online_dimension_combo.clear()
        self.online_value_combo.clear()

    def _short_text(self, text, limit):
        text = " ".join(str(text or "").split())
        return text[:limit - 3] + "..." if len(text) > limit else text

    def _short_map_title(self, flow):
        name = flow.get("name", "") or flow.get("id", "TÜİK Veri")
        text = normalize_key(name)
        if "ilce nufus artis" in text:
            return "İlçe Nüfus Artış Hızı"
        if "population density" in text:
            return "Nüfus Yoğunluğu"
        if "growth rate" in text:
            return "Nüfus Artış Hızı"
        if "migration" in text:
            return "Göç"
        if "education" in text:
            return "Eğitim"
        if "household" in text:
            return "Hanehalkı"
        if "foreign" in text:
            return "Yabancı Nüfus"
        if "marital" in text or "civil" in text:
            return "Medeni Durum"
        return self._short_text(name, 48)

    def _scope_name(self):
        province = self.province_combo.currentText()
        if self.level_combo.currentText() == "İlçe düzeyi":
            district = self.district_combo.currentText()
            if district and district not in ("Tüm ilçeler", "Önce il seçin", "GADM listesini yükleyin"):
                return district
            if province and province != "Türkiye":
                return "%s İlçeleri" % province
        return "Türkiye" if not province else province

    def _template_category(self, item):
        title = normalize_key("%s %s %s" % (item.get("title", ""), item.get("label", ""), item.get("dataflow_id", "")))
        if any(key in title for key in ("egitim", "okul", "universite", "lise", "okuma yazma")):
            return "Eğitim"
        if any(key in title for key in ("konut", "kent kir", "kirsal", "kent nufusu", "satis")):
            return "Konut ve Kentleşme"
        if any(key in title for key in ("trafik", "tasit", "otomobil", "motosiklet", "kamyon", "minibus")):
            return "Ulaşım"
        if any(key in title for key in ("atik", "atiksu", "aritma", "su ve", "icme suyu", "desarj", "cevre", "altyapi", "belediye coplugu")):
            return "Çevre ve Altyapı"
        if any(key in title for key in ("tarim", "ormancilik", "balikcilik", "tahil", "baklagil", "tohum", "sebze", "meyve", "sigir", "koyun", "keci", "kumes", "ciftcilik", "hayvancilik")):
            return "Tarım"
        if any(key in title for key in ("sanayi", "imalat", "madencilik", "elektrik", "insaat", "gida", "tekstil", "giyim", "ayakkabi", "agac urun", "kagit", "kimya", "plastik", "metal", "makine", "motorlu tasit", "mobilya")):
            return "Sanayi"
        if any(key in title for key in ("giris", "ekonomi", "isletme")):
            return "Ekonomi"
        if any(key in title for key in ("dogum yeri", "kayit", "yabanci", "istanbul dogumlu", "ankara dogumlu")):
            return "Göç, Doğum Yeri ve Kayıt"
        if any(key in title for key in ("hane", "medeni", "evli nufus", "bosanmis nufus", "hic evlenmemis")):
            return "Hanehalkı ve Sosyal Yapı"
        if any(key in title for key in ("dogum", "evlen", "bosan", "anne", "dogurgan")):
            return "Doğum, Evlenme ve Boşanma"
        return "Nüfus ve Demografi"

    def _refresh_template_combo(self):
        if not hasattr(self, "template_combo"):
            return
        category = self.template_category_combo.currentText() if hasattr(self, "template_category_combo") else "Tümü"
        self.template_combo.clear()
        for item in self._map_templates():
            item_category = self._template_category(item)
            if category != "Tümü" and item_category != category:
                continue
            label = "%s | %s | %s" % (item["label"], item.get("level", "ölçek tabloya göre"), item.get("years", "yıl bilgisi"))
            self.template_combo.addItem(label, item)
        if self.template_combo.count() == 0:
            self.template_combo.addItem("Bu kategoride şablon yok", None)

    def _turkish_flow_description(self, flow):
        name = flow.get("name", "")
        desc = flow.get("description", "") or ""
        text = normalize_key("%s %s" % (name, desc))
        topics = []
        if "population density" in text or "nufus yogunlugu" in text:
            topics.append("nüfus yoğunluğu")
        if "growth rate" in text or "artis hizi" in text:
            topics.append("nüfus artış hızı")
        if "migration" in text or "goc" in text:
            topics.append("göç")
        if "education" in text or "egitim" in text:
            topics.append("eğitim")
        if "age" in text or "yas" in text:
            topics.append("yaş")
        if "household" in text or "hane" in text:
            topics.append("hanehalkı")
        if "foreign" in text:
            topics.append("yabancı nüfus")
        if "marital" in text or "civil" in text:
            topics.append("medeni durum")
        if "provincial and district" in text or ("province" in text and "district" in text):
            level = "il ve ilçe düzeyinde"
        elif "province" in text or "provinces" in text:
            level = "il düzeyinde"
        elif "district" in text or "districts" in text:
            level = "ilçe düzeyinde"
        elif "turkiye total" in text or "turkey total" in text:
            level = "yalnızca Türkiye toplamı"
        else:
            level = "TÜİK tablosu"
        topic = ", ".join(topics) if topics else "seçilen konu"
        warning = " Harita için il veya ilçe kırılımı olup olmadığını 'Tablo Seçeneklerini Göster' ile kontrol edin."
        return "Bu TÜİK tablosu %s %s verisi içerir.%s" % (level, topic, warning)

    def _show_filter_help(self):
        QMessageBox.information(
            self,
            "Filtre seçimi nasıl yapılır?",
            "Filtre, TÜİK tablosundaki seçeneklerden tek bir seri seçmek içindir.\n\n"
            "En iyi harita için genelde şunları seçin:\n"
            "- Gösterge/Indicator: Haritasını yapmak istediğiniz asıl konu. Örn. Population density.\n"
            "- Sex/Cinsiyet: Toplam/Total. Erkek veya kadın haritası özel amaçlıdır.\n"
            "- Age/Yaş: Toplam veya tüm yaşlar. Yaş grubu haritası istiyorsanız belirli yaş grubunu seçin.\n"
            "- Yer/Residence/İkamet: İl veya ilçe değerlerini veren alan olmalı.\n\n"
            "Seçim kutularından alanı ve değeri seçip 'Seçimi Filtreye Ekle' düğmesine basın. "
            "Eklenti filtre metnini sizin için yazar."
        )

    def _show_template_help(self):
        grouped = {}
        for item in self._map_templates():
            grouped.setdefault(self._template_category(item), []).append(item)
        template_lines = []
        for category in sorted(grouped):
            template_lines.append("[%s]" % category)
            for item in grouped[category]:
                template_lines.append("- %s: %s | %s" % (item["label"], item.get("level", "ölçek tabloya göre"), item.get("years", "yıl bilgisi TÜİK'ten kontrol edilir")))
        QMessageBox.information(
            self,
            "Beşeri coğrafya şablonları",
            "Şablonlar sık kullanılan beşeri coğrafya haritaları için başlangıç noktasıdır.\n\n"
            "Şablon kapsamları:\n%s\n\n"
            "Yaramayabilecek tablolar: yalnızca Türkiye toplamı veren, il/ilçe alanı olmayan veya çok fazla kategori içerip filtrelenmemiş tablolar. "
            "Bu durumda eklenti sizi filtre veya tablo değişikliği için yönlendirir."
            % "\n".join(template_lines)
        )

    def _apply_template(self):
        item = self.template_combo.currentData() if hasattr(self, "template_combo") else None
        if not item:
            return
        flow = {
            "id": item["dataflow_id"],
            "name": item["title"],
            "description": item["note"],
            "version": item["version"],
        }
        self.online_results = [flow]
        self.online_data = None
        self.online_meta = None
        self.online_result_combo.clear()
        self.online_result_combo.addItem("%s | %s | v%s | %s" % (flow["id"], item["title"], flow["version"], item["note"]))
        self.online_query_edit.setText(item["query"])
        self.online_filter_edit.setText(item["filters"])
        if item.get("default_year") and not self.online_start_edit.text().strip():
            self.online_start_edit.setText(item["default_year"])
        self.title_edit.setPlaceholderText(item.get("title", ""))
        self.value_unit_edit.setPlaceholderText(item.get("unit", ""))
        if item.get("level") in [self.level_combo.itemText(i) for i in range(self.level_combo.count())]:
            self.level_combo.setCurrentText(item["level"])
        if item.get("palette"):
            for i, (_, palette_key) in enumerate(getattr(self, "palette_options", [])):
                if palette_key == item["palette"]:
                    self.palette_combo.setCurrentIndex(i)
                    break
        self.online_info_label.setText(
            "Şablon uygulandı.\n"
            "Ölçek: %s\n"
            "Veri/yıl bilgisi: %s\n"
            "Sonraki adım: Kullanmak istediğiniz yılı girin. Hata alırsanız 'Tablo Seçeneklerini Göster' ile filtreleri kontrol edin."
            % (item.get("level", "tabloya göre"), item.get("years", "TÜİK tablo seçeneklerinden kontrol edin"))
        )
        self._online_selection_changed()

    def _selected_online_flow(self):
        idx = self.online_result_combo.currentIndex()
        if idx < 0 or idx >= len(self.online_results):
            return None
        return self.online_results[idx]

    def _tuik_meta(self):
        flow = self._selected_online_flow()
        if not flow:
            QMessageBox.warning(self, "TÜİK Online", "Önce TÜİK tablosu seçin.")
            return
        try:
            self.status.setText("TÜİK tablo seçenekleri okunuyor...")
            meta = self.tuik.structure_summary(flow["id"], flow.get("version") or "")
            if not meta.get("spatial_dimensions"):
                raise RuntimeError(
                    "Bu TÜİK tablosunda il/ilçe alanı görünmüyor. Harita üretmek için il veya ilçe kırılımı olan bir tablo seçin. "
                    "Öneri: nüfus yoğunluğu, nüfus artış hızı, yabancı nüfus, hanehalkı veya ilçe nüfus artış hızı şablonlarından başlayın."
                )
            self.online_meta = meta
            self._populate_online_filter_controls(meta)
            lines = []
            for dim in meta["dimensions"]:
                if dim["single_value"]:
                    continue
                values = ", ".join("%s" % v["name"] for v in dim["values"][:8])
                more = " ..." if len(dim["values"]) > 8 else ""
                lines.append("%s (%s): %s%s" % (dim["id"], dim["name"], values, more))
            if meta.get("spatial_dimensions"):
                lines.insert(0, "Harita kırılımı adayı: %s" % ", ".join(meta["spatial_dimensions"]))
            else:
                lines.insert(0, "Uyarı: Bu tabloda belirgin il/ilçe alanı görünmüyor. Harita üretmezse başka tablo seçin.")
            if meta.get("indicator_dimensions"):
                lines.insert(1 if meta.get("spatial_dimensions") else 0, "Gösterge filtresi adayı: %s" % ", ".join(meta["indicator_dimensions"]))
            if not lines:
                lines = ["Seçim gerektiren kırılım bulunmadı."]
            self.online_info_label.setText("Tablo seçenekleri yüklendi. Harita kırılımı ve gösterge adayları aşağıda listelendi; filtreyi seçim kutularıyla ekleyebilirsiniz.\n" + "\n".join(lines[:10]))
            self.online_filter_edit.setPlaceholderText("Örnek: ADNKS_GOSTERGE=Population density; SEX=Total")
        except Exception as exc:
            self._show_error(
                "TÜİK Online Hatası",
                "Tablo seçenekleri okunamadı.",
                exc,
                ["Seçilen tablonun kodu veya sürümü değişmiş olabilir; önce arama ile tabloyu yeniden bulun.", "Hazır şablonu kullandıysanız aynı konuyu arama kutusuyla tekrar arayın.", "İl/ilçe kırılımı olmayan tablolar yerine hazır şablonlardan başlayın."]
            )
        finally:
            self.status.setText("Hazır")

    def _populate_online_filter_controls(self, meta):
        self.online_dimension_combo.clear()
        for dim in meta.get("dimensions", []):
            if dim.get("single_value"):
                continue
            label = "%s - %s (%d seçenek)" % (dim["id"], dim.get("name", ""), dim.get("value_count", 0))
            self.online_dimension_combo.addItem(label, dim["id"])
        self._online_dimension_changed()

    def _online_dimension_changed(self):
        self.online_value_combo.clear()
        if not self.online_meta:
            return
        dim_id = self.online_dimension_combo.currentData()
        for dim in self.online_meta.get("dimensions", []):
            if dim.get("id") == dim_id:
                for value in dim.get("values", [])[:1000]:
                    self.online_value_combo.addItem("%s - %s" % (value.get("id", ""), value.get("name", "")), value.get("name", ""))
                break

    def _tuik_add_filter(self):
        dim_id = self.online_dimension_combo.currentData()
        value = self.online_value_combo.currentData()
        if not dim_id or not value:
            QMessageBox.warning(self, "Filtre", "Önce filtre alanı ve değer seçin.")
            return
        current = self.online_filter_edit.text().strip()
        addition = "%s=%s" % (dim_id, value)
        self.online_filter_edit.setText(addition if not current else current + "; " + addition)

    def _tuik_fetch(self):
        flow = self._selected_online_flow()
        if not flow:
            QMessageBox.warning(self, "TÜİK Online", "Önce TÜİK tablosu seçin.")
            return
        if not self.online_start_edit.text().strip():
            QMessageBox.warning(self, "Yıl zorunlu", "Online harita için tek yıl veya başlangıç yılı girin. Örn: 2020 veya 2011 - 2020.")
            return
        try:
            self.status.setText("TÜİK SDMX verisi çekiliyor...")
            title = self.title_edit.text().strip() or self._short_map_title(flow)
            filters = parse_filter_text(self.online_filter_edit.text())
            filters = self.tuik.complete_default_filters(flow["id"], flow.get("version") or "", filters)
            meta = self.tuik.structure_summary(flow["id"], flow.get("version") or "")
            multi_indicators = [d["id"] for d in meta["dimensions"] if d["id"] in meta.get("indicator_dimensions", []) and d["value_count"] > 1]
            filter_keys = {normalize_key(key) for key in filters}
            missing = [dim_id for dim_id in multi_indicators if normalize_key(dim_id) not in filter_keys]
            if missing:
                raise RuntimeError(
                    "Bu TÜİK tablosu birden fazla gösterge içeriyor. Karışık değer üretmemek için filtre verin: %s. "
                    "Seçim kutularını doldurmak için 'Tablo Seçeneklerini Göster' düğmesini kullanın." % ", ".join(missing)
                )
            data = self.tuik.fetch_records(
                flow["id"],
                flow.get("version") or "",
                self.online_start_edit.text().strip(),
                self.online_end_edit.text().strip() or self.online_start_edit.text().strip(),
                filters,
                title,
            )
            if not data.get("records"):
                raise RuntimeError("Çekilen veride il/ilçe adı ve sayısal değer birlikte bulunamadı. 'Tablo Seçeneklerini Göster' ekranından il/ilçe kırılımı olan tabloyu veya doğru filtreyi seçin.")
            self.online_data = data
            years = ", ".join(data.get("years", [])[:5])
            self.online_info_label.setText("Online veri hazır: %d ham satır, %d harita kaydı. Yıllar: %s" % (data.get("row_count", 0), len(data["records"]), years))
            QMessageBox.information(self, "TÜİK Online", "Online veri üretim kuyruğuna hazırlandı. Şimdi 'Seçili Haritaları Üret' düğmesini kullanabilirsiniz.")
        except Exception as exc:
            self._show_error(
                "TÜİK Online Hatası",
                "Veri çekilemedi veya haritaya çevrilecek il/ilçe kayıtları bulunamadı.",
                exc,
                ["'Tablo Seçeneklerini Göster' düğmesine basın.", "Harita kırılımı adayı olarak il/ilçe alanı var mı kontrol edin.", "Gösterge/Indicator alanından tek gösterge seçip filtreye ekleyin.", "Cinsiyet/yaş gibi alanlarda mümkünse Toplam/Total seçin.", "Emin değilseniz Beşeri Coğrafya Hazır Şablonları bölümünden başlayın."]
            )
        finally:
            self.status.setText("Hazır")

    def _on_level_changed(self, text):
        self.district_combo.setEnabled(text == "İlçe düzeyi")
        self._refresh_districts()

    def _refresh_districts(self):
        if not hasattr(self, "district_combo") or self.level_combo.currentText() != "İlçe düzeyi":
            return
        province = self.province_combo.currentText()
        self.district_combo.clear()
        if not province or province == "Türkiye":
            self.district_combo.addItem("Önce il seçin")
            return
        try:
            self.district_combo.addItem("Tüm ilçeler")
            self.district_combo.addItems(self.gadm.districts(province))
        except Exception:
            self.district_combo.addItem("GADM listesini yükleyin")

    def generate_maps(self):
        try:
            self._validate_before_generate()
            include_manual = bool(self.manual_path and self.manual_val_combo.currentText())
            include_online = bool(self.online_data and self.online_data.get("records"))
            if not include_manual and not include_online:
                QMessageBox.warning(self, "Veri seçimi", "Önce TÜİK Online verisini hazırlayın veya manuel Excel/CSV yükleyin.")
                return
            if include_manual and not self.manual_year_combo.currentText() and not self.manual_start_year_edit.text().strip():
                QMessageBox.warning(self, "Yıl zorunlu", "Manuel Excel/CSV haritası için tek yıl veya başlangıç yılı girin.")
                return
            project_dir = self._project_dir()
            for sub in ("01_layout_haritalar", "02_vektor_veriler", "03_qgis_proje", "04_rapor_istatistik", "05_png"):
                os.makedirs(os.path.join(project_dir, sub), exist_ok=True)
            total = 0
            if include_manual:
                total += self._year_count_for_data(self._load_manual_data())
            if include_online:
                total += self._year_count_for_data(self.online_data)
            self.progress.setMaximum(total)
            self.progress.setValue(0)
            self.generated_list.clear()
            self.generated_exports = []
            idx = 0
            if include_manual:
                data = self._load_manual_data()
                title = self.title_edit.text().strip() or data.get("title")
                idx = self._generate_year_series(data, title, project_dir, idx)
            if include_online:
                title = self.online_data.get("title") or "TÜİK Online Veri"
                idx = self._generate_year_series(self.online_data, title, project_dir, idx)
            self.status.setText("Harita üretimi tamamlandı. Dosya almak için Dışa Aktarma & Rapor sekmesini kullanın.")
        except Exception as exc:
            self._show_error(
                "Üretim Hatası",
                "Harita üretimi tamamlanamadı.",
                exc,
                ["Çalışma Alanı sekmesinde il/ilçe ve çıktı klasörünü kontrol edin.", "Veri Seçimi veya Manuel Veri sekmesinde en az bir veri kaynağını hazırlayın.", "Harita Ayarları sekmesinde sınır kalınlığı ve manuel sınıf eşiklerinin sayısal olduğundan emin olun.", "Hata veri eşleşmesiyle ilgiliyse il/ilçe adlarının TÜİK/GADM yazımıyla uyumlu olduğunu kontrol edin."]
            )
            self.status.setText("Hata: %s" % exc)

    def _validate_before_generate(self):
        try:
            border = float(self.border_width.text().strip() or "0.2")
        except Exception:
            raise RuntimeError("Sınır kalınlığı sayısal olmalı. Örnek: 0.35")
        if border < 0 or border > 5:
            raise RuntimeError("Sınır kalınlığı 0 ile 5 arasında olmalı. Akademik haritalar için 0.2-0.5 uygundur.")
        if self.class_combo.currentText() == "Manuel":
            text = self.manual_breaks.text().strip()
            if not text:
                raise RuntimeError("Sınıflandırma 'Manuel' seçiliyse manuel sınırlar yazılmalı. Örnek: 10,25,50,100")
            for part in text.split(","):
                try:
                    float(part.strip().replace(",", "."))
                except Exception:
                    raise RuntimeError("Manuel sınıf sınırları yalnızca sayılardan oluşmalı. Virgülle ayırın: 10,25,50,100")
        if self.level_combo.currentText() == "İlçe düzeyi" and self.province_combo.currentText() == "Türkiye":
            raise RuntimeError("İlçe düzeyi harita için önce belirli bir il seçin. Örnek: İstanbul veya Ankara.")
        output = self.output_edit.text().strip()
        if not output:
            raise RuntimeError("Çıktı klasörü boş bırakılamaz.")
        parent = os.path.dirname(output.rstrip("\\/")) or output
        if parent and not os.path.isdir(parent):
            raise RuntimeError("Çıktı klasörünün üst klasörü bulunamadı: %s" % parent)

    def _load_manual_data(self):
        start_year = self.manual_start_year_edit.text().strip()
        end_year = self.manual_end_year_edit.text().strip()
        year = "" if start_year else self.manual_year_combo.currentText()
        return self.loader.load_manual(
            self.manual_path,
            self.manual_loc_combo.currentText(),
            self.manual_val_combo.currentText(),
            year=year,
            year_column=self.manual_year_col_combo.currentText(),
            start_year=start_year,
            end_year=end_year,
            filter_column=self.manual_filter_col_combo.currentText(),
            filter_value=self.manual_filter_value_combo.currentText(),
        )

    def _year_count_for_data(self, data):
        years = sorted({r.get("year", "") for r in data.get("records", []) if r.get("year")}, reverse=True)
        return max(1, len(years))

    def _selected_crs(self):
        text = self.crs_combo.currentText()
        return text.split(" - ", 1)[0].strip() if " - " in text else text.strip()

    def _selected_palette(self):
        idx = self.palette_combo.currentIndex()
        if hasattr(self, "palette_options") and 0 <= idx < len(self.palette_options):
            return self.palette_options[idx][1]
        return self.palette_combo.currentText().split(" - ", 1)[0]

    def _layer_name(self, name):
        text = str(name or "TÜİK Haritası")
        replacements = {
            "Population of province/district centers and towns/villages by province and sex by province": "İl/İlçe Merkez Nüfusu",
            "Annual growth rate of population and population density of provinces by years": "Nüfus Artışı ve Yoğunluğu",
            "Annual growth rate of population by provinces and districts": "Nüfus Artış Hızı",
            "Population density": "Nüfus Yoğunluğu",
            "Population of province/district centers": "İl/İlçe Merkez Nüfusu",
            "Foreign population": "Yabancı Nüfus",
            "marital status": "Medeni Durum",
            "households": "Hanehalkı",
        }
        for long_name, short_name in replacements.items():
            if long_name.lower() in text.lower():
                text = short_name
                break
        text = self._short_text(text, 42)
        year = ""
        if hasattr(self, "_current_layer_year") and self._current_layer_year:
            year = " %s" % self._current_layer_year
        scope = self._scope_name()
        return self._short_text("%s%s - %s" % (text, year, scope), 64)

    def _map_title(self, name, year):
        manual = self.title_edit.text().strip()
        if manual:
            return manual if not year else "%s (%s)" % (manual, year)
        return "%s Haritası - %s%s" % (self._layer_name(name).split(" - ")[0].replace(" %s" % year, ""), self._scope_name(), (", %s" % year) if year else "")

    def _subtitle(self, year, unit_label):
        parts = ["Kaynak: TÜİK"]
        if year:
            parts.append("Yıl: %s" % year)
        if unit_label:
            parts.append("Birim: %s" % unit_label)
        parts.append("Projeksiyon: %s" % self._selected_crs())
        return " | ".join(parts)

    def _legend_title(self, name, unit_label):
        manual = self.legend_title_edit.text().strip()
        if manual:
            return manual
        base = self._layer_name(name).split(" - ")[0]
        if hasattr(self, "_current_layer_year") and self._current_layer_year:
            base = base.replace(" %s" % self._current_layer_year, "").strip()
            base = "%s %s" % (base, self._current_layer_year)
        return "%s - %s" % (base, self._scope_name())

    def _unit_label(self, name):
        manual = self.value_unit_edit.text().strip()
        if manual:
            return manual
        key = normalize_key(name)
        if "density" in key or "yogun" in key:
            return "kişi/km²"
        if "growth" in key or "artis" in key:
            return "‰"
        if "rate" in key or "oran" in key:
            return "%"
        return "kişi"

    def _apply_labels(self, layer, unit_label):
        if not self.labels_check.isChecked():
            return
        mode = self.label_mode_combo.currentText()
        if mode == "Sadece değer":
            expression = "format_number(\"ttm_value\", 2) || '%s'" % ((" " + unit_label) if unit_label else "")
        elif mode == "İl/ilçe adı + değer":
            expression = "\"ttm_label\" || '\\n' || format_number(\"ttm_value\", 2) || '%s'" % ((" " + unit_label) if unit_label else "")
        else:
            expression = "\"ttm_label\""
        settings = QgsPalLayerSettings()
        settings.fieldName = expression
        settings.isExpression = True
        text_format = QgsTextFormat()
        text_format.setFont(QFont("Arial", int(self.label_size.value())))
        text_format.setSize(float(self.label_size.value()))
        text_format.setColor(QColor("#222222"))
        settings.setFormat(text_format)
        layer.setLabelsEnabled(True)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.triggerRepaint()

    def _overview_layers(self, active_layer):
        try:
            if self.province_combo.currentText() == "Türkiye" and self.level_combo.currentText() == "İl düzeyi":
                return [active_layer, self._world_context_layer(active_layer)]
            overview = self.gadm.filtered_layer("İl düzeyi", None, None, self._selected_crs())
            try:
                symbol = QgsFillSymbol.createSimple({"color": "255,255,255,0", "outline_color": "150,150,150,255", "outline_width": "0.18"})
                overview.renderer().setSymbol(symbol)
            except Exception:
                pass
            overview.setCustomProperty("TurkeyThesisMap", True)
            QgsProject.instance().addMapLayer(overview, False)
            return [active_layer, overview]
        except Exception:
            return [active_layer]

    def _world_context_layer(self, active_layer):
        layer = QgsVectorLayer("Polygon?crs=%s" % active_layer.crs().authid(), "Dünya Konum Çerçevesi", "memory")
        provider = layer.dataProvider()
        extent = active_layer.extent()
        extent.scale(7.0)
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(extent)))
        provider.addFeature(feature)
        layer.updateExtents()
        symbol = QgsFillSymbol.createSimple({"color": "255,255,255,0", "outline_color": "150,150,150,255", "outline_width": "0.2"})
        layer.renderer().setSymbol(symbol)
        layer.setCustomProperty("TurkeyThesisMap", True)
        layer.setCustomProperty("TTM_WorldContext", True)
        QgsProject.instance().addMapLayer(layer, False)
        return layer

    def _generate_year_series(self, data, title, project_dir, idx):
        years = sorted({r.get("year", "") for r in data.get("records", []) if r.get("year")}, reverse=True)
        if not years:
            self._generate_one(data, title, "", project_dir)
            idx += 1
            self.progress.setValue(idx)
            return idx
        for year in years:
            subset = dict(data)
            subset["records"] = [r for r in data.get("records", []) if r.get("year") == year]
            self._generate_one(subset, title, year, project_dir)
            idx += 1
            self.progress.setValue(idx)
        return idx

    def _generate_one(self, data, name, year, project_dir):
        self._current_layer_year = year
        records = data.get("records", [])
        if not records:
            raise RuntimeError(
                "%s için haritalanabilir kayıt bulunamadı. Bu Excel dosyasında il/ilçe adı içeren satır yoksa koroplet harita üretilemez. "
                "Çözüm: TÜİK'ten il bazlı tabloyu indirin veya manuel yüklemede il/ilçe sütunu ve değer sütunu seçin." % name
            )
        self.status.setText("%s katmanı oluşturuluyor..." % name)
        district = None
        if self.level_combo.currentText() == "İlçe düzeyi" and self.district_combo.currentText() not in ("", "Tüm ilçeler", "Önce il seçin", "GADM listesini yükleyin"):
            district = self.district_combo.currentText()
        base = self.gadm.filtered_layer(
            self.level_combo.currentText(),
            None if self.province_combo.currentText() == "Türkiye" else self.province_combo.currentText(),
            district,
            self._selected_crs(),
        )
        try:
            QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(self._selected_crs()))
        except Exception:
            pass
        layer = self._memory_join_layer(base, records, name)
        QgsProject.instance().addMapLayer(layer)
        try:
            node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
            if node:
                node.setName(layer.name())
        except Exception:
            pass
        unit_label = self._unit_label(name)
        koroplet_uret(layer, "ttm_value", self.class_combo.currentText(), int(self.class_count.currentText()), self._selected_palette(),
                      self.reverse_check.isChecked(), self.manual_breaks.text(), self.border_color, float(self.border_width.text() or "0.2"),
                      unit_label=unit_label)
        self._apply_labels(layer, unit_label)
        title = self._map_title(name, year)
        layout_dir = os.path.join(project_dir, "01_layout_haritalar")
        png_dir = os.path.join(project_dir, "05_png")
        overview_layers = self._overview_layers(layer) if self.location_map_check.isChecked() else None
        layout, _outputs = LayoutBuilder().build(layer, title, layout_dir, self.page_combo.currentText(), self.orientation_combo.currentText(),
                              export_pdf=False, export_png=False, dpi=int(self.dpi_combo.currentText()),
                              show_north=self.north_check.isChecked(), show_scale=self.scale_check.isChecked(), show_legend=self.legend_check.isChecked(),
                              legend_title=self._legend_title(name, unit_label), subtitle=self._subtitle(year, unit_label),
                              overview_layers=overview_layers, show_location=self.location_map_check.isChecked(),
                              classification=self.class_combo.currentText(), unit_label=unit_label,
                              include_visible_context=self.neighbor_check.isChecked(),
                              use_manual_legend=self.manual_legend_check.isChecked())
        self.generated_exports.append({"title": title, "layout": layout, "layer": layer, "records": records})
        self.generated_list.addItem("✓ " + title)
        self._current_layer_year = ""

    def _memory_join_layer(self, base, records, name):
        geometry_name = "Polygon" if QgsWkbTypes.geometryType(base.wkbType()) == QgsWkbTypes.PolygonGeometry else QgsWkbTypes.displayString(base.wkbType())
        layer = QgsVectorLayer("%s?crs=%s" % (geometry_name, base.crs().authid()), self._layer_name(name), "memory")
        provider = layer.dataProvider()
        provider.addAttributes(list(base.fields()) + [QgsField("ttm_value", QVariant.Double), QgsField("ttm_label", QVariant.String)])
        layer.updateFields()
        values = {}
        for record in records:
            keys = {normalize_key(record.get("name")), normalize_key(record.get("raw_name")), normalize_key(turkish_title(record.get("name")))}
            for canonical, variants in IL_ESLESME.items():
                if normalize_key(record.get("name")) == normalize_key(canonical) or normalize_key(record.get("raw_name")) in [normalize_key(v) for v in variants]:
                    keys.add(normalize_key(canonical))
                    keys.update(normalize_key(v) for v in variants)
            for key in keys:
                if key:
                    values[key] = record
        field_names = base.fields().names()
        for feature in base.getFeatures():
            candidates = []
            for field in ("NAME_2", "NL_NAME_2", "VARNAME_2", "NAME_1", "NL_NAME_1", "VARNAME_1"):
                if field in field_names and feature[field]:
                    for part in str(feature[field]).replace("|", ",").split(","):
                        candidates.append(normalize_key(part))
            rec = None
            for key in candidates:
                rec = values.get(key)
                if rec:
                    break
            new = QgsFeature(layer.fields())
            new.setGeometry(feature.geometry())
            attrs = feature.attributes() + [rec["value"] if rec else None, rec["name"] if rec else ""]
            new.setAttributes(attrs)
            provider.addFeature(new)
        layer.updateExtents()
        layer.setCustomProperty("TurkeyThesisMap", True)
        return layer

    def clear_cache(self):
        self.cache.clear_runtime()
        self.gadm.remove_layers()
        manager = QgsProject.instance().layoutManager()
        for layout in list(manager.layouts()):
            if layout.name().startswith("TTM_"):
                manager.removeLayout(layout)
        self.refresh_cache_label()
        QMessageBox.information(self, "Önbellek", "Geçici çıktı önbelleği, TurkeyThesisMap katmanları ve Layout Manager'daki TTM haritaları temizlendi. GADM dosyaları korundu.")

    def refresh_cache_label(self):
        self.cache_label.setText("Önbellek: " + self.cache.human_size())

    def _project_dir(self):
        path = os.path.join(self.output_edit.text(), self._safe(self.project_edit.text() or "beseri_cografya_haritasi"))
        os.makedirs(path, exist_ok=True)
        return path

    def _zip_output(self):
        project_dir = self._project_dir()
        zip_base = project_dir.rstrip("\\/")
        shutil.make_archive(zip_base, "zip", project_dir)
        QMessageBox.information(self, "ZIP", "Teslim paketi oluşturuldu: %s.zip" % zip_base)

    def _export_outputs(self):
        if not getattr(self, "generated_exports", []):
            QMessageBox.warning(self, "Dışa aktarma", "Önce Üretim sekmesinden en az bir harita üretin.")
            return
        try:
            project_dir = self._project_dir()
            layout_dir = os.path.join(project_dir, "01_layout_haritalar")
            png_dir = os.path.join(project_dir, "05_png")
            vector_dir = os.path.join(project_dir, "02_vektor_veriler")
            report_dir = os.path.join(project_dir, "04_rapor_istatistik")
            qgz_dir = os.path.join(project_dir, "03_qgis_proje")
            for folder in (layout_dir, png_dir, vector_dir, report_dir, qgz_dir):
                os.makedirs(folder, exist_ok=True)
            for item in self.generated_exports:
                title = item["title"]
                layout = item["layout"]
                layer = item["layer"]
                records = item["records"]
                exporter = QgsLayoutExporter(layout)
                safe = self._safe(title)
                if self.pdf_check.isChecked():
                    exporter.exportToPdf(os.path.join(layout_dir, safe + ".pdf"), QgsLayoutExporter.PdfExportSettings())
                if self.png_check.isChecked():
                    settings = QgsLayoutExporter.ImageExportSettings()
                    settings.dpi = int(self.dpi_combo.currentText())
                    exporter.exportToImage(os.path.join(png_dir, safe + ".png"), settings)
                if self.svg_check.isChecked():
                    try:
                        exporter.exportToSvg(os.path.join(layout_dir, safe + ".svg"), QgsLayoutExporter.SvgExportSettings())
                    except Exception:
                        pass
                if self.gpkg_check.isChecked():
                    try:
                        options = QgsVectorFileWriter.SaveVectorOptions()
                        options.driverName = "GPKG"
                        options.fileEncoding = "utf-8"
                        QgsVectorFileWriter.writeAsVectorFormatV3(layer, os.path.join(vector_dir, safe + ".gpkg"), QgsCoordinateTransformContext(), options)
                    except Exception:
                        QgsVectorFileWriter.writeAsVectorFormat(layer, os.path.join(vector_dir, safe + ".gpkg"), "utf-8", layer.crs(), "GPKG")
                if self.csv_check.isChecked() or self.html_check.isChecked() or self.txt_check.isChecked():
                    self.reports.write_all(records, title, report_dir)
            if self.qgz_check.isChecked():
                QgsProject.instance().write(os.path.join(qgz_dir, self.project_edit.text() + ".qgz"))
            if self.zip_check.isChecked():
                self._zip_output()
            QMessageBox.information(self, "Dışa aktarma", "Seçili çıktılar hazırlandı: %s" % project_dir)
        except Exception as exc:
            self._show_error(
                "Dışa Aktarma Hatası",
                "Seçili dosyalar dışa aktarılamadı.",
                exc,
                ["Çıktı klasörünün yazılabilir olduğundan emin olun.", "QGIS içinde açık dosyanın başka programda kilitli olmadığını kontrol edin.", "SVG hata verirse PDF/PNG ile tekrar dışa aktarın."]
            )

    def _safe(self, text):
        keep = []
        for ch in str(text):
            keep.append(ch.lower() if ch.isalnum() else "_")
        return "_".join(filter(None, "".join(keep).split("_")))[:100]
