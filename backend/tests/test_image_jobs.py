from threading import Event
import time
import pytest

from app.image_jobs import ImageJobConflict, ImageJobManager, ImageJobNotFound


def wait_for(manager, job_id, statuses, timeout=2):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        job=manager.get(job_id)
        if job['status'] in statuses:
            return job
        time.sleep(.01)
    raise AssertionError('image job did not reach expected state')


def test_image_job_persists_result_and_missing_id_is_explicit(tmp_path):
    def generate(recipe, output_dir):
        return {'status':'completed','url':'/generated/example.png','is_ai_generated':True}
    manager=ImageJobManager(tmp_path/'jobs.sqlite3',generate)
    try:
        created=manager.submit({'recipe_id':'demo-001'},tmp_path)
        completed=wait_for(manager,created['job_id'],{'completed'})
        assert completed['result']['url']=='/generated/example.png'
        with pytest.raises(ImageJobNotFound):
            manager.get('missing')
    finally:
        manager.shutdown()
    reopened=ImageJobManager(tmp_path/'jobs.sqlite3',generate)
    try:
        assert reopened.get(created['job_id'])['status']=='completed'
    finally:
        reopened.shutdown()


def test_only_queued_image_job_can_be_cancelled(tmp_path):
    release=Event()
    def generate(recipe, output_dir):
        release.wait(1)
        return {'status':'completed','url':'/generated/example.png','is_ai_generated':True}
    manager=ImageJobManager(tmp_path/'jobs.sqlite3',generate,max_workers=1)
    try:
        first=manager.submit({'recipe_id':'first'},tmp_path)
        wait_for(manager,first['job_id'],{'running'})
        second=manager.submit({'recipe_id':'second'},tmp_path)
        cancelled=manager.cancel(second['job_id'])
        assert cancelled['status']=='cancelled'
        with pytest.raises(ImageJobConflict):
            manager.cancel(first['job_id'])
    finally:
        release.set()
        manager.shutdown()
