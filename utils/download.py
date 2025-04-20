import base64

def get_table_download_link(filename):
    with open(filename, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 {filename} 다운로드</a>'
    return href