import os
import shutil


class CacheManager:
    def __init__(self, plugin_dir):
        self.cache_dir = os.path.join(plugin_dir, "data", "cache")
        self.gadm_dir = os.path.join(self.cache_dir, "gadm")
        self.generated_dir = os.path.join(self.cache_dir, "generated")
        self.temp_dir = os.path.join(self.cache_dir, "temp")
        for path in (self.gadm_dir, self.generated_dir, self.temp_dir):
            if not os.path.isdir(path):
                os.makedirs(path)

    def clear_runtime(self):
        for path in (self.generated_dir, self.temp_dir):
            if os.path.isdir(path):
                shutil.rmtree(path)
            os.makedirs(path)

    def size_info(self):
        count = 0
        total = 0
        for root, _, files in os.walk(self.cache_dir):
            for name in files:
                count += 1
                total += os.path.getsize(os.path.join(root, name))
        return count, total

    def human_size(self):
        count, total = self.size_info()
        size = float(total)
        unit = "B"
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                break
            size /= 1024.0
        return "%d dosya, %.2f %s" % (count, size, unit)
