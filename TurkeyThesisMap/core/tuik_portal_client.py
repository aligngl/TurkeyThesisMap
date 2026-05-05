import json
import urllib.request


class TuikPortalClient:
    """Lightweight placeholder for TÜİK Veri Portalı file/catalog workflows.

    TurkeyThesisMap currently uses SDMX online data as the reliable automated
    path. This class keeps the tuikr-style portal/catalog boundary explicit so
    file-download support can be expanded without changing the dialog contract.
    """

    BASE = "https://veriportali.tuik.gov.tr"

    def get_json(self, path_or_url, timeout=60):
        url = path_or_url if path_or_url.startswith("http") else self.BASE + path_or_url
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "TurkeyThesisMap/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
