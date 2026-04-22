from pydantic import BaseModel

class SystemMetrics(BaseModel):
    cpu_temp: int
    cpu_usage: int
    ram_usage: int
    ram_total: int
    disk_usage: int
    disk_total: int
