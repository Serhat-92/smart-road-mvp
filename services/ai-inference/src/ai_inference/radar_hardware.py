"""
DONANIM RADAR ARAYÜZÜ MODÜLÜ
Geliştirici: Yusuf Serhat Tümtürk

Bu modül, seri port (USB/UART) üzerinden bağlanan radar sensörlerinden (Örn: OmniPreSense OPS243)
gerçek zamanlı veri okumayı sağlar.
"""

import serial
import threading
import time

class RadarSensor:
    def __init__(self, port, baudrate=19200):
        self.port = port
        self.baudrate = baudrate
        self.current_speed = 0.0
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()
        self.connection = None

    def start(self):
        """Sensör okuma işlemini başlatır (Arka planda thread olarak)."""
        try:
            self.connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.is_running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            print(f"[Donanım] Sensör bağlandı: {self.port}")
            return True
        except serial.SerialException as e:
            print(f"[Donanım] Bağlantı Hatası ({self.port}): {e}")
            return False

    def stop(self):
        """Sensör okuma işlemini durdurur."""
        self.is_running = False
        if self.connection and self.connection.is_open:
            self.connection.close()

    def get_speed(self):
        """En son okunan anlık hız değerini döndürür (km/s cinsinden)."""
        with self.lock:
            return self.current_speed

    def _read_loop(self):
        """Sürekli veri okuyan döngü."""
        while self.is_running and self.connection.is_open:
            try:
                # Satır oku (Örn: "15.5" veya "15.5\r\n")
                # OmniPreSense genellikle basit string veya JSON atar.
                line = self.connection.readline().decode('utf-8').strip()
                
                if line:
                    # Gelen veriyi parse etmeye çalış
                    try:
                        # Eğer veri JSON değilse ve saf sayıysa:
                        # Bazı sensörler m/s veya mph gönderebilir, birim dönüşümü gerekebilir.
                        # Varsayım: Sensör km/s veya ayarlanabilir birim gönderiyor.
                        # Eğer m/s geliyorsa 3.6 ile çarpılmalı.
                        
                        val = float(line)
                        
                        # Gürültü filtresi (0.1 altını yok say)
                        if val > 0.5:
                            with self.lock:
                                self.current_speed = abs(val)
                        else:
                            # Yoksa hız 0 kabul edilebilir veya son değer tutulabilir.
                            # Genelde radar veri göndermiyorsa nesne yoktur.
                            with self.lock:
                                self.current_speed = 0.0
                                
                    except ValueError:
                        # Sayısal olmayan veri geldiyse (debug mesajı vs) yoksay
                        pass
                        
            except Exception as e:
                print(f"[Donanım] Okuma Hatası: {e}")
                time.sleep(1)

class MockRadarSensor(RadarSensor):
    """Test amaçlı sanal radar sensörü."""
    def __init__(self):
        super().__init__("MOCK", 0)
        
    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._mock_loop, daemon=True)
        self.thread.start()
        print("[Donanım] Sanal Sensör (MOCK) başlatıldı.")
        return True
        
    def _mock_loop(self):
        import random
        import time
        
        # Simülasyon Senaryoları (CHAOS MODE)
        # Sistem her 10 saniyede bir senaryo değiştirsin
        scenarios = ["NORMAL", "SIGNAL_LOSS", "UNSTABLE", "GHOST_TARGET"]
        current_scenario_idx = 0
        last_switch = time.time()
        
        print("[MOCK] Senaryo Döngüsü Başlatıldı: NORMAL -> LOSS -> UNSTABLE -> GHOST")
        
        while self.is_running:
            # Senaryo Değiştirme
            if time.time() - last_switch > 10:
                current_scenario_idx = (current_scenario_idx + 1) % len(scenarios)
                last_switch = time.time()
                print(f"[MOCK] SENARYO DEĞİŞTİ: {scenarios[current_scenario_idx]}")
            
            scenario = scenarios[current_scenario_idx]
            measure = 0.0
            
            # --- SENARYO MANTIĞI ---
            
            if scenario == "NORMAL":
                # Stabil Hedef: 135 km/s, Polis: 70 km/s -> Radar: 65
                measure = 65 + random.uniform(-2, 2)
                if random.random() > 0.1: # %90 stabil
                    with self.lock: self.current_speed = measure
                else: 
                     with self.lock: self.current_speed = 0 # Anlık kopma
                     
            elif scenario == "SIGNAL_LOSS":
                # Sinyal tamamen gitti (Tünel vs.)
                with self.lock: self.current_speed = 0.0
                
            elif scenario == "UNSTABLE":
                # Aşırı Gürültü (Jitter)
                # Bir 30, bir 90 ölçüyor. Sistem bunu filtrelemeli.
                val = random.choice([30, 90, 45, 120])
                with self.lock: self.current_speed = val
                
            elif scenario == "GHOST_TARGET":
                # Hayalet Hedef (Kamera 90 görüyor ama Radar 200 diyor)
                # Radar çok hızlı bir şey görüyor (Belki kuş, belki yansıma)
                # Kamera bunu eşleştirememeli ve "MISMATCH" vermeli.
                with self.lock: self.current_speed = 190.0
            
            time.sleep(0.2)
