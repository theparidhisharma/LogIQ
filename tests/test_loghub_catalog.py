from services.dataset import main as dataset


def test_loghub_catalog_has_upstream_references_and_import_metadata():
    result = dataset.loghub_catalog()
    assert result['repository'] == 'https://github.com/logpai/loghub'
    ids = {item['name'] for item in result['items']}
    assert {'HDFS_v1', 'Hadoop', 'OpenStack', 'BGL', 'HPC', 'Zookeeper'} <= ids
    assert all(item['download'].startswith('https://zenodo.org/records/8196385/files/') for item in result['items'])
    assert all('labeled' in item and 'raw_size' in item for item in result['items'])


def test_loghub_upload_requires_catalog_id():
    assert 'Hadoop' in dataset.LOGHUB_CATALOG
    assert 'made-up' not in dataset.LOGHUB_CATALOG
