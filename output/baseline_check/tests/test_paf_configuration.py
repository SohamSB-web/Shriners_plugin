from pathlib import Path


def test_paf_preserves_qtm_encoding_marker():
    """The PAF encoding marker is required for QTM to read generated sessions."""
    paf_path = (
        Path(__file__).resolve().parents[1]
        / "Shriners_Gait_Model_PAF_v1.0"
        / "Shriners_Gait_Model_PAF_v1.0"
        / "Settings.paf"
    )

    contents = paf_path.read_text(encoding="utf-8")

    assert "Encoding bytes: €€€€€" in contents
    assert "Encoding bytes: ?????" not in contents
