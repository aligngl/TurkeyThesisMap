import hashlib
import json
import os
import socket
import time
import urllib.parse
import urllib.error
import urllib.request

from .excel_parser import TR_IL_LISTESI, normalize_key, parse_number, turkish_title


BASE_URL = "https://nsiws.tuik.gov.tr/rest"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "TurkeyThesisMap/1.0",
}

class TuikSdmxClient:
    """Small dependency-free client inspired by tuik-mcp and tuikr workflows."""

    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir
        if cache_dir and not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)
        self.dataflow_cache = os.path.join(cache_dir, "tuik_sdmx_dataflows.json") if cache_dir else ""
        self.response_cache_dir = os.path.join(cache_dir, "responses") if cache_dir else ""
        if self.response_cache_dir and not os.path.isdir(self.response_cache_dir):
            os.makedirs(self.response_cache_dir)

    def dataflows(self, include_test=False, max_age_hours=24):
        raw = self._load_cached_dataflows(max_age_hours)
        if raw is None:
            raw = self._get_json(BASE_URL + "/dataflow/", timeout=60, cache_max_age_hours=max_age_hours).get("references", {})
            self._save_cached_dataflows(raw)
        flows = []
        for ref in raw.values():
            if not include_test and self._is_non_production(ref):
                continue
            flows.append({
                "id": ref.get("id", ""),
                "name": ref.get("name", ""),
                "description": ref.get("description", ""),
                "version": ref.get("version", ""),
            })
        return flows

    def search(self, query, include_test=False, limit=50):
        terms = [normalize_key(x) for x in str(query or "").split() if x.strip()]
        if not terms:
            return []
        scored = []
        for flow in self.dataflows(include_test=include_test):
            text = normalize_key("%s %s %s" % (flow["id"], flow["name"], flow["description"]))
            score = sum(1 for term in terms if term in text)
            if score:
                scored.append((score, flow))
        scored.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [flow for _, flow in scored[:limit]]

    def all_production_flows(self):
        return self.dataflows(include_test=False)

    def structure(self, dataflow_id, version=""):
        version = version or self.resolve_version(dataflow_id)
        url = "%s/data/TR,%s,%s/" % (BASE_URL, urllib.parse.quote(dataflow_id), urllib.parse.quote(version))
        raw = self._get_json(url, params={"detail": "nodata"}, timeout=45, cache_max_age_hours=24 * 14)
        return {
            "dataflow_id": dataflow_id,
            "version": version,
            "dimensions": self._parse_dimensions(raw),
        }

    def structure_summary(self, dataflow_id, version=""):
        meta = self.structure(dataflow_id, version)
        spatial = []
        indicators = []
        for dim in meta["dimensions"]:
            dim_key = normalize_key("%s %s" % (dim["id"], dim["name"]))
            if any(token in dim_key for token in ("ikamet", "province", "ilce", "residence", "ref area", "yerlesim")):
                spatial.append(dim["id"])
            if any(token in dim_key for token in ("gosterge", "indicator", "statistical")):
                indicators.append(dim["id"])
        meta["spatial_dimensions"] = spatial
        meta["indicator_dimensions"] = indicators
        return meta

    def fetch_rows(self, dataflow_id, version="", start_period="", end_period="", filters=None):
        version = version or self.resolve_version(dataflow_id)
        url = "%s/data/TR,%s,%s/" % (BASE_URL, urllib.parse.quote(dataflow_id), urllib.parse.quote(version))
        params = {}
        if start_period:
            params["startPeriod"] = start_period
        if end_period:
            params["endPeriod"] = end_period
        raw = self._get_json(url, params=params, timeout=75, cache_max_age_hours=24 * 7, retries=2)
        rows = self._parse_sdmx_data(raw)
        return self._filter_rows(rows, filters or {})

    def fetch_records(self, dataflow_id, version="", start_period="", end_period="", filters=None, title=""):
        rows = self.fetch_rows(dataflow_id, version, start_period, end_period, filters)
        records = self.rows_to_records(rows, title or dataflow_id)
        years = sorted({r["year"] for r in records if r.get("year")}, reverse=True)
        return {
            "title": title or dataflow_id,
            "headers": list(rows[0].keys()) if rows else [],
            "years": years,
            "records": records,
            "source": "TÜİK SDMX",
            "row_count": len(rows),
        }

    def complete_default_filters(self, dataflow_id, version="", filters=None):
        """Add safe Total filters for common category dimensions left empty by templates."""
        completed = dict(filters or {})
        filtered_keys = {normalize_key(key) for key in completed}
        meta = self.structure_summary(dataflow_id, version)
        spatial = {normalize_key(key) for key in meta.get("spatial_dimensions", [])}
        for dim in meta.get("dimensions", []):
            dim_id = dim.get("id", "")
            dim_key = normalize_key(dim_id)
            if dim.get("value_count", 0) <= 1 or dim_key in filtered_keys or dim_key in spatial:
                continue
            if self._is_location_dimension(dim):
                continue
            if dim_key in ("time period", "time_period", "ref_area", "freq", "indicator", "yas", "yas grubu", "yas_grubu", "yas grup", "age", "age group"):
                continue
            values = dim.get("values", [])
            total = self._default_total_value(values)
            if total:
                completed[dim_id] = [total]
                filtered_keys.add(dim_key)
        return completed

    def _is_location_dimension(self, dim):
        dim_key = normalize_key("%s %s" % (dim.get("id", ""), dim.get("name", "")))
        return any(token in dim_key for token in (
            "ikamet", "residence", "ref area", "province", "provinces",
            "ilce", "il ", "iller", "yerlesim", "dogum yeri il",
            "place of birth province", "nufus kayit il",
        ))

    def _default_total_value(self, values):
        preferred = ("total", "toplam")
        fallback = ("not applicable", "not applicable", "uygulanamaz")
        for wanted in preferred:
            for value in values:
                if normalize_key(value.get("name")) == wanted or normalize_key(value.get("id")) == wanted:
                    return value.get("name") or value.get("id")
        for wanted in fallback:
            for value in values:
                if normalize_key(value.get("name")) == wanted or normalize_key(value.get("id")) in ("z", "_z"):
                    return value.get("name") or value.get("id")
        return ""

    def rows_to_records(self, rows, title):
        aggregated = {}
        order = []
        for row in rows:
            loc = self._location_value(row)
            val = self._value(row)
            if not loc or val is None:
                continue
            year = str(row.get("obsTime") or row.get("TIME_PERIOD") or row.get("ZAMAN") or row.get("YIL") or "")
            key = (turkish_title(loc), year)
            if key not in aggregated:
                aggregated[key] = {
                    "name": turkish_title(loc),
                    "raw_name": loc,
                    "year": year,
                    "value": 0.0,
                    "value_text": str(val),
                    "title": title,
                }
                order.append(key)
            aggregated[key]["value"] += float(val)
        return [aggregated[key] for key in order]

    def resolve_version(self, dataflow_id):
        versions = [flow["version"] for flow in self.dataflows(include_test=True) if flow["id"] == dataflow_id]
        return sorted(versions)[-1] if versions else "1.0"

    def _get_json(self, url, params=None, timeout=120, cache_max_age_hours=24, retries=1):
        if params:
            query = urllib.parse.urlencode(params)
            url = url + ("&" if "?" in url else "?") + query
        cache_path = self._response_cache_path(url)
        cached = self._read_response_cache(cache_path, cache_max_age_hours)
        if cached is not None:
            return cached
        last_error = None
        for attempt in range(max(1, retries + 1)):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    data = response.read()
                parsed = json.loads(data.decode("utf-8"))
                self._write_response_cache(cache_path, parsed)
                return parsed
            except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                stale = self._read_response_cache(cache_path, None)
                if stale is not None:
                    return stale
            except Exception:
                stale = self._read_response_cache(cache_path, None)
                if stale is not None:
                    return stale
                raise
        raise TimeoutError("TÜİK servisi zamanında yanıt vermedi. Lütfen aynı şablonu tekrar deneyin; başarılı cevaplar otomatik önbelleğe alınır. Teknik ayrıntı: %s" % last_error)

    def _response_cache_path(self, url):
        if not self.response_cache_dir:
            return ""
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return os.path.join(self.response_cache_dir, digest + ".json")

    def _read_response_cache(self, path, max_age_hours):
        if not path or not os.path.exists(path):
            return None
        if max_age_hours is not None:
            age = time.time() - os.path.getmtime(path)
            if age > max_age_hours * 3600:
                return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    def _write_response_cache(self, path, payload):
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
        except Exception:
            pass

    def _load_cached_dataflows(self, max_age_hours):
        if not self.dataflow_cache or not os.path.exists(self.dataflow_cache):
            return None
        age = time.time() - os.path.getmtime(self.dataflow_cache)
        if age > max_age_hours * 3600:
            return None
        try:
            with open(self.dataflow_cache, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    def _save_cached_dataflows(self, raw):
        if not self.dataflow_cache:
            return
        with open(self.dataflow_cache, "w", encoding="utf-8") as handle:
            json.dump(raw, handle, ensure_ascii=False)

    def _is_non_production(self, flow):
        for ann in flow.get("annotations", []):
            if ann.get("type") == "NonProductionDataflow" and str(ann.get("text")).lower() == "true":
                return True
        return False

    def _parse_dimensions(self, raw):
        dims = []
        for dim_type in ("series", "observation"):
            for dim in raw.get("structure", {}).get("dimensions", {}).get(dim_type, []):
                values = [{"id": v.get("id", ""), "name": v.get("name", v.get("id", ""))} for v in dim.get("values", [])]
                dims.append({
                    "id": dim.get("id", ""),
                    "name": dim.get("name", ""),
                    "position": dim.get("keyPosition", dim.get("position", 0)),
                    "type": dim_type,
                    "values": values,
                    "value_count": len(values),
                    "single_value": len(values) <= 1,
                })
        dims.sort(key=lambda item: item["position"])
        return dims

    def _parse_sdmx_data(self, raw):
        struct = raw.get("structure", {})
        data_sets = raw.get("dataSets", [])
        if not data_sets:
            return []
        dim_info = {}
        for dim_type in ("series", "observation"):
            for dim in struct.get("dimensions", {}).get(dim_type, []):
                dim_id = dim.get("id", "")
                pos = dim.get("keyPosition", dim.get("position", 0))
                values = {i: v.get("name", v.get("id", "")) for i, v in enumerate(dim.get("values", []))}
                dim_info[dim_id] = {"position": pos, "values": values, "type": dim_type}
        rows = []
        for series_key, series_val in data_sets[0].get("series", {}).items():
            key_parts = series_key.split(":")
            series_dims = {}
            for dim_id, info in dim_info.items():
                if info["type"] == "series" and info["position"] < len(key_parts):
                    idx = int(key_parts[info["position"]])
                    series_dims[dim_id] = info["values"].get(idx, "?%d" % idx)
            for obs_key, obs_val in series_val.get("observations", {}).items():
                obs_dims = {}
                obs_parts = obs_key.split(":")
                for dim_id, info in dim_info.items():
                    if info["type"] == "observation":
                        pos = info["position"]
                        idx = int(obs_parts[pos]) if pos < len(obs_parts) else int(obs_parts[0])
                        obs_dims[dim_id] = info["values"].get(idx, "?%d" % idx)
                value = obs_val[0] if obs_val else None
                rows.append(dict(series_dims, **obs_dims, DEGER=value))
        return rows

    def _filter_rows(self, rows, filters):
        if not filters:
            return rows
        row_keys = {normalize_key(key): key for row in rows[:50] for key in row.keys()}
        missing = [key for key in filters if normalize_key(key) not in row_keys]
        if missing:
            raise ValueError("Filtre boyutu veride bulunamadı: %s. 'Tablo Seçeneklerini Göster' bölümündeki boyut kodlarını kullanın." % ", ".join(missing))
        filtered = []
        for row in rows:
            ok = True
            for key, allowed in filters.items():
                real_key = row_keys.get(normalize_key(key), key)
                if real_key not in row:
                    continue
                row_value = normalize_key(row.get(real_key))
                allowed_keys = [normalize_key(x) for x in allowed]
                if row_value not in allowed_keys:
                    ok = False
                    break
            if ok:
                filtered.append(row)
        return filtered

    def _location_value(self, row):
        for row_key, value in row.items():
            if normalize_key(row_key) in ("ikamet yeri", "residence", "place of residence"):
                value_key = normalize_key(value)
                if value_key in ("total", "toplam"):
                    return ""
                if self._looks_spatial(value):
                    return value
        preferred = [
            "IKAMET_YERI", "RESIDENCE", "PLACE_OF_RESIDENCE",
            "DOGUM_YERI_IL", "PLACE_OF_BIRTH", "PROVINCE",
            "REF_AREA", "ILCE", "IL", "ILI", "BOLGE", "YERLESIM",
        ]
        for key in preferred:
            for row_key, value in row.items():
                row_key_norm = normalize_key(row_key)
                key_norm = normalize_key(key)
                if self._dimension_matches_location_key(row_key_norm, key_norm) and self._looks_spatial(value):
                    return value
        for value in row.values():
            if self._looks_like_known_province(value):
                return value
        return ""

    def _dimension_matches_location_key(self, row_key_norm, key_norm):
        if key_norm in ("il", "ili"):
            return row_key_norm == key_norm
        return row_key_norm == key_norm or key_norm in row_key_norm

    def _looks_spatial(self, value):
        key = normalize_key(value)
        if key in ("", "turkiye", "turkey", "toplam", "total", "not applicable"):
            return False
        if self._looks_like_known_province(value):
            return True
        return any(ch.isalpha() for ch in str(value)) and not key[:4].isdigit()

    def _looks_like_known_province(self, value):
        key = normalize_key(value)
        return key in {normalize_key(name) for name in TR_IL_LISTESI}

    def _value(self, row):
        for key in ("DEGER", "obsValue", "OBS_VALUE", "value"):
            if key in row:
                return parse_number(row[key])
        for value in reversed(list(row.values())):
            parsed = parse_number(value)
            if parsed is not None:
                return parsed
        return None


def parse_filter_text(text):
    filters = {}
    parts = []
    for raw_part in str(text or "").split(";"):
        part = raw_part.strip()
        if not part:
            continue
        if "=" in part:
            parts.append(part)
        elif parts:
            parts[-1] = parts[-1] + "; " + part
    for part in parts:
        key, raw_values = part.split("=", 1)
        values = [v.strip() for v in raw_values.split("|") if v.strip()]
        if key.strip() and values:
            filters[key.strip()] = values
    return filters
