"""Real checkpoint serialization/file IO with a controlled cloud transport."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import torch

from app.services import model_service


@pytest.fixture
def storage(tmp_path,monkeypatch):
    cloud = MagicMock()
    monkeypatch.setattr(model_service,"LOCAL_MODELS_DIR",tmp_path)
    monkeypatch.setattr(model_service,"supabase_client",SimpleNamespace(storage=SimpleNamespace(from_=lambda _:cloud)))
    return tmp_path,cloud


@pytest.mark.parametrize("identity",["../outside","/outside","nested/model",":0","model\\other"])
def test_checkpoint_identifiers_cannot_escape_storage(storage,identity):
    root,cloud = storage
    with pytest.raises(ValueError):
        model_service.save_checkpoint(identity,0,{"weights":torch.ones(1)})
    cloud.upload.assert_not_called()
    assert not list(root.rglob("*.pt"))


def test_serialization_failure_preserves_previous_checkpoint(storage,monkeypatch):
    root,cloud = storage
    destination = root/"model"/"checkpoint_0.pt"
    destination.parent.mkdir()
    destination.write_bytes(b"previous complete artifact")
    def interrupted_save(data,destination):
        if hasattr(destination,"write"):
            destination.write(b"partial")
        else:
            destination.write_bytes(b"partial")
        raise OSError("synthetic serialization interruption")
    monkeypatch.setattr(model_service.torch,"save",interrupted_save)
    with pytest.raises(OSError,match="interruption"):
        model_service.save_checkpoint("model",0,{"weights":torch.ones(1)})
    assert destination.read_bytes() == b"previous complete artifact"
    cloud.upload.assert_not_called()


@pytest.mark.parametrize("cloud_fails",[False,True])
def test_saved_bytes_and_receipt_identify_actual_storage_outcome(storage,cloud_fails):
    import hashlib
    root,cloud = storage
    if cloud_fails:
        cloud.upload.side_effect = OSError("synthetic upload unavailable")
    receipt = model_service.save_checkpoint("model",7,{"episode":7,"weights":torch.arange(3)})
    raw = (root/"model"/"checkpoint_7.pt").read_bytes()
    assert cloud.upload.call_args.kwargs["file"] == raw
    assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["size_bytes"] == len(raw) and receipt["local_saved"]
    assert receipt["cloud_uploaded"] is (not cloud_fails)
    cloud.download.side_effect = OSError("synthetic offline read")
    restored = model_service.load_checkpoint("model",7)
    assert restored["episode"] == 7
    torch.testing.assert_close(restored["weights"],torch.arange(3))


def test_atomic_replace_failure_preserves_previous_file_and_removes_temporary(storage,monkeypatch):
    from app.services import artifact_files
    root,cloud = storage
    destination = root/"model"/"checkpoint_0.pt"
    destination.parent.mkdir()
    destination.write_bytes(b"previous complete artifact")
    monkeypatch.setattr(artifact_files.os,"replace",MagicMock(side_effect=OSError("synthetic replace failure")))
    with pytest.raises(OSError,match="replace failure"):
        model_service.save_checkpoint("model",0,{"weights":torch.ones(1)})
    assert destination.read_bytes() == b"previous complete artifact"
    assert list(destination.parent.iterdir()) == [destination]
    cloud.upload.assert_not_called()


def test_remote_load_pins_exact_bytes_and_local_copy_has_explicit_precedence(storage):
    root,cloud = storage
    receipt = model_service.save_checkpoint("model",7,{"episode":7,"weights":torch.arange(3)})
    raw = (root/"model"/"checkpoint_7.pt").read_bytes()
    cloud.download.return_value = b"stale remote bytes"
    local = model_service.load_checkpoint("model",7,expected_sha256=receipt["sha256"])
    assert local["storage_provenance"]["source"] == "local"
    cloud.download.assert_not_called()
    (root/"model"/"checkpoint_7.pt").unlink()
    cloud.download.return_value = raw
    restored = model_service.load_checkpoint("model",7,expected_sha256=receipt["sha256"])
    assert restored["storage_provenance"]["source"] == "supabase"
    with pytest.raises(ValueError,match="expected SHA-256"):
        model_service.load_checkpoint("model",7,expected_sha256="0"*64)


def test_local_checkpoints_remain_visible_when_cloud_listing_is_incomplete(storage):
    root,cloud = storage
    destination = root/"model"/"checkpoint_7.pt"
    destination.parent.mkdir()
    destination.write_bytes(b"listing fixture")
    cloud.list.return_value = [{"name":"checkpoint_0.pt"},{"name":"unrelated.json"}]
    assert model_service.list_checkpoints("model") == ["models/model/checkpoint_0.pt","models/model/checkpoint_7.pt"]
