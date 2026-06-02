## MD to Docs

Converts a markdown file to a new Google Doc. LaTeX is normalized to `$$...$$` (compatible with the [Auto-Latex Equations](https://workspace.google.com/marketplace/app/auto_latex_equations/850293439076) extension). Images are embedded inline.

### Setup
The setup is a bit annoying, but for subsequent use you only have to run a single command to produce your google doc. 
1. In [Google Cloud Console](https://console.cloud.google.com/), create a project and enable the **Google Drive API** and **Google Docs API**.
2. Go to **APIs and Services -> Credentials -> Create Credentials -> OAuth client ID**. Select **Desktop app**, download the JSON, and save it as `credentials.json` in the project directory. You'll need to add yourself as a test user to your project. 
3. Install dependencies:

```
pip install google-auth google-auth-oauthlib google-api-python-client
brew install pandoc
```

### Usage

```
python main.py <md_path> [--title <title>] [--media-dir <path>] [--save-docx <path>]
```

- `md_path` — path to the markdown file
- `--title` — title for the new Google Doc (default: markdown filename)
- `--media-dir` — path to the folder containing images referenced in the markdown (default: same directory as the markdown file)
- `--save-docx` — save the intermediate `.docx` to this path for inspection

On first run, a browser window will open to authorize access. The token is cached in `token.json` for subsequent runs. After running, open the Google Doc and run the Auto-Latex Equations extension to render math.