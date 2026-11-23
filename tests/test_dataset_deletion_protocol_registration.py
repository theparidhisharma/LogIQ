from pathlib import Path


def test_deletion_protocol_workers_and_outbox_are_registered():
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.yml").read_text()
    dataset_worker = (root / "services/dataset/deletion_worker.py").read_text()
    intelligence_worker = (root / "services/intelligence/deletion_worker.py").read_text()
    ack_worker = (root / "services/dataset/deletion_ack_worker.py").read_text()
    assert "intelligence-deletion-worker" in compose
    assert "dataset-deletion-ack-worker" in compose
    assert "dataset_deletion_outbox" in dataset_worker
    assert "datasets.deletion_requested" in intelligence_worker
    assert "dataset_deletion_receipts" in intelligence_worker
    assert "datasets.deletion_acknowledged" in ack_worker
