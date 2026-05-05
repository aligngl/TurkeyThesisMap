import csv
import os
import re
import zipfile
import xml.etree.ElementTree as ET


IL_LISTESI = [
    "Adana", "Adiyaman", "Afyonkarahisar", "Agri", "Amasya", "Ankara", "Antalya", "Artvin",
    "Aydin", "Balikesir", "Bilecik", "Bingol", "Bitlis", "Bolu", "Burdur", "Bursa",
    "Canakkale", "Cankiri", "Corum", "Denizli", "Diyarbakir", "Edirne", "Elazig", "Erzincan",
    "Erzurum", "Eskisehir", "Gaziantep", "Giresun", "Gumushane", "Hakkari", "Hatay", "Isparta",
    "Mersin", "Istanbul", "Izmir", "Kars", "Kastamonu", "Kayseri", "Kirklareli", "Kirsehir",
    "Kocaeli", "Konya", "Kutahya", "Malatya", "Manisa", "Kahramanmaras", "Mardin", "Mugla",
    "Mus", "Nevsehir", "Nigde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop",
    "Sivas", "Tekirdag", "Tokat", "Trabzon", "Tunceli", "Sanliurfa", "Usak", "Van", "Yozgat",
    "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kirikkale", "Batman", "Sirnak", "Bartin",
    "Ardahan", "Igdir", "Yalova", "Karabuk", "Kilis", "Osmaniye", "Duzce",
]

TR_IL_LISTESI = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin",
    "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
    "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan",
    "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta",
    "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
    "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla",
    "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop",
    "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat",
    "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın",
    "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce",
]

IL_ESLESME = {
    "Afyonkarahisar": ["Afyon", "AFYONKARAHİSAR", "AFYONKARAHISAR"],
    "Kahramanmaraş": ["K.Maraş", "Kahraman Maraş", "KAHRAMANMARAŞ", "KAHRAMANMARAS"],
    "Şanlıurfa": ["Urfa", "ŞANLIURFA", "SANLIURFA"],
    "İstanbul": ["ISTANBUL", "İSTANBUL"],
    "İzmir": ["IZMIR", "İZMİR"],
    "Çanakkale": ["CANAKKALE", "ÇANAKKALE"],
    "Gümüşhane": ["GUMUSHANE", "GÜMÜŞHANE"],
    "Iğdır": ["IGDIR", "IĞDIR"],
    "Mersin": ["İçel", "ICEL", "İÇEL"],
}

_TR_LOWER = str.maketrans("IİŞĞÜÖÇÂÎÛ", "ıişğüöçâîû")
_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜı", "cgiosuCGIOSUi")


def turkish_title(value):
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*\([^)]*\)\s*", " ", text).strip()
    words = []
    for word in text.translate(_TR_LOWER).split(" "):
        words.append(word[:1].upper().replace("I", "İ") + word[1:])
    titled = " ".join(words)
    for canonical, variants in IL_ESLESME.items():
        keys = [canonical] + variants
        if normalize_key(titled) in [normalize_key(x) for x in keys]:
            return canonical
    for name in TR_IL_LISTESI:
        if normalize_key(titled) == normalize_key(name):
            return name
    return titled


