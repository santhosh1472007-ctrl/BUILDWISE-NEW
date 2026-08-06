from app import create_app

app = create_app({'TESTING': True})

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'

    resp = client.get('/3d-builder')
    print('Status code:', resp.status_code)
    data = resp.get_data(as_text=True)
    print('Response length:', len(data))
    # Show snippets of the select elements to confirm population
    start = data.find('<select id="cpu-select"')
    if start != -1:
        print(data[start:start+500])
    else:
        print('cpu-select not found')
    start = data.find('<select id="gpu-select"')
    if start != -1:
        print(data[start:start+500])
    else:
        print('gpu-select not found')
