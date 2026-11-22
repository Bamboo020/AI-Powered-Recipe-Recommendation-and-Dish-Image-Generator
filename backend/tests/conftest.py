import os
from pathlib import Path
import tempfile
test_directory = Path(tempfile.mkdtemp(prefix='recipe-tests-'))
os.environ['RECIPE_DB_PATH'] = str(test_directory / 'test.sqlite3')
os.environ['IMAGE_JOB_DB_PATH'] = str(test_directory / 'image-jobs.sqlite3')
for key in ('EMBEDDING_MODEL', 'OLLAMA_EMBED_MODEL', 'OLLAMA_MODEL', 'DIFFUSION_MODEL', 'CNN_CHECKPOINT', 'CNN_LABELS_PATH', 'OLLAMA_VISION_MODEL'):
    os.environ.pop(key, None)
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