def normalize_key(value):
    text = str(value or "").strip()
    text = re.sub(r"\s*\([^)]*\)\s*", " ", text)
    text = re.sub(r"[^0-9A-Za-zÇĞİÖŞÜçğıöşü]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().translate(_ASCII).lower()


def parse_number(value):
    if value is None:
        return None
    text = str(value).strip()
    if text in ("", "-", "...", "NaN", "nan"):
        return None
    text = text.replace("\xa0", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def is_mappable_location(value):
    key = normalize_key(value)
    if key in ("", "turkiye", "turkey", "toplam", "total", "not applicable"):
        return False
    if key[:4].isdigit():
        return False
    return any(ch.isalpha() for ch in str(value))


class ExcelParser:
    HEADER_HINTS = {"yil", "yıl", "duzey", "düzey", "il", "iller", "province", "deger", "değer", "toplam"}
    LOCATION_HINTS = {"duzey", "düzey", "il", "iller", "il adi", "il adı", "province", "name", "yerlesim", "yerleşim"}

    def read_table(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            return self._read_csv(path)
        if ext == ".xlsx":
            return self._read_xlsx(path)
        raise ValueError("Yalnızca .xlsx ve .csv dosyaları desteklenir.")

    def parse_records(self, path, location_column=None, value_column=None, year=None,
                      year_column=None, start_year=None, end_year=None,
                      filter_column=None, filter_value=None):
        rows = self.read_table(path)
        if not rows:
            return {"title": os.path.splitext(os.path.basename(path))[0], "headers": [], "years": [], "records": []}
        title = self._guess_title(rows, path)
        header_index = self._find_header_row(rows)
        headers = self._make_headers(rows, header_index)
        data_rows = rows[header_index + 1:]
        loc_idx = self._find_column(headers, location_column, self.LOCATION_HINTS)
        loc_idx = self._repair_location_column(headers, data_rows, loc_idx)
        year_idx = self._find_column(headers, year_column, {"yil", "yıl", "year"})
        val_idx = self._find_value_column(headers, value_column, loc_idx, year_idx)
        filter_idx = self._find_column(headers, filter_column, {filter_column}) if filter_column else None
        allowed_filters = [normalize_key(v) for v in str(filter_value or "").split("|") if v.strip()]
        aggregated = {}
        order = []
        years = set()
        for raw in data_rows:
            row = list(raw) + [""] * max(0, len(headers) - len(raw))
            row_year = str(row[year_idx]).strip() if year_idx is not None and year_idx < len(row) else ""
            if row_year:
                years.add(row_year)
            if year and row_year and str(year) != row_year:
                continue
            if start_year and row_year and row_year[:4].isdigit() and int(row_year[:4]) < int(start_year):
                continue
            if end_year and row_year and row_year[:4].isdigit() and int(row_year[:4]) > int(end_year):
                continue
            if filter_idx is not None and allowed_filters:
                row_filter = row[filter_idx] if filter_idx < len(row) else ""
                if normalize_key(row_filter) not in allowed_filters:
                    continue
            loc = row[loc_idx] if loc_idx is not None and loc_idx < len(row) else ""
            if not is_mappable_location(loc):
                continue
            val = row[val_idx] if val_idx is not None and val_idx < len(row) else ""
            num = parse_number(val)
            if num is None:
                continue
            name = turkish_title(loc)
            key = (name, row_year)
            if key not in aggregated:
                aggregated[key] = {
                    "name": name,
                    "raw_name": loc,
                    "year": row_year,
                    "value": 0.0,
                    "value_text": str(val),
                    "title": title,
                }
                order.append(key)
            aggregated[key]["value"] += num
        records = [aggregated[key] for key in order]
        return {
            "title": title,
            "headers": headers,
            "years": sorted(years, reverse=True),
            "records": records,
            "location_column": headers[loc_idx] if loc_idx is not None else "",
            "value_column": headers[val_idx] if val_idx is not None else "",
        }

    def is_mappable_location(self, value):
        return is_mappable_location(value)

    def _read_csv(self, path):
        for enc in ("utf-8-sig", "cp1254", "iso-8859-9"):
            try:
                with open(path, newline="", encoding=enc) as handle:
                    sample = handle.read(4096)
                    handle.seek(0)
                    dialect = csv.Sniffer().sniff(sample, delimiters=";, \t")
                    return [list(row) for row in csv.reader(handle, dialect)]
            except Exception:
                continue
        raise ValueError("CSV encoding veya ayraç yapısı okunamadı.")

    def _read_xlsx(self, path):
        ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        with zipfile.ZipFile(path) as zf:
            shared = []
            if "xl/sharedStrings.xml" in zf.namelist():
                root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in root.findall("a:si", ns):
                    shared.append("".join(t.text or "" for t in si.findall(".//a:t", ns)))
            sheet_name = self._first_sheet_path(zf)
            root = ET.fromstring(zf.read(sheet_name))
            rows = []
            for row in root.findall(".//a:sheetData/a:row", ns):
                values = []
                last_col = 0
                for cell in row.findall("a:c", ns):
                    col = self._column_index(cell.get("r", "A1"))
                    while last_col < col:
                        values.append("")
                        last_col += 1
                    value = self._cell_value(cell, shared, ns)
                    values.append(value)
                    last_col += 1
                while values and values[-1] == "":
                    values.pop()
                rows.append(values)
            return rows

    def _first_sheet_path(self, zf):
        candidates = sorted(name for name in zf.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        if not candidates:
            raise ValueError("XLSX içinde çalışma sayfası bulunamadı.")
        return candidates[0]

    def _cell_value(self, cell, shared, ns):
        value = cell.find("a:v", ns)
        if value is None:
            inline = cell.find("a:is", ns)
            return "" if inline is None else "".join(t.text or "" for t in inline.findall(".//a:t", ns))
        text = value.text or ""
        if cell.get("t") == "s" and text.isdigit():
            idx = int(text)
            return shared[idx] if idx < len(shared) else ""
        return text

    def _column_index(self, ref):
        letters = re.sub(r"[^A-Z]", "", ref.upper())
        total = 0
        for ch in letters:
            total = total * 26 + ord(ch) - 64
        return max(0, total - 1)

    def _guess_title(self, rows, path):
        for row in rows[:3]:
            non_empty = [x for x in row if str(x).strip()]
            if len(non_empty) == 1 and normalize_key(non_empty[0]) not in self.HEADER_HINTS:
                return str(non_empty[0]).strip()
        return os.path.splitext(os.path.basename(path))[0]

    def _find_header_row(self, rows):
        best_idx, best_score = 0, -1
        for idx, row in enumerate(rows[:12]):
            keys = {normalize_key(x) for x in row if str(x).strip()}
            score = len(keys & {normalize_key(x) for x in self.HEADER_HINTS})
            if score > best_score:
                best_idx, best_score = idx, score
        return best_idx

    def _make_headers(self, rows, header_index):
        row = rows[header_index]
        next_row = rows[header_index + 1] if header_index + 1 < len(rows) else []
        width = max(len(row), len(next_row))
        headers = []
        for i in range(width):
            first = row[i] if i < len(row) else ""
            second = next_row[i] if i < len(next_row) else ""
            if str(first).strip():
                headers.append(str(first).strip())
            elif str(second).strip() and parse_number(second) is None:
                headers.append(str(second).strip())
            else:
                headers.append("Sutun_%d" % (i + 1))
        return headers

    def _find_column(self, headers, requested, hints):
        if requested and requested in headers:
            return headers.index(requested)
        hint_keys = {normalize_key(x) for x in hints}
        for i, header in enumerate(headers):
            hkey = normalize_key(header)
            if hkey in hint_keys or any(hint in hkey for hint in hint_keys if len(hint) > 2):
                return i
        return None

    def _find_value_column(self, headers, requested, loc_idx, year_idx):
        if requested and requested in headers:
            return headers.index(requested)
        skip = {idx for idx in (loc_idx, year_idx) if idx is not None}
        preferred = ["aldigi goc", "aldığı göç", "net goc", "net göç", "toplam", "deger", "değer", "oran", "hiz", "hız", "sayi", "sayı", "nufus", "nüfus"]
        for key in preferred:
            for i, header in enumerate(headers):
                if i not in skip and key in normalize_key(header):
                    return i
        for i, _ in enumerate(headers):
            if i not in skip:
                return i
        return None

    def _repair_location_column(self, headers, data_rows, loc_idx):
        if loc_idx is None:
            return None
        sample = []
        for row in data_rows[:100]:
            if loc_idx < len(row) and str(row[loc_idx]).strip():
                sample.append(normalize_key(row[loc_idx]))
        if sample and len(set(sample)) == 1 and sample[0] in ("turkiye", "turkey"):
            for i, header in enumerate(headers):
                hkey = normalize_key(header)
                tokens = hkey.split()
                if i != loc_idx and ("il" in tokens or "ili" in tokens or "iller" in tokens) and "nufus" not in tokens:
                    return i
        return loc_idx
