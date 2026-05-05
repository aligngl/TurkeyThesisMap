import csv
import os

from .classifier import format_tr, stats


class ReportGenerator:
    def write_all(self, records, title, output_dir):
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        csv_path = os.path.join(output_dir, "istatistik_tablosu.csv")
        html_path = os.path.join(output_dir, "rapor.html")
        txt_path = os.path.join(output_dir, "yorum.txt")
        ordered = sorted(records, key=lambda r: r["value"], reverse=True)
        summary = stats([r["value"] for r in ordered])
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["İl/İlçe Adı", "Değer", "Sıralama", "Ortalama Farkı"])
            for idx, record in enumerate(ordered, 1):
                writer.writerow([record["name"], format_tr(record["value"]), idx, format_tr(record["value"] - summary.get("mean", 0))])
        rows = "\n".join("<tr><td>%s</td><td>%s</td><td>%d</td></tr>" % (r["name"], format_tr(r["value"]), i) for i, r in enumerate(ordered, 1))
        html = """<!doctype html><html lang="tr"><meta charset="utf-8"><title>{0}</title>
<style>body{{font-family:Arial,sans-serif;line-height:1.45}}table{{border-collapse:collapse}}td,th{{border:1px solid #999;padding:6px 10px}}</style>
<h1>{0}</h1><p>Minimum {1}, maksimum {2}, ortalama {3}, medyan {4}.</p>
<table><thead><tr><th>İl/İlçe</th><th>Değer</th><th>Sıra</th></tr></thead><tbody>{5}</tbody></table></html>""".format(
            title, format_tr(summary.get("min")), format_tr(summary.get("max")), format_tr(summary.get("mean")), format_tr(summary.get("median")), rows)
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(html)
        top = ordered[0] if ordered else {"name": "", "value": 0}
        low = ordered[-1] if ordered else {"name": "", "value": 0}
        text = ("%s verilerine göre en yüksek değere sahip birim %s (%s), en düşük değere sahip birim %s (%s) olarak belirlenmiştir. "
                "Ortalama değer %s olup dağılım tez haritası ve istatistik tablosunda karşılaştırmalı olarak sunulmuştur." %
                (title, top["name"], format_tr(top["value"]), low["name"], format_tr(low["value"]), format_tr(summary.get("mean"))))
        with open(txt_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return {"csv": csv_path, "html": html_path, "txt": txt_path}
