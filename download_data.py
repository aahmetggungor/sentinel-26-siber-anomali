"""Doğrulanmış UNSW-NB15 CSV kopyasını indir. Akademik lisans ve atıf README'de."""

from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

import pandas as pd


BASE = "https://raw.githubusercontent.com/Nir-J/ML-Projects/master/UNSW-Network_Packet_Classification/"
FILES = {
    "UNSW_NB15_training-set.csv": ("bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa", 175341),
    "UNSW_NB15_testing-set.csv": ("734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559", 82332),
}
DATA = Path(__file__).resolve().parent / "data"


def valid(path: Path, expected_hash: str, expected_rows: int) -> bool:
    if not path.is_file():
        return False
    if sha256(path.read_bytes()).hexdigest() != expected_hash:
        return False
    frame = pd.read_csv(path, usecols=["label"])
    return len(frame) == expected_rows and set(frame["label"].unique()) == {0, 1}


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    for filename, (expected_hash, expected_rows) in FILES.items():
        destination = DATA / filename
        if valid(destination, expected_hash, expected_rows):
            print(f"OK: {filename} doğrulandı.")
            continue
        temporary = DATA / (filename + ".download")
        print(f"İndiriliyor: {filename}", flush=True)
        with urlopen(BASE + filename, timeout=120) as source, temporary.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
        if not valid(temporary, expected_hash, expected_rows):
            temporary.unlink(missing_ok=True)
            raise ValueError(f"Dosya hash/satır kontrolünü geçmedi: {filename}")
        temporary.replace(destination)
        print(f"OK: {filename} indirildi ve doğrulandı.")
