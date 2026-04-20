import psutil
import os
from services.system.schemas import SystemMetrics

class SystemService:
    @staticmethod
    def get_cpu_temperature() -> int:
        try:
            temps = psutil.sensors_temperatures()
            if "cpu_thermal" in temps:
                return int(temps["cpu_thermal"][0].current)
            if "vcgencmd" in temps:
                 return int(temps["vcgencmd"][0].current)
        except Exception:
            pass
        
        try:
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp_raw = int(f.read())
                    return int(temp_raw / 1000)
        except Exception:
            pass
            
        return 0

    def get_metrics(self) -> SystemMetrics:
        cpu_usage = int(psutil.cpu_percent(interval=0.5))
        cpu_temp = self.get_cpu_temperature()

        ram = psutil.virtual_memory()
        ram_usage = int(ram.percent)
        ram_total = int(ram.total / (1024**3))

        disk = psutil.disk_usage('/')
        disk_usage = int(disk.percent)
        disk_total = int(disk.total / (1024**3))

        return SystemMetrics(
            cpu_temp=cpu_temp,
            cpu_usage=cpu_usage,
            ram_usage=ram_usage,
            ram_total=ram_total,
            disk_usage=disk_usage,
            disk_total=disk_total
        )

system_service = SystemService()
