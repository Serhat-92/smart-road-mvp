"""
KULLANICI ARAYÜZÜ VE HUD (HEAD-UP DISPLAY)
Geliştirici: Yusuf Serhat Tümtürk
"""
import cv2
import numpy as np

class RadarUI:
    def __init__(self, max_speed=90, min_speed=30):
        self.max_speed = max_speed
        self.min_speed = min_speed
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Renkler (B, G, R)
        self.COLOR_NORMAL = (0, 255, 0)      # Yeşil (Normal)
        self.COLOR_WARNING = (0, 0, 255)     # Kırmızı (İhlal - Çok Hızlı)
        self.COLOR_SLOW = (0, 255, 255)      # Sarı (Çok Yavaş)
        self.COLOR_TEXT = (255, 255, 255)    # Beyaz
        self.COLOR_HUD_BG = (50, 50, 50)     # Koyu Gri

    def draw_dashboard(self, frame, own_speed, track_count=0):
        """
        Ekranın altına polis aracının hızını ve durumunu çizer.
        """
        h, w = frame.shape[:2]
        
        # Alt bant
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h-60), (w, h), (0, 0, 0), -1)
        # Şeffaflık
        alpha = 0.6
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        
        # Yazılar
        info_text = f"POLICE UNIT: {own_speed} km/h | TARGETS: {track_count}"
        cv2.putText(frame, info_text, (20, h-20), self.font, 0.8, self.COLOR_TEXT, 2)
        
        limit_text = f"LIMIT: {self.min_speed} - {self.max_speed} km/h"
        cv2.putText(frame, limit_text, (w - 350, h-20), self.font, 0.8, self.COLOR_WARNING, 2)
        
        # Sol Üst Köşe Durum Bilgisi (Sistem Çalışıyor mu?)
        cv2.putText(frame, "RADAR SYSTEM ACTIVE", (20, 40), self.font, 0.7, (0, 255, 0), 2)
        
        return frame

    def draw_detections(self, frame, vehicle_data):
        """
        Araçların etrafına kutu ve hız bilgisini çizer.
        vehicle_data formatı: {track_id: {'box': [x1,y1,x2,y2], 'speed': float}}
        """
        for track_id, data in vehicle_data.items():
            x1, y1, x2, y2 = map(int, data['box'])
            speed = data['speed']
            
            # Sadece Hız Limitini Aşanları (Ve varsa çok yavaşları) Göster
            # Normal (Yeşil) araçları çizme ki ekran kalabalık olmasın.
            should_draw = False
            
            if speed > self.max_speed:
                color = self.COLOR_WARNING # İhlal (Hızlı)
                tag = " ! IHLAL !"
            # Renk belirle (Hız limitine veya Füzyon durumuna göre)
            color = data.get('color', None)
            if color is None:
                color = (0, 0, 255) if speed > self.max_speed else (0, 255, 0)
            
            # Kutu çiz
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Etiket metni
            label = f"ID: {track_id} | {int(speed)} km/s"
            
            # Füzyon Durumu Ekranı
            fusion_status = data.get('fusion_status', None)
            radar_val = data.get('radar_speed', 0)
            
            if fusion_status:
                if fusion_status == "VERIFIED":
                    label += " [ONAY]"
                elif fusion_status == "MISMATCH":
                    label += f" [HATA! R:{int(radar_val)}]"
                
            
            # Arka plan kutusu (Okunabilirlik için)
            (w, h), _ = cv2.getTextSize(label, self.font, 0.6, 1)
            cv2.rectangle(frame, (x1, y1 - 25), (x1 + w, y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 8), self.font, 0.6, (255,255,255), 1)
            
        return frame
