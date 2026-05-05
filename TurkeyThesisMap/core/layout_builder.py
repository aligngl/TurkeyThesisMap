import math
import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsFillSymbol,
    QgsLegendStyle,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsPrintLayout,
    QgsProject,
    QgsRectangle,
    QgsUnitTypes,
)


class LayoutBuilder:
    """Tez çıktısına uygun, kontrollü QGIS layout üreticisi."""

    def __init__(self, project=None):
        self.project = project or QgsProject.instance()

    def build(
        self,
        layer,
        title,
        output_dir,
        page_size="A4",
        orientation="Yatay",
        footer="",
        export_pdf=True,
        export_png=False,
        dpi=300,
        show_north=True,
        show_scale=True,
        show_legend=True,
        legend_title="Lejant",
        subtitle="",
        overview_layers=None,
        show_location=False,
        classification="",
        unit_label="",
        include_visible_context=True,
        use_manual_legend=False,
    ):
        manager = self.project.layoutManager()
        layout = QgsPrintLayout(self.project)
        layout.initializeDefaults()
        layout.setName(self._unique_name("TTM_" + self._safe(title)))

        width, height = self._page_dimensions(page_size, orientation)
        page = layout.pageCollection().page(0)
        page.setPageSize(QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters))

        self._add_title_block(layout, title, width)
        map_rect, side_rect = self._content_rects(width, height, orientation, show_legend)
        legend_rect, location_rect = self._split_side_panel(
            side_rect, orientation, show_legend, bool(show_location and overview_layers)
        )

        map_item = self._add_main_map(layout, layer, map_rect, include_visible_context)

        if show_scale:
            self._add_scale_bar(layout, map_item, map_rect, layer)
        if show_north:
            self._add_north_arrow(layout, map_rect)
        if show_location and overview_layers:
            self._add_location_map(layout, location_rect or self._map_corner_location_rect(map_rect), overview_layers)
        if show_legend and use_manual_legend:
            self._add_manual_legend(layout, layer, legend_rect, legend_title, unit_label, classification)
        elif show_legend:
            self._add_qgis_legend(layout, map_item, layer, legend_rect, legend_title, unit_label, classification, subtitle)

        manager.addLayout(layout)
        layout.refresh()

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        exporter = QgsLayoutExporter(layout)
        outputs = {}
        base = self._safe(title)
        if export_pdf:
            pdf = os.path.join(output_dir, base + ".pdf")
            exporter.exportToPdf(pdf, QgsLayoutExporter.PdfExportSettings())
            outputs["pdf"] = pdf
        if export_png:
            png = os.path.join(output_dir, base + ".png")
            settings = QgsLayoutExporter.ImageExportSettings()
            settings.dpi = int(dpi)
            exporter.exportToImage(png, settings)
            outputs["png"] = png
        return layout, outputs

    def _page_dimensions(self, page_size, orientation):
        sizes = {
            "A4": (210, 297),
            "A3": (297, 420),
            "A2": (420, 594),
        }
        width, height = sizes.get(str(page_size).upper(), sizes["A4"])
        if orientation == "Yatay":
            width, height = height, width
        return float(width), float(height)

    def _content_rects(self, width, height, orientation, show_legend):
        margin = 12.0
        top = 23.0
        bottom = 13.0
        gap = 7.0

        if not show_legend:
            return (margin, top, width - margin * 2, height - top - bottom), None

        if orientation == "Dikey":
            legend_h = min(72.0, max(58.0, height * 0.24))
            map_h = height - top - bottom - legend_h - gap
            return (
                (margin, top, width - margin * 2, map_h),
                (margin, top + map_h + gap, width - margin * 2, legend_h),
            )

        legend_w = min(88.0, max(80.0, width * 0.28))
        map_w = width - margin * 2 - legend_w - gap
        return (
            (margin, top, map_w, height - top - bottom),
            (margin + map_w + gap, top, legend_w, height - top - bottom),
        )

    def _add_title_block(self, layout, title, page_width):
        title_item = self._label(layout, title, 12, 6.5, page_width - 24, 11, 16, True)
        title_item.setHAlign(Qt.AlignLeft)
        self._shape(layout, 12, 19.0, page_width - 24, 0.45, "#2f3f4f", "#2f3f4f", 0, 255)

    def _add_main_map(self, layout, layer, rect, include_visible_context):
        x, y, w, h = rect
        layer.updateExtents()
        layer.triggerRepaint()

        map_item = QgsLayoutItemMap(layout)
        layout.addLayoutItem(map_item)
        map_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
        map_item.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
        map_item.setLayers(self._map_layers(layer, include_visible_context))
        map_item.setKeepLayerSet(True)
        if hasattr(map_item, "setCrs"):
            try:
                map_item.setCrs(layer.crs())
            except Exception:
                pass
        try:
            map_item.setBackgroundEnabled(True)
            map_item.setBackgroundColor(QColor("#ffffff"))
        except Exception:
            pass
        self._style_item_frame(map_item, "#000000", 0.28)

        extent = self._safe_extent(layer)
        extent = self._fit_extent_to_rect(extent, w, h)
        map_item.setExtent(extent)
        map_item.zoomToExtent(extent)
        map_item.refresh()
        return map_item

    def _add_manual_legend(self, layout, layer, rect, title, unit_label, classification):
        if rect is None:
            return
        x, y, w, h = rect
        self._shape(layout, x, y, w, h, "#ffffff", "#000000", 0.28, 0)

        title_text = "Açıklamalar"
        self._label(layout, title_text, x + 5, y + 5, w - 10, 6.5, 8.5, True, "#1f1f1f")

        meta = []
        if unit_label:
            meta.append("Birim: %s" % unit_label)
        if classification:
            meta.append("Sınıflandırma: %s" % self._short_classification(classification))
        meta_text = " | ".join(meta)
        if meta_text:
            self._label(layout, meta_text, x + 5, y + 13, w - 10, 5.0, 5.8, False, "#555555")

        ranges = self._legend_ranges(layer)
        null_count = self._null_count(layer)
        if null_count:
            ranges.append(("#d9d9d9", "Veri yok"))
        if not ranges:
            self._label(layout, "Lejant üretilemedi", x + 5, y + 28, w - 10, 8, 8, False, "#555555")
            return

        start_y = y + (23 if meta_text else 18)
        bottom_margin = 5.0
        columns = 2 if w >= 120 and len(ranges) > 5 else 1
        col_w = (w - 10.0) / columns
        row_h = max(6.3, min(8.2, (h - (start_y - y) - bottom_margin) / math.ceil(float(len(ranges)) / columns)))
        rows_per_col = int(math.ceil(float(len(ranges)) / columns))

        for idx, (color, label) in enumerate(ranges):
            col = idx // rows_per_col
            row = idx % rows_per_col
            item_x = x + 5 + col * col_w
            item_y = start_y + row * row_h
            if item_y + row_h > y + h - bottom_margin:
                break
            self._shape(layout, item_x, item_y + 1.2, 5.8, 3.8, color, "#777777", 0.08)
            clean_label = self._clean_legend_label(label)
            self._label(layout, clean_label, item_x + 8, item_y - 0.2, col_w - 10, row_h + 0.8, 7.3, False, "#222222")

    def _add_qgis_legend(self, layout, map_item, layer, rect, title, unit_label, classification, subtitle):
        if rect is None:
            return
        x, y, w, h = rect

        self._shape(layout, x, y, w, h, "#ffffff", "#000000", 0.28, 0)
        title_text = "Açıklamalar"
        title_item = self._label(layout, title_text, x + 5, y + 5, w - 10, 6.5, 8.5, True, "#1f1f1f")
        title_item.setHAlign(Qt.AlignLeft)
        notes = self._legend_notes(unit_label, classification, subtitle)
        note_y = y + 13.0
        for note in notes[:3]:
            self._label(layout, note, x + 5, note_y, w - 10, 4.2, 5.8, False, "#4b5563")
            note_y += 4.5

        legend = QgsLayoutItemLegend(layout)
        layout.addLayoutItem(legend)
        legend.setTitle("")
        legend.setLinkedMap(map_item)
        legend.setAutoUpdateModel(False)
        try:
            root = legend.model().rootGroup()
            root.removeAllChildren()
            root.addLayer(layer)
            node = root.findLayer(layer.id())
            if node:
                node.setName(layer.name())
        except Exception:
            pass
        try:
            from qgis.core import QgsLayerTreeModel
            legend.model().setFlag(QgsLayerTreeModel.ShowLegendAsTree, False)
        except Exception:
            pass
        if hasattr(legend, "setWrapString"):
            legend.setWrapString("|")
        if hasattr(legend, "setResizeToContents"):
            legend.setResizeToContents(False)
        if hasattr(legend, "setColumnCount"):
            legend.setColumnCount(1)
        if hasattr(legend, "setSymbolWidth"):
            legend.setSymbolWidth(9.5)
        if hasattr(legend, "setSymbolHeight"):
            legend.setSymbolHeight(4.2)
        if hasattr(legend, "setBoxSpace"):
            legend.setBoxSpace(1.0)
        if hasattr(legend, "setLineSpacing"):
            legend.setLineSpacing(0.9)
        if hasattr(legend, "setBackgroundEnabled"):
            legend.setBackgroundEnabled(False)
        if hasattr(legend, "setFrameEnabled"):
            legend.setFrameEnabled(False)
        try:
            legend.setStyleFont(QgsLegendStyle.Title, QFont("Arial", 1))
            legend.setStyleFont(QgsLegendStyle.Group, QFont("Arial", 6, QFont.Bold))
            legend.setStyleFont(QgsLegendStyle.Subgroup, QFont("Arial", 6))
            legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Arial", 6))
            legend.setStyleMargin(QgsLegendStyle.Title, QgsLegendStyle.Bottom, 0)
            legend.setStyleMargin(QgsLegendStyle.Group, QgsLegendStyle.Bottom, 2.0)
            legend.setStyleMargin(QgsLegendStyle.Subgroup, QgsLegendStyle.Bottom, 1.0)
            legend.setStyleMargin(QgsLegendStyle.Symbol, QgsLegendStyle.Top, 1.1)
            legend.setStyleMargin(QgsLegendStyle.SymbolLabel, QgsLegendStyle.Left, 3.2)
        except Exception:
            pass
        legend_y = max(note_y + 2.0, y + 27.0)
        legend.attemptMove(QgsLayoutPoint(x + 5, legend_y, QgsUnitTypes.LayoutMillimeters))
        legend.attemptResize(QgsLayoutSize(w - 10, max(20.0, y + h - legend_y - 5), QgsUnitTypes.LayoutMillimeters))
        if hasattr(legend, "refresh"):
            legend.refresh()

    def _add_scale_bar(self, layout, map_item, rect, layer):
        x, y, w, h = rect
        panel_w = min(54.0, max(42.0, w * 0.25))
        panel_h = 11.0
        panel_x = x + 6
        panel_y = y + h - panel_h - 6

        scale = QgsLayoutItemScaleBar(layout)
        layout.addLayoutItem(scale)
        self._style_item_box(scale, "#ffffff", "#c7c7c7", 235)
        scale.setLinkedMap(map_item)
        scale.setStyle("Line Ticks Up")
        scale.setUnits(QgsUnitTypes.DistanceKilometers)
        scale.setUnitLabel("km")
        try:
            scale.setNumberOfSegments(2)
            scale.setNumberOfSegmentsLeft(0)
            scale.setUnitsPerSegment(self._nice_scale_segment(layer))
            scale.setHeight(2.0)
            scale.setFont(QFont("Arial", 5))
            scale.setFontColor(QColor("#222222"))
            if hasattr(scale, "setMapUnitsPerScaleBarUnit") and layer.crs().authid().upper() != "EPSG:4326":
                scale.setMapUnitsPerScaleBarUnit(1000.0)
        except Exception:
            pass
        scale.applyDefaultSize()
        scale.attemptMove(QgsLayoutPoint(panel_x, panel_y, QgsUnitTypes.LayoutMillimeters))
        scale.attemptResize(QgsLayoutSize(panel_w, panel_h, QgsUnitTypes.LayoutMillimeters))

    def _add_north_arrow(self, layout, rect):
        x, y, w, _h = rect
        box_w = 14.0
        box_h = 19.0
        box_x = x + w - box_w - 6
        box_y = y + 6
        arrow = QgsLayoutItemPicture(layout)
        layout.addLayoutItem(arrow)
        self._style_item_box(arrow, "#ffffff", "#c7c7c7", 235)
        arrow_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "north_arrow.svg"))
        if os.path.exists(arrow_path):
            arrow.setPicturePath(arrow_path)
        arrow.attemptMove(QgsLayoutPoint(box_x, box_y, QgsUnitTypes.LayoutMillimeters))
        arrow.attemptResize(QgsLayoutSize(box_w, box_h, QgsUnitTypes.LayoutMillimeters))

    def _add_location_map(self, layout, rect, overview_layers):
        x, y, w, h = rect
        self._shape(layout, x, y, w, h, "#ffffff", "#000000", 0.24, 0)
        self._label(layout, "Konum Haritası", x + 2.5, y + 2.2, w - 5, 4.5, 6, True, "#333333")

        inset = QgsLayoutItemMap(layout)
        layout.addLayoutItem(inset)
        inset.attemptMove(QgsLayoutPoint(x + 2.0, y + 7.2, QgsUnitTypes.LayoutMillimeters))
        inset.attemptResize(QgsLayoutSize(w - 4.0, h - 9.2, QgsUnitTypes.LayoutMillimeters))
        active_layer = overview_layers[0]
        inset_layers = self._location_layers(overview_layers)
        inset.setLayers(inset_layers)
        inset.setKeepLayerSet(True)
        if hasattr(inset, "setCrs"):
            try:
                inset.setCrs(active_layer.crs())
            except Exception:
                pass
        try:
            inset.setBackgroundEnabled(True)
            inset.setBackgroundColor(QColor("#ffffff"))
        except Exception:
            pass
        extent = self._location_extent(overview_layers)
        extent = self._fit_extent_to_rect(extent, w - 4.0, h - 9.2)
        inset.setExtent(extent)
        inset.zoomToExtent(extent)
        self._style_item_frame(inset, "#000000", 0.18)
        inset.refresh()

    def _add_side_panel(self, layout, rect):
        return

    def _split_side_panel(self, side_rect, orientation, show_legend, show_location):
        if not side_rect:
            return None, None
        x, y, w, h = side_rect
        pad = 0.0
        gap = 6.0
        if not show_location:
            return (x, y, w, h), None
        if orientation == "Dikey":
            loc_w = min(62.0, max(48.0, w * 0.34))
            legend_w = w - loc_w - gap
            return (
                (x, y, legend_w, h),
                (x + w - loc_w, y, loc_w, h),
            )
        loc_h = min(50.0, max(42.0, h * 0.30))
        legend_h = h - loc_h - gap
        return (
            (x, y, w, legend_h),
            (x, y + h - loc_h, w, loc_h),
        )

    def _map_corner_location_rect(self, map_rect):
        x, y, w, h = map_rect
        size = min(42.0, max(30.0, min(w * 0.22, h * 0.28)))
        return (x + w - size - 6, y + h - size - 6, size, size)

    def _label(self, layout, text, x, y, w, h, size, bold=False, color="#111111"):
        item = QgsLayoutItemLabel(layout)
        layout.addLayoutItem(item)
        item.setText(str(text or ""))
        font = QFont("Arial", int(size), QFont.Bold if bold else QFont.Normal)
        item.setFont(font)
        try:
            item.setFontColor(QColor(color))
        except Exception:
            pass
        try:
            item.setMargin(0)
        except Exception:
            pass
        item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
        item.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
        return item

    def _shape(self, layout, x, y, w, h, fill, outline, outline_width=0.2, alpha=255):
        shape = QgsLayoutItemShape(layout)
        layout.addLayoutItem(shape)
        shape.setShapeType(QgsLayoutItemShape.Rectangle)
        fill_color = QColor(fill)
        fill_color.setAlpha(int(alpha))
        fill_rgba = "%d,%d,%d,%d" % (fill_color.red(), fill_color.green(), fill_color.blue(), fill_color.alpha())
        symbol = QgsFillSymbol.createSimple({
            "color": fill_rgba,
            "outline_color": outline,
            "outline_width": str(outline_width),
        })
        shape.setSymbol(symbol)
        shape.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
        shape.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
        return shape

    def _style_item_box(self, item, fill, outline, alpha=255):
        fill_color = QColor(fill)
        fill_color.setAlpha(int(alpha))
        try:
            item.setBackgroundEnabled(True)
            item.setBackgroundColor(fill_color)
        except Exception:
            pass
        try:
            item.setFrameEnabled(True)
        except Exception:
            pass
        for method, value in (
            ("setFrameStrokeColor", QColor(outline)),
            ("setFrameStrokeWidth", 0.10),
        ):
            try:
                getattr(item, method)(value)
            except Exception:
                pass

    def _style_item_frame(self, item, outline, width=0.24):
        try:
            item.setFrameEnabled(True)
        except Exception:
            pass
        for method, value in (
            ("setFrameStrokeColor", QColor(outline)),
            ("setFrameStrokeWidth", float(width)),
        ):
            try:
                getattr(item, method)(value)
            except Exception:
                pass

    def _safe_extent(self, layer):
        layer.updateExtents()
        extent = QgsRectangle(layer.extent())
        if self._extent_ok(extent):
            extent.scale(1.08)
            return extent

        calculated = None
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if not geom or geom.isEmpty():
                continue
            bbox = geom.boundingBox()
            if calculated is None:
                calculated = QgsRectangle(bbox)
            else:
                calculated.combineExtentWith(bbox)
        if calculated and self._extent_ok(calculated):
            calculated.scale(1.08)
            return calculated
        return QgsRectangle(25, 35, 46, 43)

    def _map_layers(self, active_layer, include_visible_context):
        if not include_visible_context:
            return [active_layer]
        layers = [active_layer]
        for context_layer in self._visible_context_layers(active_layer):
            if context_layer.id() != active_layer.id():
                layers.append(context_layer)
        return layers

    def _location_layers(self, overview_layers):
        layers = list(overview_layers)
        active_layer = layers[0] if layers else None
        if active_layer:
            for context_layer in self._visible_context_layers(active_layer):
                if context_layer.id() not in {layer.id() for layer in layers}:
                    layers.append(context_layer)
        return layers

    def _location_extent(self, overview_layers):
        if len(overview_layers) > 1 and not overview_layers[1].customProperty("TTM_WorldContext"):
            extent = self._safe_extent(overview_layers[1])
            extent.scale(1.08)
            return extent
        extent = self._safe_extent(overview_layers[0])
        extent.scale(3.2)
        return extent

    def _visible_context_layers(self, active_layer):
        root = self.project.layerTreeRoot()
        context_layers = []
        try:
            nodes = root.findLayers()
        except Exception:
            nodes = []
        for node in nodes:
            layer = node.layer()
            if not layer:
                continue
            if layer.id() == active_layer.id():
                continue
            if self._is_ttm_layer(layer):
                continue
            try:
                visible = node.isVisible() if hasattr(node, "isVisible") else node.itemVisibilityChecked()
            except Exception:
                visible = True
            if visible:
                context_layers.append(layer)
        return context_layers

    def _is_ttm_layer(self, layer):
        try:
            if layer.customProperty("TurkeyThesisMap"):
                return True
        except Exception:
            pass
        name = str(layer.name() or "")
        return name.startswith("TurkeyThesisMap") or name.startswith("TTM_")

    def _fit_extent_to_rect(self, extent, rect_w, rect_h):
        if not self._extent_ok(extent):
            return extent
        target_aspect = float(rect_w) / max(float(rect_h), 0.001)
        extent_aspect = float(extent.width()) / max(float(extent.height()), 0.001)
        cx = extent.center().x()
        cy = extent.center().y()
        half_w = extent.width() / 2.0
        half_h = extent.height() / 2.0
        if extent_aspect > target_aspect:
            half_h = half_w / target_aspect
        else:
            half_w = half_h * target_aspect
        fitted = QgsRectangle(cx - half_w, cy - half_h, cx + half_w, cy + half_h)
        fitted.scale(1.03)
        return fitted

    def _extent_ok(self, extent):
        try:
            return extent and extent.width() > 0 and extent.height() > 0
        except Exception:
            return False

    def _legend_ranges(self, layer):
        renderer = layer.renderer()
        if not renderer or not hasattr(renderer, "ranges"):
            return []
        entries = []
        for item in renderer.ranges():
            symbol = item.symbol()
            color = "#999999"
            if symbol:
                try:
                    color = symbol.color().name()
                except Exception:
                    pass
            label = item.label() or ""
            entries.append((color, label))
        return entries

    def _null_count(self, layer):
        fields = layer.fields().names()
        if "ttm_value" not in fields:
            return 0
        count = 0
        for feature in layer.getFeatures():
            value = feature["ttm_value"]
            if value is None:
                count += 1
        return count

    def _layout_item_width(self, item, fallback):
        for attr in ("rectWithFrame", "rect"):
            try:
                rect = getattr(item, attr)()
                width = float(rect.width())
                if width > 0:
                    return width
            except Exception:
                pass
        return float(fallback)

    def _layout_item_height(self, item, fallback):
        for attr in ("rectWithFrame", "rect"):
            try:
                rect = getattr(item, attr)()
                height = float(rect.height())
                if height > 0:
                    return height
            except Exception:
                pass
        return float(fallback)

    def _nice_scale_segment(self, layer):
        extent = self._safe_extent(layer)
        width_units = max(float(extent.width()), 1.0)
        authid = layer.crs().authid().upper() if layer.crs() else ""
        if authid == "EPSG:4326":
            width_km = width_units * 85.0
        else:
            width_km = width_units / 1000.0
        raw = max(width_km / 5.0, 0.1)
        exponent = math.floor(math.log10(raw))
        fraction = raw / (10 ** exponent)
        if fraction <= 1:
            nice = 1
        elif fraction <= 2:
            nice = 2
        elif fraction <= 5:
            nice = 5
        else:
            nice = 10
        return nice * (10 ** exponent)

    def _clean_legend_label(self, label):
        text = str(label or "").replace(" - ", " – ")
        text = text.replace(",0000", "").replace(",000", "")
        return self._wrap_text(text, 34)

    def _legend_notes(self, unit_label, classification, subtitle):
        notes = []
        if unit_label:
            notes.append("Birim: %s" % unit_label)
        if classification:
            notes.append("Sınıflandırma: %s" % self._short_classification(classification))
        source_year = []
        for part in str(subtitle or "").split("|"):
            clean = part.strip()
            if clean.startswith("Kaynak:") or clean.startswith("Yıl:"):
                source_year.append(clean)
        if source_year:
            notes.append(" | ".join(source_year))
        return notes

    def _single_line_text(self, text, max_chars):
        clean = " ".join(str(text or "").split())
        if len(clean) <= max_chars:
            return clean
        return clean[:max(0, max_chars - 1)].rstrip() + "…"

    def _short_classification(self, text):
        text = str(text or "")
        if "Jenks" in text:
            return "Doğal aralar"
        if "Kantil" in text:
            return "Kantil"
        if "Eşit" in text:
            return "Eşit aralık"
        if "Standart" in text:
            return "Std. sapma"
        if "Manuel" in text:
            return "Manuel"
        return text

    def _wrap_text(self, text, width):
        words = str(text or "").split()
        lines = []
        current = ""
        for word in words:
            proposed = (current + " " + word).strip()
            if len(proposed) <= width:
                current = proposed
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return "\n".join(lines)

    def _unique_name(self, name):
        existing = {layout.name() for layout in self.project.layoutManager().layouts()}
        candidate = name
        i = 2
        while candidate in existing:
            candidate = "%s_%d" % (name, i)
            i += 1
        return candidate

    def _safe(self, text):
        keep = []
        for ch in str(text):
            keep.append(ch.lower() if ch.isalnum() else "_")
        return "_".join(filter(None, "".join(keep).split("_")))[:120]
