from mitsu.voice import server_stt as SST


def test_doctor_shape():
    d = SST.doctor()
    assert {"recorder", "sources", "hints"} <= set(d)
    assert d["recorder"] is not None  # this machine has arecord/parecord
    assert isinstance(d["sources"], list)
