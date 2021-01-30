import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

import unicodedata
import os
import io
from datetime import datetime

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

def init_drive_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    return service

def export_sheet(drive_service, file_id, output_name):
    data = drive_service.files().export(fileId=file_id, mimeType='text/csv').execute()

    return data

def search_folders(drive_service, folder_name):
    page_token = None
    results = {}
    while True:
        response = drive_service.files().list(
            q=f"name = '{folder_name}' and mimeType='application/vnd.google-apps.folder'",
            spaces='drive',
            fields='nextPageToken, files(id, name)',
            pageToken=page_token
        ).execute()
        for file in response.get('files', []):
            results[file.get('name')] = file.get('id')
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return results

def search_by_name(drive_service, file_name, parent_folder_id=None):
    # name = 'file_name' and 'parent_folder_id' in parents
    if parent_folder_id is not None:
        raise NotImplementedError()

    page_token = None
    results = {}
    while True:
        response = drive_service.files().list(
            q=f"name = '{file_name}'",
            spaces='drive',
            fields='nextPageToken, files(id, name)',
            pageToken=page_token
        ).execute()
        for file in response.get('files', []):
            results[file.get('name')] = file.get('id')
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break

    return results

def get_exact(name, results):
    c = 0
    m = None
    for k, v in results.items():
        if k == name:
            c += 1
            m = v
    if c > 1:
        raise RuntimeError(f'Found multiple matches for {name}: {c}')
    return m

def gen_pleco_import(entries):
    out = []
    for category, entries in entries.items():
        out.append(f'// {category}')

        for entry in entries:
            out.append(f'{entry.chinese}\t{entry.pinyin}')
    return '\n'.join(out)

class Entry:
    def __init__(self, category, chinese, pinyin):
        self.category = category
        self.chinese = chinese
        self.pinyin = pinyin

def parse_sheet(sheet_contents, parent_category):
    lines = sheet_contents.decode('utf-8').split('\r\n')
    header = lines[0].split(',')
    lines = lines[1:]
    vals = []

    for line in lines:
        v = {}
        vals.append(v)
        for col, val in zip(header, line.split(',')):
            v[col] = val

    sheet = {}
    for v in vals:
        week = v['Week']
        cat = f'{parent_category}/{week}'
        chinese = v['Chinese']
        pinyin = v['Pinyin']
        try:
            entries = sheet[cat]
        except KeyError:
            sheet[cat] = []
            entries = sheet[cat]
        entries.append(Entry(cat, chinese, pinyin))

    return sheet

tone_map = {
    # high
    b'\xcc\x84': 1,
    # rising
    b'\xcc\x81': 2,
    # falling rising
    b'\xcc\x8c': 3,
    # falling
    b'\xcc\x80': 4,
}

def convert_pinyin(unicode_str):
    n = unicodedata.normalize('NFD', unicode_str)
    o = [map_pinyin(c) for c in n]
    return ''.join(o)

def map_pinyin(c):
    try:
        return str(tone_map[c.encode('utf-8')])
    except:
        return c

def upload(drive_service, source_file, dest_folder_id, dest_name):
    file_metadata = {
        'name': dest_name,
        'parents': [dest_folder_id]
    }
    media = MediaFileUpload(source_file, mimetype='text/plain')
    file = drive_service.files().create(body=file_metadata,
                                        media_body=media,
                                        fields='id').execute()
    return file['id']

def update(drive_service, source_file, dest_id):
    media = MediaFileUpload(source_file)
    drive_service.files().update(
        fileId=dest_id,
        media_body=media
    ).execute()

def main():
    drive_service = init_drive_service()
    source_file = 'Chinese Words'
    export_folder = 'pleco'
    matches = search_by_name(drive_service, source_file)
    file_id = get_exact(source_file, matches)
    matches = search_folders(drive_service, export_folder)
    folder_id = get_exact(export_folder, matches)

    contents = export_sheet(drive_service, file_id, 'demo')
    sheet = parse_sheet(contents, 'Y2021')
    pleco = gen_pleco_import(sheet)

    file_date = datetime.today().strftime('%Y-%m-%d')
    output_name = f'{file_date}_pleco_import.txt'
    out_folder = 'output'
    output_path = os.path.join(out_folder, output_name)

    os.makedirs(out_folder, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(pleco)

    # todo: include directory in search
    matches = search_by_name(drive_service, output_name)
    dest_file_id = get_exact(output_name, matches)

    print('got dest file name', dest_file_id)

    if dest_file_id is None:
        upload(drive_service, output_path, folder_id, output_name)
    else:
        print('Found existing file:', dest_file_id)
        if input('Overwrite? y/n').strip() == 'y':
            update(drive_service, output_path, dest_file_id)
        else:
            print('skipping update')

if __name__ == '__main__':
    main()
