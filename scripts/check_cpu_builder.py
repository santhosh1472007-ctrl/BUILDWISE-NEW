import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app

app = create_app({'TESTING': True})

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'

    resp = client.get('/3d-builder')
    print('status', resp.status_code)
    data = resp.get_data(as_text=True)
    print('fetchCpuCatalog present:', 'fetchCpuCatalog' in data)
    print('cpu-select present:', '<select id="cpu-select"' in data)
    print('gpu-select present:', '<select id="gpu-select"' in data)
    print('catalog.cpu present:', 'catalog.cpu' in data)
    print('searchFilter cpu-only present:', "category === 'cpu'" in data)

    api_resp = client.get('/api/hardware/cpu')
    print('api status', api_resp.status_code)
    print('api body snippet:', api_resp.get_data(as_text=True)[:300])
