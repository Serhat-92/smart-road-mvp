"""
KANIT VE İHLAL KAYIT SİSTEMİ
Geliştirici: Yusuf Serhat Tümtürk
"""
import cv2
import os
import datetime
import json
import threading
import queue
import time
import requests

class NetworkUploader:
    """
    Arka planda (Asenkron) çalışan 5G Veri Gönderme Modülü.
    Radar sistemini dondurmadan verileri sunucuya yükler.
    """
    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
        self.upload_queue = queue.Queue()
        self.running = True
        self.endpoint = f"{server_url}/api/violation"
        
        # Gönderim işlemini yapacak arka plan işçisini başlat
        self.worker_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.worker_thread.start()
        print(f"📡 5G MODÜLÜ AKTİF: Hedef -> {self.server_url}")

    def add_to_queue(self, violation_data, image_path):
        """Kuyruğa yeni bir ihlal paketi ekler."""
        self.upload_queue.put((violation_data, image_path))

    def _upload_worker(self):
        while self.running:
            try:
                # Kuyruktan veri al (yoksa 1sn bekle)
                data, img_path = self.upload_queue.get(timeout=1)
                
                # Veriyi sunucuya gönder
                self._send_to_server(data, img_path)
                
                # İşin bittiğini işaretle
                self.upload_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Upload Loop Error: {e}")

    def _send_to_server(self, data, img_path):
        """Gerçek HTTP İsteği (5G Simülasyonu)"""
        try:
            # Resim dosyasını aç
            with open(img_path, 'rb') as f:
                files = {'file': (os.path.basename(img_path), f, 'image/jpeg')}
                
                # JSON verisini string olarak gönder
                payload = {'jsonData': json.dumps(data)}
                
                print(f"☁️ YÜKLENİYOR: {data['record_id']}...")
                response = requests.post(self.endpoint, data=payload, files=files, timeout=10)
                
                if response.status_code == 200:
                    print(f"✅ 5G BAŞARILI: {data['record_id']} Merkezde!")
                else:
                    print(f"⚠️ 5G HATASI {response.status_code}: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print("❌ BAĞLANTI HATASI: Sunucuya erişilemiyor (Offline Modda çalışılıyor)")
        except Exception as e:
            print(f"❌ UPLOAD HATASI: {e}")

    def stop(self):
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1)

class EvidenceRecorder:
    def __init__(self, output_dir="ihlaller", server_url=None):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Eğer sunucu URL verildiyse uploader'ı başlat
        self.uploader = None
        if server_url:
            self.uploader = NetworkUploader(server_url)
            
    def save_violation(self, frame, speed, limit, track_id, radar_speed=0, ai_speed=0, deviation=0.0):
        """
        İhlal anını 'İhlal Paketi' olarak (JPG + JSON) kaydeder ve varsa sunucuya gönderir.
        """
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%H-%M-%S")
        
        # 1. Fotoğraf İşlemleri (Watermark)
        evidence_img = frame.copy()
        h, w = evidence_img.shape[:2]
        
        # Bilgi kutusu (Alt şerit)
        cv2.rectangle(evidence_img, (0, h-180), (w, h), (0, 0, 150), -1) 
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        # Başlık ve ID
        cv2.putText(evidence_img, f"RESMI IHLAL KAYDI - ID:{track_id}", (20, h-140), font, 1.0, (255,255,255), 2)
        
        # Sol Kolon (Temel Bilgiler)
        cv2.putText(evidence_img, f"TARIH: {now.strftime('%d.%m.%Y %H:%M:%S')}", (20, h-100), font, 0.6, (255,255,255), 1)
        cv2.putText(evidence_img, f"KONUM: OTOYOL K3 NOKTASI (SABIT)", (20, h-70), font, 0.6, (255,255,255), 1)
        
        # Sağ Kolon (Hız Verileri - Kritik)
        col2_x = w // 2
        # Yasal Hız (Radar) - Sarı Renk
        cv2.putText(evidence_img, f"RADAR HIZI: {int(radar_speed)} km/s", (col2_x, h-100), font, 0.8, (0, 255, 255), 2)
        # AI Tahmini - Beyaz (Referans)
        cv2.putText(evidence_img, f"AI TAHMINI: {int(ai_speed)} km/s", (col2_x, h-70), font, 0.6, (200, 200, 200), 1)
        # Sapma Oranı
        cv2.putText(evidence_img, f"SAPMA: %{deviation:.1f}", (col2_x, h-40), font, 0.6, (200, 200, 200), 1)
        
        # Limit Bilgisi
        cv2.putText(evidence_img, f"YASAL LIMIT: {limit} km/s", (20, h-40), font, 0.8, (255, 255, 0), 2)
        
        # Dosya İsimlendirme
        base_filename = f"{timestamp_str}_ID{track_id}_SPD{int(radar_speed)}"
        img_path = os.path.join(self.output_dir, base_filename + ".jpg")
        json_path = os.path.join(self.output_dir, base_filename + ".json")
        
        # 2. Resmi Kaydet
        cv2.imwrite(img_path, evidence_img)
        
        # 3. JSON Veri Paketi Oluştur
        violation_package = {
            "record_id": base_filename,
            "timestamp": now.isoformat(),
            "location": "OTOYOL_K3",
            "vehicle_id": track_id,
            "limit": limit,
            "measurements": {
                "radar_speed": radar_speed,
                "ai_vision_speed": ai_speed,
                "deviation_percent": deviation,
                "final_speed": speed  # Ceza kesilen hız (Genelde Radar)
            },
            "evidence_files": {
                "photo": img_path
            }
        }
        
        # JSON Kaydet
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(violation_package, f, indent=4, ensure_ascii=False)
            
        print(f"IHLAL PAKETI OLUSTURULDU: {base_filename}")
        
        # 4. Sunucuya Gönder (Eğer aktifse)
        if self.uploader:
            self.uploader.add_to_queue(violation_package, img_path)

    def stop(self):
        if self.uploader:
            self.uploader.stop()
