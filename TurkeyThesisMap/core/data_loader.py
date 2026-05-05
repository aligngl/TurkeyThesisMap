import os

from .excel_parser import ExcelParser


class DataLoader:
    CATEGORY_LABELS = {
        "nufus": "Nüfus & Yerleşme",
        "goc": "Göç",
        "egitim": "Eğitim",
        "saglik": "Sağlık",
        "yasam": "Yaşam Kalitesi",
    }

    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        self.builtin_dir = os.path.join(plugin_dir, "data", "builtin")
        self.parser = ExcelParser()

    def datasets(self):
        items = []
        for category in ("nufus", "goc", "egitim", "saglik", "yasam"):
            folder = os.path.join(self.builtin_dir, category)
            if not os.path.isdir(folder):
                continue
            for name in sorted(os.listdir(folder), key=str.lower):
                if os.path.splitext(name)[1].lower() not in (".xlsx", ".csv"):
                    continue
                path = os.path.join(folder, name)
                years = self._years_for(path)
                mappable_years = self._mappable_years_for(path)
                items.append({
                    "id": "%s/%s" % (category, name),
                    "category": category,
                    "category_label": self.CATEGORY_LABELS.get(category, category),
                    "name": os.path.splitext(name)[0],
                    "path": path,
                    "years": years,
                    "mappable_years": mappable_years,
                    "mappable": bool(mappable_years),
                })
        return items

    def load(self, dataset, year=None):
        return self.parser.parse_records(dataset["path"], year=year)

    def load_manual_preview(self, path):
        rows = self.parser.read_table(path)
        header_index = self.parser._find_header_row(rows) if rows else 0
        headers = self.parser._make_headers(rows, header_index) if rows else []
        return headers, rows[header_index + 1:header_index + 11]

    def load_manual(self, path, location_column, value_column, year=None, year_column=None,
                    start_year=None, end_year=None, filter_column=None, filter_value=None):
        return self.parser.parse_records(
            path,
            location_column=location_column,
            value_column=value_column,
            year=year,
            year_column=year_column,
            start_year=start_year,
            end_year=end_year,
            filter_column=filter_column,
            filter_value=filter_value,
        )

    def _years_for(self, path):
        try:
            rows = self.parser.read_table(path)
            header_index = self.parser._find_header_row(rows) if rows else 0
            headers = self.parser._make_headers(rows, header_index) if rows else []
            year_idx = self.parser._find_column(headers, None, {"yil", "yıl", "year"})
            years = set()
            for row in rows[header_index + 1:]:
                if year_idx is not None and year_idx < len(row):
                    value = str(row[year_idx]).strip()
                    if value and value[:4].isdigit():
                        years.add(value[:4])
            return sorted(years, reverse=True)
        except Exception:
            return []

    def _mappable_years_for(self, path):
        try:
            rows = self.parser.read_table(path)
            header_index = self.parser._find_header_row(rows) if rows else 0
            headers = self.parser._make_headers(rows, header_index) if rows else []
            data_rows = rows[header_index + 1:]
            loc_idx = self.parser._find_column(headers, None, self.parser.LOCATION_HINTS)
            loc_idx = self.parser._repair_location_column(headers, data_rows, loc_idx)
            year_idx = self.parser._find_column(headers, None, {"yil", "yıl", "year"})
            if loc_idx is None:
                return []
            years = set()
            for row in data_rows:
                if loc_idx >= len(row):
                    continue
                loc = row[loc_idx]
                if self.parser.is_mappable_location(loc):
                    if year_idx is not None and year_idx < len(row):
                        year = str(row[year_idx]).strip()
                        if year[:4].isdigit():
                            years.add(year[:4])
                    else:
                        years.add("")
            return sorted(years, reverse=True)
        except Exception:
            return []
