import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app

app = create_app({'TESTING': True})

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'

    paths = ['/reverse-builder', '/bottleneck-predictor', '/upgrade-planner']

    for path in paths:
        print('---', path, '---')
        try:
            resp = client.get(path)
            print('Status code:', resp.status_code)
            data = resp.get_data(as_text=True)
            if resp.status_code >= 500:
                print('Response body (truncated):')
                print(data[:1500])
            else:
                print('Response length:', len(data))
        except Exception as e:
            import traceback
            traceback.print_exc()
