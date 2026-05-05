from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsClassificationEqualInterval,
    QgsClassificationJenks,
    QgsClassificationQuantile,
    QgsClassificationStandardDeviation,
    QgsColorRampShader,
    QgsFillSymbol,
    QgsGraduatedSymbolRenderer,
    QgsRendererRange,
    QgsSymbol,
)

from .classifier import format_tr, manual_breaks


PALETLER = {
    "Blues": ["#d8ebf7", "#a9d0e8", "#6baed6", "#2171b5", "#084594"],
    "Reds": ["#f6d6cb", "#f5aa91", "#fb6a4a", "#cb181d", "#67000d"],
    "Greens": ["#d7efd0", "#addd9d", "#74c476", "#238b45", "#00441b"],
    "Oranges": ["#f5d5b4", "#fdae6b", "#fd8d3c", "#d94801", "#7f2704"],
    "Purples": ["#ded9ee", "#bcbddc", "#9e9ac8", "#6a51a3", "#3f007d"],
    "Greys": ["#e0e0e0", "#bdbdbd", "#969696", "#636363", "#252525"],
    "YlOrRd": ["#f4e17a", "#fed976", "#fd8d3c", "#e31a1c", "#800026"],
    "YlGnBu": ["#d8ef8a", "#a1dab4", "#41b6c4", "#225ea8", "#081d58"],
    "BuPu": ["#d6e6f2", "#bfd3e6", "#8c96c6", "#88419d", "#4d004b"],
    "OrRd": ["#f4cf9d", "#fdbb84", "#fc8d59", "#d7301f", "#7f0000"],
    "RdBu": ["#9e0142", "#f46d43", "#e6e6e6", "#74add1", "#313695"],
    "RdYlGn": ["#a50026", "#f46d43", "#e6d96a", "#66bd63", "#006837"],
    "BrBG": ["#543005", "#bf812d", "#d9d9c3", "#80cdc1", "#003c30"],
    "PiYG": ["#8e0152", "#de77ae", "#e6e6e6", "#7fbc41", "#276419"],
    "PRGn": ["#762a83", "#af8dc3", "#e6e6e6", "#7fbf7b", "#1b7837"],
}


def _method(name):
    key = str(name or "").lower()
    if "kantil" in key or "quantile" in key:
        return QgsClassificationQuantile()
    if "eşit" in key or "equal" in key:
        return QgsClassificationEqualInterval()
    if "standart" in key or "std" in key:
        return QgsClassificationStandardDeviation()
    return QgsClassificationJenks()


def koroplet_uret(layer, deger_alan, siniflandirma="Jenks", sinif_sayisi=5, renk_paleti="Blues",
                  ters_cevir=False, manuel_sinirlar="", border_color="#ffffff", border_width=0.2,
                  unit_label=""):
    colors = list(PALETLER.get(renk_paleti, PALETLER["Blues"]))
    if ters_cevir:
        colors.reverse()
    symbol = QgsFillSymbol.createSimple({"outline_color": border_color, "outline_width": str(border_width)})
    renderer = QgsGraduatedSymbolRenderer(deger_alan)
    renderer.setSourceSymbol(symbol)
    if str(siniflandirma).lower().startswith("manuel"):
        values = sorted([f[deger_alan] for f in layer.getFeatures() if f[deger_alan] is not None])
        if values:
            bounds = [values[0]] + manual_breaks(manuel_sinirlar) + [values[-1]]
            ranges = []
            for i in range(len(bounds) - 1):
                sym = QgsSymbol.defaultSymbol(layer.geometryType())
                sym.setColor(QColor(colors[min(i, len(colors) - 1)]))
                sym.symbolLayer(0).setStrokeColor(QColor(border_color))
                sym.symbolLayer(0).setStrokeWidth(float(border_width))
                label = "%s - %s" % (format_tr(bounds[i]), format_tr(bounds[i + 1]))
                ranges.append(QgsRendererRange(bounds[i], bounds[i + 1], sym, label))
            renderer = QgsGraduatedSymbolRenderer(deger_alan, ranges)
    else:
        renderer.setClassificationMethod(_method(siniflandirma))
        renderer.updateClasses(layer, int(sinif_sayisi))
        renderer.updateColorRamp(_ramp(colors))
    for item in renderer.ranges():
        item.setLabel("%s - %s" % (format_tr(item.lowerValue()), format_tr(item.upperValue())))
    layer.setRenderer(renderer)
    layer.triggerRepaint()
    return renderer


def _ramp(colors):
    shader = QgsColorRampShader()
    items = []
    step = 1.0 / max(1, len(colors) - 1)
    for i, color in enumerate(colors):
        items.append(QgsColorRampShader.ColorRampItem(i * step, QColor(color)))
    shader.setColorRampItemList(items)
    try:
        from qgis.core import QgsGradientColorRamp
        return QgsGradientColorRamp(QColor(colors[0]), QColor(colors[-1]))
    except Exception:
        return None
