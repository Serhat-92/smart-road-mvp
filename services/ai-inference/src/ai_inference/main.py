"""Main runtime for the ai-inference radar service."""

import argparse

import cv2

from .api import AIInferenceService
from .patrol_speed import PatrolSpeedMonitor
from .radar_hardware import MockRadarSensor, RadarSensor
from .recorder import EvidenceRecorder
from .ui import RadarUI


def parse_video_source(raw_source):
    """Return camera ids as int and file paths or URLs as strings."""
    if isinstance(raw_source, str) and raw_source.isdigit():
        return int(raw_source)
    return raw_source


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Mobil Radar Sistemi")
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Video kaynagi (0, 1 veya dosya yolu)",
    )
    parser.add_argument("--max_speed", type=int, default=90, help="Hiz limiti")
    parser.add_argument("--min_speed", type=int, default=30, help="Minimum hedef hiz")
    parser.add_argument(
        "--speed_factor",
        type=float,
        default=1.0,
        help="Gorsel hiz kalibrasyon katsayisi",
    )
    parser.add_argument(
        "--port",
        type=str,
        default=None,
        help="Radar donanim portu (COM3, MOCK)",
    )
    parser.add_argument(
        "--server",
        type=str,
        default=None,
        help="5G sunucu URL (orn: http://localhost:8000)",
    )
    parser.add_argument(
        "--evidence_dir",
        type=str,
        default="ihlaller",
        help="Ihlal paketlerinin kaydedilecegi klasor",
    )
    return parser


def main(
    video_source=0,
    max_speed=90,
    min_speed=30,
    speed_factor=1.0,
    hardware_port=None,
    server_url=None,
    evidence_dir="ihlaller",
):
    print(
        f"Sistem baslatiliyor (MAX: {max_speed}, MIN: {min_speed}, "
        f"FACTOR: {speed_factor})..."
    )
    if server_url:
        print(f"5G modulu aktif: {server_url}")

    hw_radar = None
    if hardware_port:
        if hardware_port.upper() == "MOCK":
            print("Simulasyon modu: sanal radar ve sanal OBD devrede.")
            hw_radar = MockRadarSensor()
        else:
            print(f"Donanim modu: {hardware_port} uzerinden sensor bekleniyor...")
            hw_radar = RadarSensor(port=hardware_port)

        if hw_radar and hw_radar.start():
            print(f"Donanim radar modu aktif: {hardware_port}")
        else:
            print("Donanim sensoru baslatilamadi, gorsel tahmine donuluyor.")
            hw_radar = None

    obd_mock = hardware_port.upper() == "MOCK" if hardware_port else True
    patrol_monitor = PatrolSpeedMonitor(port="AUTO", mock_mode=obd_mock)

    inference_service = AIInferenceService(speed_factor=speed_factor)
    ui = RadarUI(max_speed=max_speed, min_speed=min_speed)
    recorder = EvidenceRecorder(output_dir=evidence_dir, server_url=server_url)

    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"Hata: video kaynagi acilamadi ({video_source})")
        return

    print("Kayit basladi. Cikmak icin 'q' tusuna basin.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Video sonu veya okuma hatasi.")
            break

        current_patrol_speed, current_patrol_accel = patrol_monitor.get_speed_and_accel()
        radar_relative_speed = hw_radar.get_speed() if hw_radar else None
        inference = inference_service.infer_frame(
            frame,
            radar_relative_speed=radar_relative_speed,
            patrol_speed=current_patrol_speed,
            patrol_accel=current_patrol_accel,
        )
        vehicle_data = inference.vehicle_data

        for track_id, data in vehicle_data.items():
            speed = data["speed"]
            captured = data.get("captured", False)

            if speed > max_speed and not captured:
                radar_val = data.get("radar_speed", 0)
                ai_val = data.get("speed", 0)

                if radar_val == 0:
                    radar_val = speed

                deviation = 0.0
                if ai_val > 0:
                    deviation = abs(radar_val - ai_val) / ai_val * 100

                recorder.save_violation(
                    frame,
                    speed=speed,
                    limit=max_speed,
                    track_id=track_id,
                    radar_speed=radar_val,
                    ai_speed=ai_val,
                    deviation=deviation,
                )
                inference_service.mark_captured(track_id)

        frame = ui.draw_detections(frame, vehicle_data)
        frame = ui.draw_dashboard(frame, current_patrol_speed, track_count=len(vehicle_data))

        cv2.imshow("MOBIL RADAR SISTEMI - PROTOTIP", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    if hw_radar:
        hw_radar.stop()
    recorder.stop()


def main_cli(argv=None):
    args = build_arg_parser().parse_args(argv)
    main(
        video_source=parse_video_source(args.source),
        max_speed=args.max_speed,
        min_speed=args.min_speed,
        speed_factor=args.speed_factor,
        hardware_port=args.port,
        server_url=args.server,
        evidence_dir=args.evidence_dir,
    )


if __name__ == "__main__":
    main_cli()
