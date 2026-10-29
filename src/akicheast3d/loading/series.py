"""Serien in einem DICOM-Ordner oder unter einem DICOMDIR finden."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pydicom.dataset import Dataset
from pydicom.uid import (
    ComprehensiveSRStorage,
    EnhancedSRStorage,
    XRayRadiationDoseSRStorage,
)

from akicheast3d.core import ProgressCallback
from akicheast3d.loading.tags import read_header

DOSE_REPORT_CLASSES = {
    XRayRadiationDoseSRStorage,
    EnhancedSRStorage,
    ComprehensiveSRStorage,
}
MIN_SLICES = 3


class SeriesKind(Enum):
    VOLUME = "volume"
    LOCALIZER = "localizer"
    DOSE_REPORT = "dose_report"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class SeriesInfo:
    """Eine gefundene Serie. Enthält keine Patientendaten."""

    uid: str
    number: int | None
    description: str
    modality: str
    slice_thickness: float | None
    files: tuple[Path, ...]
    kind: SeriesKind
    note: str
    """Hinweis für die Serienliste, leer bei ladbaren Serien."""

    @property
    def slice_count(self) -> int:
        return len(self.files)

    @property
    def loadable(self) -> bool:
        return self.kind is SeriesKind.VOLUME


def scan(path: Path, progress: ProgressCallback | None = None) -> list[SeriesInfo]:
    """Durchsucht einen Ordner mit allen Unterordnern nach DICOM-Serien.

    Wird eine Datei angegeben, zum Beispiel ein DICOMDIR, wird ihr Ordner durchsucht.
    Dateien, die kein DICOM sind, werden übersprungen. Doppelte Dateien zählen einmal.
    """
    root = Path(path)
    if root.is_file():
        root = root.parent
    files = sorted(p for p in root.rglob("*") if p.is_file())

    groups: dict[str, list[tuple[Path, Dataset]]] = {}
    seen: set[str] = set()
    for n, file in enumerate(files, start=1):
        ds = read_header(file)
        # Ein DICOMDIR hat keine SeriesInstanceUID und fällt hier heraus.
        if ds is not None and "SeriesInstanceUID" in ds:
            sop_uid = str(ds.get("SOPInstanceUID", file))
            if sop_uid not in seen:
                seen.add(sop_uid)
                groups.setdefault(str(ds.SeriesInstanceUID), []).append((file, ds))
        if progress:
            progress(n / len(files))

    series = [_describe(uid, members) for uid, members in groups.items()]
    series.sort(key=lambda s: (s.number is None, s.number or 0, s.description))
    return series


def _describe(uid: str, members: list[tuple[Path, Dataset]]) -> SeriesInfo:
    first = members[0][1]
    kind, note = _classify(first, len(members))
    number = first.get("SeriesNumber")
    thickness = first.get("SliceThickness")
    return SeriesInfo(
        uid=uid,
        number=int(number) if number not in (None, "") else None,
        description=str(first.get("SeriesDescription", "")).strip() or "(ohne Beschreibung)",
        modality=str(first.get("Modality", "")),
        slice_thickness=float(thickness) if thickness not in (None, "") else None,
        files=tuple(path for path, _ in members),
        kind=kind,
        note=note,
    )


def _classify(ds: Dataset, count: int) -> tuple[SeriesKind, str]:
    modality = str(ds.get("Modality", ""))
    image_type = [str(v).upper() for v in ds.get("ImageType", [])]

    if ds.get("SOPClassUID") in DOSE_REPORT_CLASSES or modality == "SR":
        return SeriesKind.DOSE_REPORT, "Dosisbericht, kein 3D möglich"
    if "LOCALIZER" in image_type:
        return SeriesKind.LOCALIZER, "Übersichtsbild (Topogramm), kein 3D möglich"
    if modality != "CT":
        return SeriesKind.UNSUPPORTED, f"Kein CT ({modality or 'unbekannt'}), wird nicht unterstützt"
    if int(ds.get("NumberOfFrames", 1) or 1) > 1:
        return SeriesKind.UNSUPPORTED, "Mehrbild-Datei, wird noch nicht unterstützt"
    if "ImagePositionPatient" not in ds or "ImageOrientationPatient" not in ds:
        return SeriesKind.UNSUPPORTED, "Ohne Positionsangaben, kein 3D möglich"
    if count < MIN_SLICES:
        return SeriesKind.UNSUPPORTED, "Zu wenige Schichten für 3D"
    return SeriesKind.VOLUME, ""
