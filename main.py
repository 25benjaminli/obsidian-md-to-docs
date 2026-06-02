import os
import re
import argparse
import subprocess
import tempfile
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
]


def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as f:
            f.write(creds.to_json())
    return creds


def normalize_obsidian_images(md_content):
    # ![[filename.png|width]] or ![[filename.png]] → ![](filename.png)
    return re.sub(r'!\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', r'![](\1)', md_content)


def normalize_latex(md_content):
    # \[...\] → $$...$$
    md_content = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', md_content, flags=re.DOTALL)
    # \(...\) → $$...$$
    md_content = re.sub(r'\\\((.*?)\\\)', r'$$\1$$', md_content, flags=re.DOTALL)
    # $...$ (not $$) → $$...$$
    md_content = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', r'$$\1$$', md_content)
    return md_content


MATH_FILTER = """\
function Math(m)
  local delim = "$$"
  return pandoc.Str(delim .. m.text .. delim)
end
"""


def md_to_docx(md_path, media_dir, output_path):
    with open(md_path, 'r') as f:
        content = f.read()

    content = normalize_obsidian_images(content)
    content = normalize_latex(content)

    tmp_md = tmp_filter = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            tmp_md = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False, encoding='utf-8') as f:
            f.write(MATH_FILTER)
            tmp_filter = f.name

        resource_paths = [os.path.dirname(os.path.abspath(md_path))]
        if media_dir:
            resource_paths.append(os.path.abspath(media_dir))

        cmd = [
            'pandoc', tmp_md,
            '-o', output_path,
            '--resource-path', ':'.join(resource_paths),
            '--lua-filter', tmp_filter,
        ]
        subprocess.run(cmd, check=True)
    finally:
        for p in [tmp_md, tmp_filter]:
            if p and os.path.exists(p):
                os.unlink(p)


def upload_docx_as_gdoc(drive_service, docx_path, title):
    file_metadata = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.document',
    }
    media = MediaFileUpload(
        docx_path,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    doc = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id,webViewLink',
    ).execute()
    return doc['id'], doc['webViewLink']


def main():
    parser = argparse.ArgumentParser(description='Convert a markdown file to a new Google Doc.')
    parser.add_argument('md_path', help='Path to the markdown file')
    parser.add_argument('--title', default=None, help='Title for the new Google Doc (default: markdown filename)')
    parser.add_argument('--media-dir', default=None, help='Path to the media/images folder')
    parser.add_argument('--save-docx', default=None, metavar='PATH', help='Save the intermediate .docx to this path')
    args = parser.parse_args()

    title = args.title or os.path.splitext(os.path.basename(args.md_path))[0]

    creds = get_credentials()
    drive_service = build('drive', 'v3', credentials=creds)

    if args.save_docx:
        docx_path = args.save_docx
        cleanup = False
    else:
        tmp = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        tmp.close()
        docx_path = tmp.name
        cleanup = True

    try:
        print("Converting markdown to docx...")
        md_to_docx(args.md_path, args.media_dir, docx_path)

        if args.save_docx:
            print(f"Saved docx to {docx_path}")

        print("Uploading to Google Drive...")
        _, url = upload_docx_as_gdoc(drive_service, docx_path, title)
        print(f"Created: {url}")
    finally:
        if cleanup and os.path.exists(docx_path):
            os.unlink(docx_path)


if __name__ == '__main__':
    main()
