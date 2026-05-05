import os
import urllib.request
import zipfile

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
)


GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_TUR_shp.zip"


class GadmManager:
    def __init__(self, plugin_dir):
        self.cache_dir = os.path.join(plugin_dir, "data", "cache", "gadm")
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.zip_path = os.path.join(self.cache_dir, "gadm41_TUR_shp.zip")

    def ensure(self, progress_callback=None):
        shp = os.path.join(self.cache_dir, "gadm41_TUR_1.shp")
        if os.path.exists(shp):
            return self.cache_dir
        if not os.path.exists(self.zip_path):
            if progress_callback:
                progress_callback("GADM indiriliyor...")
            urllib.request.urlretrieve(GADM_URL, self.zip_path)
        if progress_callback:
            progress_callback("GADM arşivi açılıyor...")
        with zipfile.ZipFile(self.zip_path) as zf:
            zf.extractall(self.cache_dir)
        return self.cache_dir

    def province_layer(self, name="TurkeyThesisMap İl Sınırları"):
        self.ensure()
        path = os.path.join(self.cache_dir, "gadm41_TUR_1.shp")
        layer = QgsVectorLayer(path, name, "ogr")
        if not layer.isValid():
            raise RuntimeError("GADM il katmanı açılamadı.")
        return layer

    def district_layer(self, name="TurkeyThesisMap İlçe Sınırları"):
        self.ensure()
        path = os.path.join(self.cache_dir, "gadm41_TUR_2.shp")
        layer = QgsVectorLayer(path, name, "ogr")
        if not layer.isValid():
            raise RuntimeError("GADM ilçe katmanı açılamadı.")
        return layer

    def filtered_layer(self, level, province=None, district=None, crs_authid="EPSG:4326"):
        base = self.district_layer() if level == "İlçe düzeyi" else self.province_layer()
        exprs = []
        if province:
            exprs.append("\"NAME_1\" = '%s'" % province.replace("'", "''"))
        if district and level == "İlçe düzeyi":
            exprs.append("\"NAME_2\" = '%s'" % district.replace("'", "''"))
        subset = " AND ".join(exprs)
        if subset:
            base.setSubsetString(subset)
        if crs_authid and base.crs().authid() != crs_authid:
            return self._reproject_memory_layer(base, crs_authid)
        return base

    def _reproject_memory_layer(self, source, crs_authid):
        target_crs = QgsCoordinateReferenceSystem(crs_authid)
        geom_name = "Polygon" if QgsWkbTypes.geometryType(source.wkbType()) == QgsWkbTypes.PolygonGeometry else QgsWkbTypes.displayString(source.wkbType())
        layer = QgsVectorLayer("%s?crs=%s" % (geom_name, target_crs.authid()), source.name(), "memory")
        provider = layer.dataProvider()
        provider.addAttributes(source.fields())
        layer.updateFields()
        transform = QgsCoordinateTransform(source.crs(), target_crs, QgsProject.instance())
        for feature in source.getFeatures():
            new_feature = QgsFeature(layer.fields())
            geom = feature.geometry()
            if geom and not geom.isEmpty():
                geom.transform(transform)
                new_feature.setGeometry(geom)
            new_feature.setAttributes(feature.attributes())
            provider.addFeature(new_feature)
        layer.updateExtents()
        return layer

    def provinces(self):
        layer = self.province_layer()
        return sorted({f["NAME_1"] for f in layer.getFeatures() if f["NAME_1"]})

    def districts(self, province):
        layer = self.district_layer()
        layer.setSubsetString("\"NAME_1\" = '%s'" % province.replace("'", "''"))
        return sorted({f["NAME_2"] for f in layer.getFeatures() if f["NAME_2"]})

    def remove_layers(self):
        project = QgsProject.instance()
        for layer_id, layer in list(project.mapLayers().items()):
            if layer.name().startswith("TurkeyThesisMap") or layer.customProperty("TurkeyThesisMap"):
                project.removeMapLayer(layer_id)
