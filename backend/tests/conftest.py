import os
from pathlib import Path
import tempfile
os.environ['RECIPE_DB_PATH'] = str(Path(tempfile.mkdtemp(prefix='recipe-tests-')) / 'test.sqlite3')
for key in ('EMBEDDING_MODEL', 'OLLAMA_EMBED_MODEL', 'OLLAMA_MODEL', 'DIFFUSION_MODEL', 'CNN_CHECKPOINT', 'CNN_LABELS_PATH', 'OLLAMA_VISION_MODEL'):
    os.environ.pop(key, None)
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
