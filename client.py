import time
import requests


'================ проверка обработки фото =============================================='

res = requests.post('http://127.0.0.1:5001/upscale', files={
    'image_for_upscale': open('example_image/valeri_nikolaev.jpg', 'rb')
})

print(res)
print(res.json())
task_id = res.json().get('task_id')
print(task_id)

status = 'PENDING'
while status == 'PENDING':
    res2 = requests.get(f'http://127.0.0.1:5001/tasks/{task_id}')
    res2_json = res2.json()
    print(res2.json())
    status = res2.json()['status']
    if res2.json()['status'] == 'PENDING':
        time.sleep(5)

print(res2_json['status'])
print(res2_json['link'])


'================ проверка GET `/processed/{file}` =============================================='

res = requests.get(f'http://127.0.0.1:5001/processed/valeri_nikolaev_UPSCALED.jpg')

print(res)
print(res.json())
