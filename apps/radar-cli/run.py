"""Interactive launcher for the radar CLI app."""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_PY = REPO_ROOT / "shared" / "python"
if str(SHARED_PY) not in sys.path:
    sys.path.insert(0, str(SHARED_PY))

from monorepo import ensure_repo_imports
from radar_config import load_config, save_config

ensure_repo_imports(REPO_ROOT)

from ai_inference.main import main as radar_main


def resolve_source_argument(raw_value):
    candidate = Path(raw_value)
    repo_relative = REPO_ROOT / raw_value
    if raw_value.isdigit():
        return int(raw_value)
    if candidate.exists():
        return str(candidate)
    if repo_relative.exists():
        return str(repo_relative)
    return raw_value


def prompt_runtime_config():
    config = load_config(REPO_ROOT)
    default_max = config.get("max_speed", 90)
    default_min = config.get("min_speed", 30)
    default_factor = config.get("speed_factor", 0.22)

    max_speed = default_max
    min_speed = default_min
    speed_factor = default_factor

    print("Mobil Radar Sistemi Baslatici")
    print("-----------------------------")
    print(
        f"Aktif ayarlar: MAX={default_max}, MIN={default_min}, "
        f"HASSASIYET={default_factor}"
    )

    change_settings = input("Ayarlari degistirmek ister misiniz? (e/h): ").strip().lower()
    if change_settings == "e":
        try:
            max_speed = int(
                input(f"Maksimum hiz limiti (Varsayilan {default_max}): ") or default_max
            )
            min_speed = int(
                input(f"Minimum hiz limiti (Varsayilan {default_min}): ") or default_min
            )
            speed_factor = float(
                input(f"Hassasiyet carpani (Varsayilan {default_factor}): ")
                or default_factor
            )
            save_config(
                REPO_ROOT,
                {
                    "max_speed": max_speed,
                    "min_speed": min_speed,
                    "speed_factor": speed_factor,
                },
            )
            print("Ayarlar kaydedildi ve varsayilan yapildi.")
        except ValueError:
            print("Hatali giris. Varsayilan degerler kullanilacak.")

    return max_speed, min_speed, speed_factor


def parse_runtime_args(argv):
    source = 0
    hardware_port = None

    for arg in argv:
        upper_arg = arg.upper()
        if "COM" in upper_arg or upper_arg == "MOCK":
            hardware_port = arg
        else:
            source = resolve_source_argument(arg)

    return source, hardware_port


def prompt_hardware_port(current_port):
    if current_port is not None:
        return current_port

    use_hw = input("Donanim sensoru kullanilsin mi? (COM port adi veya 'h'ayir): ")
    use_hw = use_hw.strip()
    if use_hw and use_hw.lower() != "h":
        return use_hw
    return None


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv

    try:
        max_speed, min_speed, speed_factor = prompt_runtime_config()
    except KeyboardInterrupt:
        sys.exit()

    source, hardware_port = parse_runtime_args(args)
    hardware_port = prompt_hardware_port(hardware_port)

    evidence_dir = REPO_ROOT / "datasets" / "violations"
    radar_main(
        source,
        max_speed=max_speed,
        min_speed=min_speed,
        speed_factor=speed_factor,
        hardware_port=hardware_port,
        evidence_dir=str(evidence_dir),
    )


if __name__ == "__main__":
    main()
