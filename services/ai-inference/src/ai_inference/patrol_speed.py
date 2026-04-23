import obd
import time
import random

class PatrolSpeedMonitor:
    def __init__(self, port="AUTO", mock_mode=False):
        """
        Polis aracı hızını OBD-II portundan (ELM327) okuyan modül.
        
        Args:
            port: COM portu (örn: COM4) veya "AUTO"
            mock_mode: True ise rastgele polis hızı simüle eder.
        """
        self.mock_mode = mock_mode
        self.connection = None
        self.cmd_speed = obd.commands.SPEED # Standart OBD Hız komutu (01 0D)
        
        if not mock_mode:
            try:
                print(f"OBD Bağlantısı aranıyor ({port})...")
                self.connection = obd.OBD(port, fast=False) # fast=False daha kararlıdır
                if self.connection.is_connected():
                    print("OBD BAĞLANDI! Araç beyni ile iletişim kuruldu.")
                else:
                    print("OBD BAĞLANTISI BAŞARISIZ! Mock moda geçiliyor.")
                    self.mock_mode = True
            except Exception as e:
                print(f"OBD Hatası: {e}")
                self.mock_mode = True
        else:
            print("Patrol Speed: MOCK MODU AKTIF")
            
        # İvme Hesabı için değişkenler
        self.last_speed_mps = 0
        self.last_time = time.time()
        self.current_accel = 0.0

    def get_speed_and_accel(self):
        """
        [HIZ (km/s), IVME (m/s^2)] döndürür.
        """
        current_speed_kmh = 0
        now = time.time()
        dt = now - self.last_time
        
        if self.mock_mode:
            # Simülasyon: Polis aracı 50-80 km/s arası gidiyor olsun
            # Hafif dalgalanma ekleyelim
            base_speed = 70
            noise = random.randint(-2, 2)
            current_speed_kmh = base_speed + noise
            # Mock İvme: Arada sırada ani fren simüle et (Test için)
            if random.random() < 0.05: # %5 şansla ani fren
                self.current_accel = -3.5 # m/s^2
            else:
                self.current_accel = 0.0
        
        elif self.connection and self.connection.is_connected():
            response = self.connection.query(self.cmd_speed)
            if not response.is_null():
                # obd response birimi Unit.KPH'dir (genelde)
                current_speed_kmh = int(response.value.magnitude)
        
        # İvme Hesapla (Gerçek Mod)
        if not self.mock_mode and dt > 0.1: # Çok sık hesaplama yapma
            current_speed_mps = current_speed_kmh / 3.6
            accel = (current_speed_mps - self.last_speed_mps) / dt
            self.current_accel = accel
            
            self.last_speed_mps = current_speed_mps
            self.last_time = now
            
        return current_speed_kmh, self.current_accel

    def get_speed(self):
        s, a = self.get_speed_and_accel()
        return s
